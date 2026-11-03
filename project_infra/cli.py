import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from .bootstrap import initialize
from .documents import KINDS
from .service import Service
from .store import Store
from .validation import kind_of
from . import __version__


def project_root(explicit=None, initializing=False):
    if explicit is not None:
        root = Path(explicit).resolve()
    else:
        root = Path.cwd().resolve()
        if not initializing:
            root = next((p for p in (root, *root.parents)
                         if (p / '.project/config.toml').is_file()), root)
    if not initializing and not (root / '.project/config.toml').is_file():
        raise ValueError('No initialized project found. Run project-infra init in the project directory, '
                         'or use project-infra --root PATH <command>.')
    return root


def main(argv=None):
    # Keep Unicode project records readable in Windows consoles and redirected output.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', errors='replace')
    parser = argparse.ArgumentParser(description='Project Infra — 文件即项目记录')
    parser.add_argument('--version', action='version', version=__version__)
    parser.add_argument('--root', help='Managed project directory (otherwise discover from current directory)')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('validate')
    sub.add_parser('status')
    p = sub.add_parser('reviewer', help='Current environment reviewer capability self-check')
    p.add_argument('action', choices=('status', 'probe', 'check', 'accept', 'disable'))
    p.add_argument('--label', default='host reviewer')
    p.add_argument('--command-file', help='Local JSON file containing adapter argv (no shell string)')
    p.add_argument('--response', help='JSON response from the host-created independent session')
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--reason', default='当前环境未接入独立审查会话')
    p = sub.add_parser('deliver', help='Explicit delivery checkpoint; invoke review only here')
    p.add_argument('id')
    p = sub.add_parser('new')
    p.add_argument('kind', choices=KINDS)
    p.add_argument('--title', required=True)
    p.add_argument('--plan', '--from-plan', '--proposal', dest='parent')
    p.add_argument('--anchor')
    p.add_argument('--after', nargs='*', help='Experiment predecessors; multiple IDs form a merge')
    p = sub.add_parser('list')
    p.add_argument('kind', nargs='?')
    p.add_argument('--status')
    p.add_argument('--plan')
    p.add_argument('--json', action='store_true')
    for name in ('show', 'context', 'review', 'run', 'verify', 'close'):
        p = sub.add_parser(name)
        p.add_argument('id')
        if name in ('context', 'review'):
            p.add_argument('--full', action='store_true')
            p.add_argument('--reviewer', action='store_true')
        if name == 'review':
            group = p.add_mutually_exclusive_group()
            group.add_argument('--prepare', action='store_true', help='Prepare a context and blank note for an independent reviewer')
            group.add_argument('--record', metavar='NOTE', help='Import a completed note from a prepared handoff')
        if name == 'close':
            p.add_argument('--resolution')
    p = sub.add_parser('edit')
    p.add_argument('id')
    p.add_argument('--status')
    p.add_argument('--summary')
    p.add_argument('--section')
    p.add_argument('--text')
    p.add_argument('--text-file')
    p.add_argument('--after', nargs='*', help='Replace Experiment predecessors; no IDs clears them')
    p = sub.add_parser('search')
    p.add_argument('query')
    p = sub.add_parser('serve')
    p.add_argument('--port', type=int, default=8765)
    args = parser.parse_args(argv)
    try:
        store = Store(project_root(args.root, initializing=args.command == 'init'))
        service = Service(store)
        if args.command == 'init':
            print('\n'.join(initialize(store)) or 'Existing files preserved.')
            return 0
        if args.command == 'serve':
            from .web import serve
            from .desktop import application_mutex
            with application_mutex():
                serve(service, args.port)
            return 0
        if args.command == 'new':
            print(service.create(args.kind, args.title, args.parent, args.anchor, args.after))
            return 0
        if args.command == 'reviewer':
            from . import reviewer_runtime as runtime
            if args.action == 'status':
                result = runtime.status(store)
            elif args.action == 'disable':
                result = runtime.disable(store, args.reason)
            elif args.action == 'accept':
                if not args.response:
                    raise ValueError('accept requires --response FILE')
                response_path = Path(args.response) if Path(args.response).is_absolute() else store.path(args.response)
                result = runtime.accept(store, json.loads(response_path.read_text(encoding='utf-8-sig')))
            else:
                if args.action == 'check' and not args.command_file:
                    raise ValueError('check requires --command-file FILE; use probe for a host/subagent handshake')
                command = json.loads(Path(args.command_file).read_text(encoding='utf-8-sig')) if args.command_file else None
                result = runtime.probe(store, args.label, command, args.timeout)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == 'deliver':
            from .review import deliver
            print(json.dumps(deliver(service, args.id), ensure_ascii=False, indent=2))
            return 0
        docs, errors = service.checked()
        if args.command == 'validate':
            print('\n'.join(errors) if errors else 'OK — files, states, references and mainline are valid.')
            return 1 if errors else 0
        if args.command == 'status':
            from .reviewer_runtime import status
            print('Reviewer:', json.dumps(status(store), ensure_ascii=False))
            for kind in KINDS:
                print(kind, dict(Counter(d.meta.get('status', 'inbox') for d in docs.values() if kind_of(d) == kind)))
            print('Diagnostics:', len(errors))
            return 1 if errors else 0
        if args.command == 'list':
            rows = [{'kind': kind_of(d), 'path': d.path, **d.meta} for d in docs.values() if kind_of(d)]
            if args.kind:
                singular = args.kind.rstrip('s')
                if singular not in KINDS:
                    raise ValueError('Unknown object kind')
                rows = [r for r in rows if r['kind'] == singular]
            if args.status:
                rows = [r for r in rows if r.get('status') == args.status]
            if args.plan:
                rows = [r for r in rows if r.get('plan') == args.plan]
            if args.json:
                print(json.dumps(rows, ensure_ascii=False, indent=2))
            else:
                for row in rows:
                    print(row['id'], row.get('status', 'inbox'), row['title'])
            return 0
        if args.command == 'search':
            candidates = [d.path for d in docs.values()]
            candidates += ['AGENTS.md', 'library/index.toml']
            candidates += [p.relative_to(store.root).as_posix() for p in store.path('docs').rglob('*.md')]
            for path in dict.fromkeys(candidates):
                if not store.path(path).is_file():
                    continue
                for line, text in enumerate(store.path(path).read_text(encoding='utf-8-sig').splitlines(), 1):
                    if args.query.casefold() in text.casefold():
                        print(f'{path}:{line}: {text}')
            return 0
        if args.command in ('run', 'verify'):
            return service.execute(args.id, args.command == 'verify')
        if args.command in ('context', 'review'):
            if args.command == 'review' and args.prepare:
                from .review import prepare
                print(prepare(service, args.id))
            elif args.command == 'review' and args.record:
                from .review import record
                print('Recorded review:', record(service, args.id, args.record))
            else:
                print(service.context(args.id, args.full, args.reviewer or args.command == 'review'))
            return 0
        doc = docs.get(args.id)
        if not doc:
            raise ValueError('Unknown object ID')
        if args.command == 'show':
            print(doc.raw)
        elif args.command in ('edit', 'close'):
            fields, sections = {}, {}
            if args.command == 'close':
                fields['status'] = 'closed'
                if args.resolution:
                    fields['resolution'] = args.resolution
            else:
                if args.status:
                    fields['status'] = args.status
                    if kind_of(doc) == 'plan' and args.status != 'closed':
                        fields['resolution'] = None
                if args.summary is not None:
                    fields['summary'] = args.summary
                if args.after is not None:
                    if kind_of(doc) != 'experiment':
                        raise ValueError('--after is only supported for Experiments')
                    fields['predecessors'] = args.after
                if args.section:
                    if args.text is None and not args.text_file:
                        raise ValueError('--section requires --text or --text-file')
                    sections[args.section] = Path(args.text_file).read_text(encoding='utf-8') if args.text_file else args.text
            service.update(doc.path, doc.revision, fields, sections)
            print('Updated', args.id)
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
