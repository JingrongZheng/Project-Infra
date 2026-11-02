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
        docs, errors = service.checked()
        if args.command == 'validate':
            print('\n'.join(errors) if errors else 'OK — files, states, references and mainline are valid.')
            return 1 if errors else 0
        if args.command == 'status':
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
