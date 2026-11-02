"""Build a wheel and an offline local-use bundle, without publishing or downloading."""
from pathlib import Path
import hashlib
import subprocess
import sys
import zipfile

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from project_infra import __version__

dist = root / 'dist'
dist.mkdir(exist_ok=True)
subprocess.run([sys.executable, '-m', 'pip', 'wheel', str(root), '--no-deps',
                '--no-build-isolation', '--no-index', '--wheel-dir', str(dist)], check=True)
wheel = dist / f'project_infra-{__version__}-py3-none-any.whl'
with zipfile.ZipFile(wheel) as archive:
    names = archive.namelist()
    assert all(n.startswith(('project_infra/', f'project_infra-{__version__}.dist-info/')) for n in names)
    for static in (root / 'project_infra/static').iterdir():
        if static.is_file():
            assert 'project_infra/static/' + static.name in names, static.name
bundle = dist / f'project-infra-{__version__}-local.zip'
with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
    archive.write(wheel, wheel.name)
    archive.write(root / 'scripts/install-local.ps1', 'install-local.ps1')
    archive.write(root / 'docs/local-use.md', '使用说明.md')
checksum = hashlib.sha256(bundle.read_bytes()).hexdigest()
bundle.with_suffix('.zip.sha256').write_text(checksum + '  ' + bundle.name + '\n', encoding='ascii')
print('Local bundle:', bundle)
print('SHA256:', checksum)
