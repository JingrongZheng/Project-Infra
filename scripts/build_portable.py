"""Run with the isolated PyInstaller environment; creates a movable Windows app folder."""
from pathlib import Path
import hashlib
import subprocess
import sys
import zipfile
import shutil
import json
from build_support import source_digest

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from project_infra import __version__
source_hash = source_digest(root)
work = root / '.work' / 'portable-spec'
work.mkdir(parents=True, exist_ok=True)
spec = work / 'ProjectInfra.spec'
version_file = work / 'version.txt'
version_tuple = tuple(int(x) for x in __version__.split('.')) + (0,)
version_file.write_text(f'''VSVersionInfo(
 ffi=FixedFileInfo(filevers={version_tuple!r}, prodvers={version_tuple!r}, mask=0x3f, flags=0,
 OS=0x40004, fileType=0x1, subtype=0, date=(0,0)),
 kids=[StringFileInfo([StringTable('040904B0',[
 StringStruct('CompanyName','ZJR_suiliang'), StringStruct('FileDescription','Project Infra'),
 StringStruct('FileVersion',{__version__!r}), StringStruct('ProductName','Project Infra'),
 StringStruct('ProductVersion',{__version__!r})])]),
 VarFileInfo([VarStruct('Translation',[1033,1200])])])''', encoding='utf-8')
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
    console=False, debug=False, strip=False, upx=False, icon={str(root / 'project_infra/assets/pi-monogram.ico')!r}, version={str(version_file)!r})
cli_scripts = a.scripts[:-1] + [('cli_entry', {str(root / 'scripts/cli_entry.py')!r}, 'PYSOURCE')]
cli = EXE(pyz, cli_scripts, [], exclude_binaries=True, name='project-infra',
    console=True, debug=False, strip=False, upx=False, icon={str(root / 'project_infra/assets/pi-monogram.ico')!r}, version={str(version_file)!r})
collection = COLLECT(app, cli, a.binaries, a.datas, strip=False, upx=False, name='ProjectInfra')
''', encoding='utf-8')
subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--distpath', str(root / 'dist/portable'),
                '--workpath', str(root / '.work/portable-pyinstaller'), str(spec)], check=True)
app = root / 'dist/portable/ProjectInfra'
if source_digest(root) != source_hash:
    raise SystemExit('Source changed during build; rebuild before distributing')
(app / 'build-info.json').write_text(json.dumps({'version': __version__, 'source_sha256': source_hash}, indent=2), encoding='utf-8')
for notice in ['LICENSE', 'THIRD_PARTY_NOTICES.md']:
    shutil.copy2(root / notice, app / notice)
shutil.copytree(root / 'licenses', app / 'licenses', dirs_exist_ok=True)
(app / '使用说明.txt').write_text((root / 'docs/portable-use.md').read_text(encoding='utf-8'), encoding='utf-8')
bundle = root / f'dist/project-infra-{__version__}-windows-portable.zip'
with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as archive:
    for path in app.rglob('*'):
        if path.is_file():
            archive.write(path, path.relative_to(app.parent))
checksum = hashlib.sha256(bundle.read_bytes()).hexdigest()
bundle.with_suffix('.zip.sha256').write_text(checksum + '  ' + bundle.name + '\n', encoding='ascii')
print('Portable app:', bundle)
print('SHA256:', checksum)
