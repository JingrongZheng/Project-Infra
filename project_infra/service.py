"""Application commands shared by CLI and Web UI."""
import json
import re
import subprocess
import tomllib
from datetime import datetime, timezone

from .documents import Document, KINDS, SECTIONS, STATES, digest, scalar, template
from .store import Conflict
from .validation import kind_of, library, mainline, validate


class Service:
    def __init__(self, store):
        self.store = store

    def checked(self, overrides=None):
        docs, errors = self.store.load(overrides)
        try:
            errors += validate(self.store, docs, overrides)
        except (ValueError, KeyError, TypeError, AttributeError) as exc:
            errors.append('Malformed project data: ' + str(exc))
        return docs, errors

    def require_valid(self, changes):
        _, errors = self.checked(changes)
        if errors:
            raise ValueError('\n'.join(errors))

    def update(self, path, expected_revision, fields=None, sections=None, raw=None):
        if not self.store.editable(path):
            raise ValueError('This file is not editable from the application')
        with self.store.locked():
            old = self.store.read(path) if path.endswith('.md') else None
            data = self.store.path(path).read_bytes()
            if digest(data) != expected_revision:
                raise Conflict('File changed; reload before saving. Your edits have not been discarded.')
            text = raw if raw is not None else old.patch(fields, sections)
            candidate = Document(path, text, '') if old else None
            if (old and kind_of(old) == 'plan' and old.meta.get('status') != 'closed'
                    and candidate.meta.get('status') == 'closed' and candidate.meta.get('resolution') != 'abandoned'):
                from .review import require_delivery
                from .reviewer_runtime import status
                message = require_delivery(self, old.meta['id'])
                if status(self.store).get('enabled'):
                    old_meta = {k: v for k, v in old.meta.items() if k not in ('status', 'resolution')}
                    new_meta = {k: v for k, v in candidate.meta.items() if k not in ('status', 'resolution')}
                    if old_meta != new_meta or old.body.strip() != candidate.body.strip():
                        raise ValueError('先保存候选方案内容，再审查，最后关闭；不能在关闭时修改审查对象')
                text = candidate.patch(sections={'Delivery': message})
            changes = {path: text}
            self.require_valid(changes)
            if old and kind_of(old) in ('plan', 'experiment'):
                new = Document(path, text, '')
                if old.meta.get('status') != 'closed' and new.meta.get('status') == 'closed' and new.meta.get('verify'):
                    old_meta = {k: v for k, v in old.meta.items() if k not in ('status', 'resolution')}
                    new_meta = {k: v for k, v in new.meta.items() if k not in ('status', 'resolution')}
                    old_body = Document(path, old.patch(sections={'Delivery': ''}), '').body.strip()
                    new_body = Document(path, new.patch(sections={'Delivery': ''}), '').body.strip()
                    if old_meta != new_meta or old_body != new_body:
                        raise ValueError('Save changed acceptance/evidence fields first, then verify, then close')
                    receipt = self.store.path(f'.work/{KINDS[kind_of(old)][1]}/{old.meta["id"]}/verification.json')
                    result = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else {}
                    if result.get('exit_code') != 0 or result.get('fingerprint') != self.store.fingerprint():
                        raise ValueError('Run verify on the current files before closing this record')
            self.store.commit_locked(changes, {path: expected_revision})
        return self.store.read(path) if path.endswith('.md') else None

    def create(self, kind, title, parent=None, anchor=None, predecessors=None):
        if kind not in KINDS or not title.strip():
            raise ValueError('Choose an object kind and nonempty title')
        with self.store.locked():
            docs, errors = self.checked()
            if errors:
                raise ValueError('\n'.join(errors))
            if kind == 'experiment' and (parent not in docs or kind_of(docs[parent]) != 'plan'):
                raise ValueError('Experiment requires --plan PLAN-ID')
            if predecessors is not None and kind != 'experiment':
                raise ValueError('predecessors are only supported for Experiments')
            if parent and parent not in docs:
                raise ValueError('Parent object does not exist')
            sequence = '.project/ids.toml'
            sequence_data = self.store.path(sequence).read_bytes() if self.store.path(sequence).exists() else None
            counters = tomllib.loads(sequence_data.decode()) if sequence_data else {}
            prefix, folder = KINDS[kind]
            highest = max([int(k.split('-')[1]) for k in docs if k.startswith(prefix + '-')] + [counters.get(prefix, 0)])
            ident = f'{prefix}-{highest + 1:04d}'
            counters[prefix] = highest + 1
            path = f'.project/{folder}/{ident}.md'
            document = Document(path, template(kind, ident, title), '')
            fields, changes, expected = {}, {}, {path: None, sequence: digest(sequence_data) if sequence_data else None}
            if predecessors is not None:
                fields['predecessors'] = predecessors
            if anchor and kind == 'plan':
                fields['design_anchor'] = anchor
            if parent:
                owner = docs[parent]
                owner_kind = kind_of(owner)
                relation = None
                if kind == 'experiment' and owner_kind == 'plan':
                    fields['plan'] = parent
                    relation = 'experiments'
                elif kind == 'plan' and owner_kind == 'proposal':
                    fields['proposal'] = parent
                    relation = 'plans'
                elif kind == 'plan' and owner_kind == 'plan':
                    relation = 'follow_up_plans'
                else:
                    raise ValueError('Unsupported parent relationship')
                changes[owner.path] = owner.patch({relation: owner.meta.get(relation, []) + [ident]})
                expected[owner.path] = owner.revision
            changes[path] = document.patch(fields)
            changes[sequence] = '\n'.join(f'{k} = {v}' for k, v in counters.items()) + '\n'
            self.require_valid(changes)
            self.store.commit_locked(changes, expected)
            return ident

    def execute(self, ident, verification=False):
        docs, errors = self.checked()
        if errors:
            raise ValueError('\n'.join(errors))
        doc = docs[ident]
        kind = kind_of(doc)
        if (verification and kind not in ('plan', 'experiment')) or (not verification and kind != 'experiment'):
            raise ValueError('verify requires Plan or Experiment; run requires Experiment')
        commands = doc.meta.get('verify', []) if verification else [doc.meta.get('run')]
        if not commands or not all(commands):
            raise ValueError('No executable entry point is retained for this object')
        before = self.store.fingerprint()
        exit_code = 0
        for command in commands:
            print('$ ' + command, flush=True)
            exit_code = subprocess.call(command, shell=True, cwd=self.store.root)
            if exit_code:
                break
        after = self.store.fingerprint()
        if after != before and not exit_code:
            print('Source changed during verification; run again against stable files.', flush=True)
            exit_code = 1
        if verification:
            receipt = self.store.path(f'.work/{KINDS[kind][1]}/{ident}/verification.json')
            receipt.parent.mkdir(parents=True, exist_ok=True)
            receipt.write_text(json.dumps({'exit_code': exit_code, 'fingerprint': after,
                                           'commands': commands, 'time': datetime.now(timezone.utc).isoformat()}), encoding='utf-8')
        return exit_code

    def context(self, ident, full=False, reviewer=False):
        docs, errors = self.checked()
        if ident not in docs:
            raise ValueError('Unknown object ' + ident)
        doc = docs[ident]
        chunks = []
        for path in ('AGENTS.md', 'PROJECT.md', 'knowledge/index.md', 'TOOLKIT.md'):
            p = self.store.path(path)
            if p.exists():
                chunks.append(f'# {path}\n' + self.store.read(path).body)
        if errors:
            chunks.append('# Diagnostics\n' + '\n'.join(errors))
        if reviewer:
            from .reviewer_runtime import status
            chunks.append('# Reviewer capability\n' + json.dumps(status(self.store), ensure_ascii=False))
            p = self.store.path('docs/reviewer.md')
            if p.exists():
                chunks.append('# Reviewer initialization\n' + p.read_text(encoding='utf-8'))
        chunks.append('# ' + ident + '\n' + doc.raw)
        if reviewer:
            from .review import history
            for related in [doc] + [item for item in docs.values()
                    if kind_of(doc) == 'plan' and item.meta.get('plan') == ident]:
                rounds = history(self.store, related.meta['id'])
                if rounds:
                    chunks.append('# 历轮审查原始记录 ' + related.meta['id'] + '\n' + '\n'.join(
                        f'{r["round"]} · {r["time"]} · {r["note"]}' for r in rounds))
        selected = set()
        if kind_of(doc) == 'plan':
            if doc.meta.get('proposal'):
                selected.add(doc.meta['proposal'])
            selected.update(doc.meta.get('experiments', []))
        if kind_of(doc) == 'experiment':
            selected.add(doc.meta.get('plan'))
            selected.update(doc.meta.get('predecessors', []))
            selected.update(key for key, item in docs.items() if kind_of(item) == 'experiment'
                            and ident in item.meta.get('predecessors', []))
        if kind_of(doc) in ('plan', 'experiment'):
            plan_id = ident if kind_of(doc) == 'plan' else doc.meta.get('plan')
            lineage = [item for item in docs.values()
                       if kind_of(item) == 'experiment' and item.meta.get('plan') == plan_id]
            chunks.append('# Exploration lineage (predecessors = based on preceding results)\n' + '\n'.join(
                f'{item.meta["id"]} <- {", ".join(item.meta.get("predecessors", [])) or plan_id}: '
                f'{item.meta.get("title")}; status: {item.meta.get("status")}' for item in lineage))
        references = set(doc.meta.get('references', []))
        for key in sorted(x for x in selected if x in docs):
            item = docs[key]
            references.update(item.meta.get('references', []))
            if full:
                chunks.append('# ' + key + '\n' + item.raw)
            else:
                summary = item.meta.get('summary') or '(No summary: open this object)'
                chunks.append(f'# {key}: {item.meta.get("title")}\n{summary}\n'
                              f'File: {item.path}; status: {item.meta.get("status", "—")}')
                if item.section('Continuation').strip():
                    chunks.append('Continuation: ' + item.section('Continuation'))
                if reviewer:
                    for section_name in ('Conclusion', 'Verification', 'Review'):
                        if item.section(section_name).strip():
                            chunks.append(section_name + ': ' + item.section(section_name))
                if kind_of(item) == 'experiment' and item.meta.get('before'):
                    chunks.append('Before / After: ' + json.dumps(
                        list(zip(item.meta.get('before', []), item.meta.get('after', []))), ensure_ascii=False))
                if kind_of(item) == 'experiment' and (item.meta.get('evidence') or item.section('Results')):
                    chunks.append('Results: ' + item.section('Results') + '\nEvidence: ' +
                                  json.dumps(item.meta.get('evidence', []), ensure_ascii=False))
                if kind_of(item) == 'plan':
                    for exp_id in item.meta.get('experiments', []):
                        exp = docs.get(exp_id)
                        if exp:
                            chunks.append(f'  {exp_id} <- {", ".join(exp.meta.get("predecessors", [])) or key}: '
                                          f'{exp.meta.get("title")}\n  {exp.meta.get("summary", "")}\n  File: {exp.path}')
        # Follow only explicitly promoted knowledge, never load the entire knowledge tree.
        knowledge_paths = set()
        for item in [doc] + [docs[key] for key in selected if key in docs]:
            for field in ('project_docs_updated', 'artifacts_promoted'):
                paths = item.meta.get(field, [])
                for path in paths if isinstance(paths, list) else []:
                    if isinstance(path, str) and path.startswith('knowledge/') and path.endswith('.md'):
                        knowledge_paths.add(path)
        for path in sorted(knowledge_paths - {'knowledge/index.md'}):
            p = self.store.path(path)
            if p.is_relative_to(self.store.path('knowledge')) and p.is_file():
                chunks.append('# Knowledge: ' + path + '\n' + p.read_text(encoding='utf-8'))
        for ref in library(self.store):
            if ref['id'] in references:
                chunks.append('# Reference\n' + json.dumps(ref, ensure_ascii=False))
        folder = KINDS[kind_of(doc)][1]
        handoff = self.store.path(f'.work/{folder}/{ident}/HANDOFF.md')
        if handoff.exists():
            chunks.append('# Handoff\n' + handoff.read_text(encoding='utf-8'))
        chunks.append('\nRead the listed files for details; the compact outline is navigation, not proof.')
        return '\n\n'.join(chunks)

    def state(self):
        from .reviewer_runtime import status
        docs, errors = self.checked()
        objects = []
        for ident, doc in docs.items():
            kind = kind_of(doc)
            if kind:
                objects.append({'kind': kind, 'path': doc.path, 'revision': doc.revision,
                                'meta': doc.meta, 'sections': {s[0]: doc.section(s[0]) for s in doc.section_spans()}})
        project = docs.get('PROJECT')
        toolkit = docs.get('TOOLKIT')
        try:
            nodes = mainline(project) if project else []
        except (KeyError, TypeError, ValueError):
            nodes = []
        try:
            entries = library(self.store)
        except (OSError, ValueError, TypeError):
            entries = []
        return {'objects': objects, 'mainline': nodes, 'library': entries, 'errors': errors,
                'reviewer': status(self.store),
                'toolkit': {'path': 'TOOLKIT.md', 'revision': toolkit.revision, 'body': toolkit.body} if toolkit else None,
                'project': {'path': 'PROJECT.md', 'revision': project.revision, 'body': project.body} if project else None,
                'states': STATES, 'root': str(self.store.root)}
