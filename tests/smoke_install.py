"""Exercise the actual offline installer and installed wheel outside the source tree."""
from pathlib import Path
import json
import os
import socket
import subprocess
import sys
import time
from urllib.request import Request, urlopen
import zipfile

root = Path(__file__).resolve().parents[1]
scratch = root / '.work' / ('offline-install-' + str(time.time_ns()))
scratch.mkdir(parents=True)
bundle = Path(sys.argv[1]).resolve()
unpacked = scratch / 'bundle'
with zipfile.ZipFile(bundle) as archive:
    archive.extractall(unpacked)
installation = scratch / '工具安装'
project = scratch / '全新项目'
project.mkdir()
env = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'PYTHONHOME')}
env['PYTHONUTF8'] = '1'

def command(args, cwd=project, success=True):
    result = subprocess.run(list(map(str, args)), cwd=cwd, env=env, text=True,
                            encoding='utf-8', errors='replace', capture_output=True, timeout=120)
    if success and result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result

command(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
         unpacked / 'install-local.ps1', '-Destination', installation, '-Python', sys.executable])
cli = installation / '.venv/Scripts/project-infra.exe'
python = installation / '.venv/Scripts/python.exe'
assert command([cli, '--version']).stdout.strip() == '0.1.0'
location = command([python, '-c', 'import project_infra; print(project_infra.__file__)']).stdout.strip()
assert str(installation).casefold() in location.casefold(), location
# Wrapper works with a Chinese installation path and the caller's current directory.
command(['cmd', '/c', str(installation / 'project-infra.cmd'), 'init'])
command([cli, 'validate'])
assert json.loads(command([cli, 'list', '--json']).stdout) == []
assert not (project / 'project_infra').exists()
for path in project.rglob('*.md'):
    contents = path.read_text(encoding='utf-8')
    assert str(Path.home()).replace('\\','/') not in contents and str(Path.home()) not in contents, path
(project / 'AGENTS.md').write_text('USER CONTENT MUST SURVIVE', encoding='utf-8')
before = {p.relative_to(project): p.read_bytes() for p in project.rglob('*') if p.is_file()}
command([cli, 'init'])
assert before == {p.relative_to(project): p.read_bytes() for p in project.rglob('*') if p.is_file()}
child = project / 'src'
child.mkdir()
command([cli, 'validate'], cwd=child)
plan = command([cli, 'new', 'plan', '--title', '空项目安装验证'], cwd=child).stdout.strip()
assert plan == 'PLAN-0001'
exp = command([cli, 'new', 'experiment', '--plan', plan, '--title', '验证记录与界面']).stdout.strip()
assert exp == 'EXP-0001'
assert '空项目安装验证' in command([cli, 'context', exp]).stdout
outside = scratch / 'not-a-project'
outside.mkdir()
assert command([cli, '--root', outside, 'validate'], cwd=outside, success=False).returncode != 0

with socket.socket() as sock:
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
server = subprocess.Popen([str(cli), 'serve', '--port', str(port)], cwd=child, env=env,
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
base = f'http://127.0.0.1:{port}'
try:
    for attempt in range(100):
        try:
            with urlopen(base + '/api/state', timeout=1) as response:
                state = json.load(response)
            break
        except OSError:
            if server.poll() is not None:
                raise RuntimeError('Installed server exited unexpectedly')
            time.sleep(.1)
    else:
        raise RuntimeError('Installed server did not become ready')
    assert Path(state['root']).resolve() == project.resolve()
    assert state['errors'] == []
    assert {o['meta']['id'] for o in state['objects']} == {plan, exp}
    for asset in ['/', '/app.js', '/graph-layout.js', '/style.css', '/facets.svg']:
        with urlopen(base + asset) as response:
            assert response.status == 200 and response.read(), asset
    request = Request(base + '/api/create', data=json.dumps({'kind': 'proposal', 'title': '安装后写回'}).encode(),
                      headers={'Content-Type': 'application/json', 'X-Infra-Token': state['token'], 'Origin': base})
    with urlopen(request) as response:
        assert json.load(response)['id'] == 'PROP-0001'
    command([cli, 'validate'])
    if env.get('INFRA_PLAYWRIGHT_MODULE'):
        command(['node', root / 'tests/browser_installed.cjs', base, scratch / 'installed-ui.png'])
        print('PASS: installed browser interface rendered and Plan dialog opened')
finally:
    server.terminate()
    server.wait(timeout=10)
print('PASS: actual offline installer, isolated installed code, Chinese paths, blank init, no overwrite, nested root discovery, records/context, installed web assets and UI write-back')
print('Retained test project:', project)
