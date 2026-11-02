"""Run with the isolated PyInstaller environment; creates a movable Windows app folder."""
from pathlib import Path
import hashlib
import subprocess
import sys
import zipfile
import shutil

root = Path(__file__).resolve().parents[1]
work = root / '.work' / 'portable-spec'
work.mkdir(parents=True, exist_ok=True)
spec = work / 'ProjectInfra.spec'
spec.write_text(f'''
a = Analysis([{str(root / 'scripts/desktop_entry.py')!r}], pathex=[{str(root)!r}],
    datas=[({str(root / 'project_infra/static')!r}, 'project_infra/static'),
           ({str(root / 'project_infra/assets/pi-monogram.ico')!r}, 'project_infra/assets'),
           ({str(root / 'project_infra/assets/pi-monogram.png')!r}, 'project_infra/assets'),
           ({str(root / 'project_infra/assets/pi-monogram.svg')!r}, 'project_infra/assets')],
    hiddenimports=['tkinter', 'tkinter.filedialog', 'tkinter.messagebox'], hookspath=[], hooksconfig={{}},
    runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
app = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ProjectInfra',
    console=False, debug=False, strip=False, upx=False, icon={str(root / 'project_infra/assets/pi-monogram.ico')!r})
cli_scripts = a.scripts[:-1] + [('cli_entry', {str(root / 'scripts/cli_entry.py')!r}, 'PYSOURCE')]
cli = EXE(pyz, cli_scripts, [], exclude_binaries=True, name='project-infra',
    console=True, debug=False, strip=False, upx=False, icon={str(root / 'project_infra/assets/pi-monogram.ico')!r})
collection = COLLECT(app, cli, a.binaries, a.datas, strip=False, upx=False, name='ProjectInfra')
''', encoding='utf-8')
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', str(root / 'dist/portable'),
                '--workpath', str(root / '.work/portable-pyinstaller'), str(spec)], check=True)
app = root / 'dist/portable/ProjectInfra'
for notice in ['LICENSE', 'THIRD_PARTY_NOTICES.md']:
    shutil.copy2(root / notice, app / notice)
shutil.copytree(root / 'licenses', app / 'licenses', dirs_exist_ok=True)
(app / '使用说明.txt').write_text((root / 'docs/portable-use.md').read_text(encoding='utf-8'), encoding='utf-8')
bundle = root / 'dist/project-infra-0.1.0-windows-portable.zip'
with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in app.rglob('*'):
        if path.is_file():
            archive.write(path, path.relative_to(app.parent))
checksum = hashlib.sha256(bundle.read_bytes()).hexdigest()
bundle.with_suffix('.zip.sha256').write_text(checksum + '  ' + bundle.name + '\n', encoding='ascii')
print('Portable app:', bundle)
print('SHA256:', checksum)
