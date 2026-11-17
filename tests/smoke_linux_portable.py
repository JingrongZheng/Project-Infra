"""Exercise the frozen Linux folder with no Python installation on PATH."""
from pathlib import Path
import json
import os
import shutil
import socket
import subprocess
import sys
import tarfile
import time
from urllib.request import urlopen

if not sys.platform.startswith('linux'):
    raise SystemExit('Linux portable smoke test must run on Linux')

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from project_infra import __version__

base = root / '.work' / ('linux-portable-check-' + str(time.time_ns()))
original = base / '原位置'
original.mkdir(parents=True)
with tarfile.open(Path(sys.argv[1]).resolve(), 'r:gz') as archive:
    archive.extractall(original, filter='data')
app = original / 'ProjectInfra'
project = original / '空白 项目'
project.mkdir()
env = {k: v for k, v in os.environ.items() if not k.startswith(('PYTHON', 'TCL', 'TK_'))}
env.update(PATH='/nonexistent', INFRA_REVIEW_STATE=str(base / 'review-state'))


def run(args, cwd=project):
    result = subprocess.run(list(map(str, args)), cwd=cwd, env=env, text=True,
                            encoding='utf-8', errors='replace', capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout


cli = app / 'project-infra'
desktop = app / 'ProjectInfra'
assert os.access(cli, os.X_OK) and os.access(desktop, os.X_OK)
assert run([cli, '--version']).strip() == __version__
build = json.loads((app / 'build-info.json').read_text(encoding='utf-8'))
assert build['system'] == 'linux' and build['version'] == __version__
run([cli, 'init'])
run([cli, 'validate'])
assert (project / 'knowledge/index.md').is_file()
assert json.loads(run([cli, 'list', '--json'])) == []

# Move the complete app and adjacent project to prove relocation works.
moved = base / '已迁移 含空格'
shutil.move(str(original), str(moved))
app, project = moved / 'ProjectInfra', moved / '空白 项目'
cli, desktop = app / 'project-infra', app / 'ProjectInfra'
run([cli, 'validate'], cwd=project)

if env.get('DISPLAY') or env.get('WAYLAND_DISPLAY'):
    (app / 'settings.json').write_text(json.dumps({'projects': [
        {'relative': '../空白 项目', 'absolute': str(project)}]}), encoding='utf-8')
    report = base / 'desktop-report.json'
    run([desktop, '--check-ui', report], cwd=project)
    data = json.loads(report.read_text(encoding='utf-8'))
    assert data['visible'] and data['title'] == 'Project Infra ' + __version__
    assert data['projects'] == [str(project.resolve())]

with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
server = subprocess.Popen([str(cli), 'serve', '--port', str(port)], cwd=project, env=env,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
url = f'http://127.0.0.1:{port}'
try:
    for _ in range(100):
        try:
            with urlopen(url + '/api/state', timeout=1) as response:
                state = json.load(response)
            break
        except OSError:
            if server.poll() is not None:
                raise RuntimeError('Frozen Linux server exited')
            time.sleep(.1)
    else:
        raise RuntimeError('Frozen Linux server unavailable')
    assert state['errors'] == [] and state['objects'] == []
    assert Path(state['root']) == project.resolve()
    for asset in ['/', '/app.js', '/graph-layout.js', '/style.css', '/facets.svg']:
        with urlopen(url + asset) as response:
            assert response.read(), asset
finally:
    server.terminate()
    server.wait(timeout=10)

print('PASS: self-contained Linux runtime, no Python on PATH, relocation, Tk desktop and web assets')
print('Retained check:', base)
