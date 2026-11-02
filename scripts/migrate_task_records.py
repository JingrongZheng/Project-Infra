"""One-time migration of this prototype's four retired records; recoverable and idempotent."""
from pathlib import Path
import json
import re
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_infra.documents import Document, scalar, template, digest
from project_infra.store import Store
from project_infra.validation import validate


MAPPING = {'TASK-0001': ('PLAN-0001', 'EXP-0004'),
           'TASK-0002': ('PLAN-0002', 'EXP-0005'),
           'TASK-0003': ('PLAN-0001', 'EXP-0003'),
           'TASK-0004': ('PLAN-0003', 'EXP-0006')}


def migrate(root):
    store = Store(root)
    source = store.path('.project/tasks')
    recovery = store.path('.work/migrations/task-removal')
    if not source.exists():
        return {'already_migrated': True}
    originals = {p.stem: Document.from_bytes(p.relative_to(store.root).as_posix(), p.read_bytes())
                 for p in source.glob('*.md')}
    if not originals:
        return {'already_migrated': True}
    if set(originals) - MAPPING.keys():
        raise ValueError('Unexpected legacy IDs: choose explicit destinations before migrating')
    # Resolve and confine both ends before any directory move; never replace an existing backup.
    backup = recovery / 'legacy-tasks'
    if not source.is_relative_to(store.root) or not backup.is_relative_to(store.root) or backup.exists():
        raise ValueError('Unsafe source or existing recovery backup; inspect before retrying')
    docs, load_errors = store.load()
    real_errors = [e for e in load_errors if not e.startswith('Legacy Task files found:')]
    if real_errors:
        raise ValueError('\n'.join(real_errors))
    changes, expected = {}, {}
    path_map = {f'.project/tasks/{old}.assets': f'.project/experiments/{exp}.assets'
                for old, (_, exp) in MAPPING.items()}
    def remap(text):
        for a, b in path_map.items():
            text = text.replace(a, b)
        for a, (plan, exp) in MAPPING.items():
            text = text.replace(a, exp)
        return text.replace('四类工作对象', '三个工作对象').replace('四类对象', '三个工作对象')
    def add(path, text):
        p = store.path(path)
        expected[path] = digest(p.read_bytes()) if p.exists() else None
        changes[path] = text
    for old_id, old in originals.items():
        plan_id, exp_id = MAPPING[old_id]
        plan_path = f'.project/plans/{plan_id}.md'
        exp_path = f'.project/experiments/{exp_id}.md'
        plan = Document(plan_path, changes.get(plan_path, docs[plan_id].raw if plan_id in docs else template('plan', plan_id, old.meta['title'])), '')
        exp = docs.get(exp_id) or Document(exp_path, template('experiment', exp_id, old.meta['title']), '')
        sections = {
            'Question': plan.section('Question') or old.section('Goal'),
            'Scope': plan.section('Scope') or old.section('Scope'),
            'Acceptance criteria': '\n\n'.join(filter(None, [plan.section('Acceptance criteria'),
                '### ' + old.meta['title'] + '\n\n' + old.section('Acceptance criteria')])),
            'Synthesis': plan.section('Synthesis') or old.section('Final summary')}
        experiments = list(dict.fromkeys(plan.meta.get('experiments', []) + [exp_id]))
        add(plan_path, remap(plan.patch({'status': 'active', 'resolution': None, 'experiments': experiments,
            'follow_up_tasks': None, 'design_anchor': plan.meta.get('design_anchor') or 'PROJECT.md#design-views'}, sections)))
        notes = '\n\n'.join(filter(None, [exp.section('Notes'), old.section('Implementation notes'),
            '### 实现范围\n' + old.section('Scope'), '### 范围之外\n' + old.section('Out of scope')]))
        verification = old.section('Verification')
        review_match = re.search(r'^### Reviewer note\s*\n([\s\S]+)', verification, re.M)
        add(exp_path, remap(exp.patch({'plan': plan_id, 'status': 'closed',
            'summary': old.meta.get('summary', ''), 'verify': old.meta.get('verify', []),
            'before': old.meta.get('before', []), 'after': old.meta.get('after', []),
            'artifacts_retained': list(dict.fromkeys(exp.meta.get('artifacts_retained', []) + old.meta.get('artifacts_retained', [])))},
            {'Approach': exp.section('Approach') or old.section('Goal'), 'Notes': notes,
             'Before / After': old.section('Before / After'), 'Verification': verification,
             'Conclusion': exp.section('Conclusion') or old.section('Final summary'),
             'Review': exp.section('Review') or (review_match[1].strip() if review_match else '')})))
    # Rewrite references in existing work records, not screenshots or old recovery material.
    for doc in docs.values():
        if doc.path != 'PROJECT.md' and doc.path not in changes:
            text = remap(doc.patch({'follow_up_tasks': None}) if doc.meta.get('follow_up_tasks') is not None else doc.raw)
            if text != doc.raw:
                add(doc.path, text)
    project = docs['PROJECT']
    header = re.sub(r'^tasks\s*=.*\n?', '', project.header, flags=re.M)
    add('PROJECT.md', '+++\n' + header.strip() + '\n+++\n\n' + remap(project.body))
    seq = store.path('.project/ids.toml')
    import tomllib
    counters = tomllib.loads(seq.read_text(encoding='utf-8')) if seq.exists() else {}
    counters.pop('TASK', None)
    counters['PLAN'] = max(counters.get('PLAN', 0), 3)
    counters['EXP'] = max(counters.get('EXP', 0), 6)
    add('.project/ids.toml', ''.join(f'{k} = {scalar(v)}\n' for k, v in counters.items()))
    add('.project/config.toml', 'schema_version = 2\n')
    with store.locked():
        recovery.mkdir(parents=True, exist_ok=True)
        shutil.copy2(store.path('PROJECT.md'), recovery / 'PROJECT.md')
        for doc in docs.values():
            if doc.path in changes and doc.path != 'PROJECT.md':
                dest = recovery / doc.path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(store.path(doc.path), dest)
        # Binary evidence is copied byte-for-byte before retiring the original directory.
        for old_id in originals:
            assets = source / (old_id + '.assets')
            if assets.exists():
                dest = store.path(path_map[f'.project/tasks/{old_id}.assets'])
                if dest.exists():
                    raise ValueError('Evidence destination already exists: ' + str(dest))
                shutil.copytree(assets, dest)
        shutil.move(str(source), str(backup))
        try:
            projected, errors = store.load(changes)
            errors += validate(store, projected, changes)
            if errors:
                raise ValueError('\n'.join(errors))
            store.commit_locked(changes, expected)
        except Exception:
            shutil.move(str(backup), str(source))
            raise
        old_template = store.path('.project/templates/task.md')
        if old_template.exists():
            shutil.move(str(old_template), str(recovery / 'task-template.md'))
        (recovery / 'mapping.json').write_text(json.dumps(MAPPING, ensure_ascii=False, indent=2), encoding='utf-8')
    return MAPPING


if __name__ == '__main__':
    print(json.dumps(migrate(sys.argv[1] if len(sys.argv) > 1 else '.'), ensure_ascii=False, indent=2))
