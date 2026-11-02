"""Compile the existing portable distribution into a current-user Windows installer."""
from pathlib import Path
import argparse
import hashlib
import subprocess
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from project_infra import __version__
parser = argparse.ArgumentParser()
parser.add_argument('--compiler', required=True, type=Path)
args = parser.parse_args()
payload = root / 'dist/portable/ProjectInfra'
if not (payload / 'ProjectInfra.exe').is_file():
    raise SystemExit('Build the portable application first with scripts/build_portable.py')
if (payload / 'settings.json').exists():
    raise SystemExit('Distribution contains local recent-project settings; rebuild a clean portable payload')
subprocess.run([str(args.compiler.resolve()), '/Qp', '/DSourceDir=' + str(payload), '/DProductVersion=' + __version__,
                str(root / 'installer/ProjectInfra.iss')], check=True)
output = root / f'dist/ProjectInfra-{__version__}-Setup.exe'
output.with_suffix('.exe.sha256').write_text(hashlib.sha256(output.read_bytes()).hexdigest() + '  ' + output.name + '\n', encoding='ascii')
print('Local installer:', output)
