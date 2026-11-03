"""Shared semantic validation. Presence checks never imply scientific validity."""
import re
import tomllib
from .documents import KINDS, STATES, RESOLUTIONS


def kind_of(doc):
    return next((k for k, (_, folder) in KINDS.items() if doc.path.startswith(f'.project/{folder}/')), None)


def mainline(doc):
    result = []
    for node in doc.meta.get('mainline', []):
        item = dict(node)
        section = item.get('section', '')
        marker = re.search(r'<a\s+id=[\"\u0027]' + re.escape(section) + r'[\"\u0027]\s*></a>\s*\n## ([^\n]+)', doc.body)
        item['title'] = marker[1] if marker else section
        content = doc.section(item['title']) if marker else ''
        item['content'] = re.sub(r'\s*<a\s+id=[\"\u0027][^\"\u0027]+[\"\u0027]\s*></a>\s*$', '', content)
        result.append(item)
    return result


def library(store, overrides=None):
    relative = 'library/index.toml'
    text = (overrides or {}).get(relative)
    if text is None:
        text = store.path(relative).read_text(encoding='utf-8-sig')
    return tomllib.loads(text).get('entry', [])


def validate(store, docs, overrides=None):
    errors = []
    def error(where, message):
        errors.append(f'{where}: {message}')
    def refs(doc, field, prefix=None):
        values = doc.meta.get(field, [])
        if not isinstance(values, list) or any(not isinstance(x, str) for x in values):
            error(doc.path, field + ' must be a string array')
            return []
        for target in values:
            if target not in docs or (prefix and not target.startswith(prefix + '-')):
                error(doc.path, f'{field}: invalid reference {target}')
        return values
    project = docs.get('PROJECT')
    nodes = []
    try:
        nodes = mainline(project) if project else []
        ids = [n['id'] for n in nodes]
        if len(set(ids)) != len(ids):
            error('PROJECT.md', 'Duplicate mainline IDs')
        graph = {n['id']: n.get('after', []) for n in nodes}
        for n in nodes:
            if not n['content']:
                error('PROJECT.md', f'Missing or empty anchored section: {n.get("section")}')
            for pred in n.get('after', []):
                if pred not in graph:
                    error('PROJECT.md', f'Unknown predecessor: {pred}')
            if n.get('tasks'):
                error('PROJECT.md', 'Retired task references must be migrated to Plans and Experiments')
            for ref in n.get('sources', []):
                if ref not in docs:
                    error('PROJECT.md', f'Unknown source: {ref}')
        visited, active = set(), set()
        def visit(key):
            if key in active:
                raise ValueError('Mainline contains a cycle')
            if key in visited or key not in graph:
                return
            active.add(key)
            for pred in graph[key]:
                visit(pred)
            active.remove(key)
            visited.add(key)
        for key in graph:
            visit(key)
    except (KeyError, TypeError, ValueError) as exc:
        error('PROJECT.md', str(exc))
    library_ids = set()
    try:
        entries = library(store, overrides)
        for entry in entries:
            ident = entry['id']
            if ident in library_ids:
                error('library/index.toml', 'Duplicate ID ' + ident)
            library_ids.add(ident)
            location = entry['location']
            if not location.startswith(('https://', 'http://')) and not store.path('library/' + location).is_file():
                error('library/index.toml', 'Missing file ' + location)
    except (ValueError, OSError, TypeError, KeyError) as exc:
        error('library/index.toml', str(exc))
    for ident, doc in docs.items():
        kind = kind_of(doc)
        if not kind:
            continue
        m, status = doc.meta, doc.meta.get('status')
        prefix = KINDS[kind][0]
        if not isinstance(ident, str) or not re.fullmatch(prefix + r'-\d{4,}', ident) or doc.path.split('/')[-1] != ident + '.md':
            error(doc.path, 'ID must match its filename and kind (e.g. PLAN-0001)')
        for field in ('title', 'summary'):
            if not isinstance(m.get(field, ''), str) or (field == 'title' and not m.get(field, '').strip()):
                error(doc.path, field + ' must be text; title cannot be empty')
        if kind != 'proposal' and status not in STATES[kind]:
            error(doc.path, 'Invalid status')
        for field in ('references',):
            vals = m.get(field, [])
            if not isinstance(vals, list) or any(x not in library_ids for x in vals):
                error(doc.path, 'Unknown Library reference')
        if kind == 'proposal':
            refs(doc, 'plans', 'PLAN')
        if kind == 'plan':
            refs(doc, 'experiments', 'EXP')
            refs(doc, 'follow_up_plans', 'PLAN')
            if m.get('follow_up_tasks'):
                error(doc.path, 'Retired task references must be migrated')
            if m.get('proposal'):
                prop = docs.get(m['proposal'])
                if not prop or kind_of(prop) != 'proposal' or ident not in prop.meta.get('plans', []):
                    error(doc.path, 'Proposal link must be reciprocal')
            for exp_id in m.get('experiments', []) if isinstance(m.get('experiments', []), list) else []:
                if exp_id in docs and docs[exp_id].meta.get('plan') != ident:
                    error(doc.path, f'{exp_id} belongs to a different Plan')
            if status != 'closed' and 'resolution' in m:
                error(doc.path, 'Only closed Plans have a resolution')
            if status == 'closed':
                if m.get('resolution') != 'abandoned':
                    from .execution import shared_step_error
                    if issue := shared_step_error(doc):
                        error(doc.path, issue)
                if m.get('resolution') not in RESOLUTIONS:
                    error(doc.path, 'Closed Plan needs a valid resolution')
                if not doc.section('Synthesis'):
                    error(doc.path, 'Closed Plan needs Synthesis')
                if m.get('resolution') in ('supported', 'refuted') and not m.get('experiments'):
                    error(doc.path, 'Supported/refuted Plan needs an Experiment')
                if m.get('resolution') != 'abandoned' and not (doc.section('Review') or doc.section('Delivery')):
                    error(doc.path, 'Delivered conclusion needs Review or an explicit Delivery record without independent review')
            for path in m.get('project_docs_updated', []):
                if not store.path(path).is_file() and path not in (overrides or {}):
                    error(doc.path, 'Missing Project Doc ' + path)
            anchor = m.get('design_anchor')
            if anchor and anchor not in ['PROJECT.md#' + n['section'] for n in nodes]:
                error(doc.path, 'Unknown design_anchor')
        if kind == 'experiment':
            plan = docs.get(m.get('plan'))
            if not plan or kind_of(plan) != 'plan' or ident not in plan.meta.get('experiments', []):
                error(doc.path, 'Experiment needs a reciprocal parent Plan')
            predecessors = refs(doc, 'predecessors', 'EXP')
            if len(set(predecessors)) != len(predecessors):
                error(doc.path, 'predecessors must not contain duplicates')
            for pred in predecessors:
                if pred == ident:
                    error(doc.path, 'Experiment cannot follow itself')
                elif pred in docs and docs[pred].meta.get('plan') != m.get('plan'):
                    error(doc.path, 'Experiment predecessor must belong to the same Plan')
            if status == 'closed' and not doc.section('Conclusion'):
                error(doc.path, 'Closed Experiment needs Conclusion')
            if 'run' in m and (not isinstance(m['run'], str) or not m['run'].strip()):
                error(doc.path, 'run must be a nonempty command')
        if kind in ('plan', 'experiment'):
            commands = m.get('verify', [])
            if not isinstance(commands, list) or any(not isinstance(c, str) for c in commands):
                error(doc.path, 'verify must be a command array')
            ac = re.findall(r'^\s*- \[([ xX])\]\s+(.+)', doc.section('Acceptance criteria'), re.M)
            if kind == 'plan' and status == 'closed' and m.get('resolution') != 'abandoned':
                if ac and any(x[0].lower() != 'x' for x in ac):
                    error(doc.path, 'All acceptance criteria must be checked')
        before, after = m.get('before', []), m.get('after', [])
        if not isinstance(before, list) or not isinstance(after, list) or len(before) != len(after):
            error(doc.path, 'Before / After must be paired arrays')
        for field in ('evidence', 'before', 'after', 'artifacts_retained', 'artifacts_promoted'):
            paths = m.get(field, [])
            if not isinstance(paths, list) or any(not isinstance(path, str) or not path.strip() for path in paths):
                error(doc.path, field + ' must be an array of nonempty artifact paths or links')
                continue
            for path in paths:
                try:
                    if not path.startswith(('https://', 'http://')) and not store.path(path).is_file():
                        error(doc.path, 'Missing artifact ' + path)
                except (ValueError, AttributeError) as exc:
                    error(doc.path, str(exc))
    # Ownership remains Plan -> experiments; predecessors record only actual exploration lineage.
    experiment_graph = {key: doc.meta.get('predecessors', []) for key, doc in docs.items()
                        if kind_of(doc) == 'experiment'}
    done, visiting = set(), set()
    def visit_experiment(key):
        if key in visiting:
            raise ValueError('Experiment lineage contains a cycle')
        if key in done or key not in experiment_graph:
            return
        visiting.add(key)
        predecessors = experiment_graph[key]
        if isinstance(predecessors, list):
            for pred in predecessors:
                if isinstance(pred, str):
                    visit_experiment(pred)
        visiting.remove(key)
        done.add(key)
    try:
        for key in experiment_graph:
            visit_experiment(key)
    except ValueError as exc:
        error('.project/experiments', str(exc))
    if store.path('.project/transaction.json').exists():
        error('.project/transaction.json', 'Unfinished transaction; inspect recovery journal')
    ignore = store.path('.gitignore')
    if not ignore.exists() or '.work/' not in ignore.read_text(encoding='utf-8'):
        error('.gitignore', '.work/ must be ignored')
    return errors
