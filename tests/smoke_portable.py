"""Relocate the shipped EXEs and run them without a Python installation on PATH."""
from pathlib import Path
import json
import os
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import urlopen
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_infra import __version__

base = Path(__file__).resolve().parents[1] / '.work' / ('portable-check-' + str(time.time_ns()))
original = base / '原位置'
original.mkdir(parents=True)
with zipfile.ZipFile(Path(sys.argv[1]).resolve()) as archive:
    archive.extractall(original)
app = original / 'ProjectInfra'
project = original / '空白 项目'
project.mkdir()
env = {k: v for k, v in os.environ.items() if not k.startswith('PYTHON') and not k.startswith('TCL') and not k.startswith('TK_')}
env['PATH'] = str(Path(os.environ['SystemRoot']) / 'System32')

def run(args, cwd=project):
    result = subprocess.run(list(map(str, args)), cwd=cwd, env=env, text=True, encoding='utf-8', errors='replace',
                            capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    return result.stdout

cli = app / 'project-infra.exe'
assert run([cli, '--version']).strip() == __version__
run([cli, 'init'])
run([cli, 'validate'])
assert (project / 'knowledge/index.md').is_file()
assert (project / 'shared/README.md').is_file()
assert json.loads(run([cli, 'list', '--json'])) == []
for path in project.rglob('*.md'):
    assert str(Path.home()) not in path.read_text(encoding='utf-8'), path
(app / 'settings.json').write_text(json.dumps({'projects': [{'relative': '../空白 项目', 'absolute': str(project)}]}), encoding='utf-8')
# Move the whole application and adjacent project, then prove relative project recovery.
moved = base / '已迁移 含空格'
assert original.resolve().is_relative_to(base.resolve()) and moved.resolve().is_relative_to(base.resolve())
shutil.move(str(original), str(moved))
app, project = moved / 'ProjectInfra', moved / '空白 项目'
cli = app / 'project-infra.exe'
report = base / 'desktop-report.json'
run([app / 'ProjectInfra.exe', '--check-ui', report], cwd=project)
data = json.loads(report.read_text(encoding='utf-8'))
assert data['visible'] and data['title'] == 'Project Infra ' + __version__
assert data['projects'] == [str(project.resolve())], data
run([cli, 'validate'], cwd=project)
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
                raise RuntimeError('Frozen server exited')
            time.sleep(.1)
    else:
        raise RuntimeError('Frozen server unavailable')
    assert state['errors'] == [] and state['objects'] == []
    assert Path(state['root']) == project.resolve()
    for asset in ['/', '/app.js', '/graph-layout.js', '/style.css', '/facets.svg']:
        with urlopen(url + asset) as response:
            assert response.read(), asset
    if os.environ.get('INFRA_PLAYWRIGHT_MODULE'):
        browser_env = dict(env, INFRA_PLAYWRIGHT_MODULE=os.environ['INFRA_PLAYWRIGHT_MODULE'])
        browser_test = Path(__file__).with_name('browser_portable.cjs')
        subprocess.run([shutil.which('node'), str(browser_test), url, str(base / 'portable-ui.png')],
                       env=browser_env, check=True, timeout=30)
    plan = run([cli, '--root', project, 'new', 'plan', '--title', 'Packaged review test fixture'], cwd=project).strip()
    capability = json.loads(run([cli, '--root', project, 'reviewer', 'probe', '--label', 'packaged host fixture'], cwd=project))
    request = json.loads((project / capability['request']).read_text(encoding='utf-8'))
    response = project / capability['response']
    response.write_text(json.dumps({'nonce': request['nonce'], 'independent': True, 'session': 'fixture-only-not-a-model'}), encoding='utf-8')
    run([cli, '--root', project, 'reviewer', 'accept', '--response', str(response)], cwd=project)
    capability_data = json.loads((project / '.work/reviewer/runtime.json').read_text(encoding='utf-8'))
    assert capability_data['environment'] == data['reviewer_environment'], 'GUI and CLI in the same installation must share environment identity'
    handoff = run([cli, '--root', project, 'review', plan, '--prepare'], cwd=project).strip()
    note = project / handoff / 'NOTE.md'
    note.write_text('Reviewer: packaged test fixture, not a real review\n\n## 已核查\nCLI packaging check only.\n\n## 主要疑点\nDoes not establish production method validity.\n', encoding='utf-8')
    run([cli, '--root', project, 'review', plan, '--record', str(note.relative_to(project))], cwd=project)
    assert 'packaged test fixture' in (project / '.project/plans' / (plan + '.md')).read_text(encoding='utf-8')
finally:
    server.terminate()
    server.wait(timeout=10)
print('PASS: relocated EXEs, no Python on PATH, packaged Tk desktop, recovered recent project, blank initialization, packaged web assets')
print('Retained check:', base)
