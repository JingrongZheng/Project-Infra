"""Filesystem storage and recoverable, optimistic file transactions."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import threading
import time
import uuid

from .documents import Document, KINDS, digest


class Conflict(ValueError):
    pass


class Store:
    def __init__(self, root):
        self.root = Path(root).resolve()
        self.mutex = threading.RLock()

    def path(self, relative):
        p = (self.root / relative).resolve()
        if not p.is_relative_to(self.root):
            raise ValueError('Path leaves the project')
        return p

    def read(self, relative):
        return Document.from_bytes(relative, self.path(relative).read_bytes())

    def load(self, overrides=None):
        docs, errors = {}, []
        overrides = overrides or {}
        paths = ['PROJECT.md']
        if self.path('TOOLKIT.md').exists():
            paths.append('TOOLKIT.md')
        for _, directory in KINDS.values():
            paths += [p.relative_to(self.root).as_posix() for p in sorted(self.path(f'.project/{directory}').glob('*.md'))]
        paths += [p for p in overrides if p not in paths and p.endswith('.md')]
        if any(self.path('.project/tasks').glob('*.md')):
            errors.append('Legacy Task files found: migrate them before editing; they are not silently ignored')
        for path in paths:
            try:
                data = overrides[path].encode('utf-8') if path in overrides else self.path(path).read_bytes()
                doc = Document.from_bytes(path, data)
                key = path[:-3] if path in ('PROJECT.md', 'TOOLKIT.md') else doc.meta.get('id', path)
                if key in docs:
                    raise ValueError('Duplicate object ID: ' + key)
                docs[key] = doc
            except (ValueError, OSError) as exc:
                errors.append(f'{path}: {exc}')
        return docs, errors

    @contextmanager
    def locked(self):
        with self.mutex:
            lock = self.path('.project/.write.lock')
            lock.parent.mkdir(parents=True, exist_ok=True)
            try:
                fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            except FileExistsError as exc:
                raise Conflict('Project write lock exists; inspect it before recovery') from exc
            try:
                os.write(fd, f'{os.getpid()} {time.time()}'.encode())
                os.close(fd)
                if self.path('.project/transaction.json').exists():
                    raise Conflict('Unfinished transaction; inspect .project/transaction.json')
                yield
            finally:
                lock.unlink(missing_ok=True)

    def commit_locked(self, changes, expected):
        originals, staged = {}, {}
        for relative, text in changes.items():
            p = self.path(relative)
            old = p.read_bytes() if p.exists() else None
            actual = digest(old) if old is not None else None
            if actual != expected.get(relative):
                raise Conflict(f'{relative} changed since it was read; reload and retry')
            originals[relative] = old
            p.parent.mkdir(parents=True, exist_ok=True)
            temp = p.with_name(p.name + '.' + uuid.uuid4().hex + '.infra-tmp')
            with temp.open('wb') as f:
                f.write(text.encode('utf-8'))
                f.flush()
                os.fsync(f.fileno())
            staged[relative] = temp
        journal = self.path('.project/transaction.json')
        journal.write_text(json.dumps({'originals': {k: v.decode('utf-8') if v else None for k, v in originals.items()},
                                       'files': list(changes)}, ensure_ascii=False), encoding='utf-8')
        replaced = []
        try:
            for relative, temp in staged.items():
                p = self.path(relative)
                actual = digest(p.read_bytes()) if p.exists() else None
                if actual != expected.get(relative):
                    raise Conflict(f'{relative} was modified during write; transaction stopped')
                os.replace(temp, p)
                replaced.append(relative)
        except Exception:
            for relative in reversed(replaced):
                p = self.path(relative)
                # Do not roll back over a third party's subsequent changes.
                if digest(p.read_bytes()) != digest(changes[relative].encode('utf-8')):
                    raise Conflict('Concurrent external write; retain transaction journal for manual recovery')
                old = originals[relative]
                if old is None:
                    p.unlink()
                else:
                    temp = p.with_name(p.name + '.rollback.infra-tmp')
                    temp.write_bytes(old)
                    os.replace(temp, p)
            journal.unlink(missing_ok=True)
            raise
        else:
            journal.unlink()
        finally:
            for temp in staged.values():
                temp.unlink(missing_ok=True)

    def editable(self, path):
        if path in ('PROJECT.md', 'TOOLKIT.md', 'library/index.toml'):
            return True
        p = Path(path)
        return len(p.parts) == 3 and p.parts[0] == '.project' and p.parts[1] in {x[1] for x in KINDS.values()} and p.suffix == '.md'

    def fingerprint(self):
        # Stable snapshot of source and project records. Ignore only generated runtime state.
        h = __import__('hashlib').sha256()
        for p in sorted(self.root.rglob('*')):
            rel = p.relative_to(self.root)
            if any(x in ('.git', '.work', '__pycache__', '.venv', 'node_modules') for x in rel.parts):
                continue
            if not p.is_file() or p.name.endswith('.infra-tmp') or p.name in ('.write.lock', 'transaction.json'):
                continue
            h.update(rel.as_posix().encode())
            h.update(p.read_bytes())
        return h.hexdigest()
