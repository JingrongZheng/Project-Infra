"""Shared build identity; prevents labeling stale binaries with a newer source version."""
import hashlib


def source_digest(root):
    files = [root / 'LICENSE', root / 'THIRD_PARTY_NOTICES.md',
             root / 'scripts/desktop_entry.py', root / 'scripts/cli_entry.py']
    files += [p for p in (root / 'project_infra').rglob('*') if p.is_file()
              and '__pycache__' not in p.parts and p.suffix in ('.py', '.js', '.css', '.html', '.svg', '.ico', '.png')]
    files += [p for p in (root / 'licenses').rglob('*') if p.is_file()]
    digest = hashlib.sha256()
    for path in sorted(files):
        digest.update(path.relative_to(root).as_posix().encode())
        content = path.read_bytes()
        if path.suffix not in ('.png', '.ico'):
            content = content.replace(b'\r\n', b'\n')
        digest.update(content)
    return digest.hexdigest()
