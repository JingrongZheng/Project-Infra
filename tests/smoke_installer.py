"""Build with an isolated identity, test real Windows install/uninstall, retain project files."""
from pathlib import Path
import json
import os
import subprocess
import sys
import time
import winreg

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from project_infra import __version__
compiler = Path(sys.argv[1]).resolve()
stamp = str(time.time_ns())
product_id = 'ProjectInfra.Smoke.' + stamp
product_name = 'ProjectInfra Test ' + stamp
scratch = root / '.work' / ('installer-check-' + stamp)
scratch.mkdir(parents=True)
target = scratch / '软件 安装'
project = scratch / '项目数据 与软件分离'
project.mkdir()
registry_key = 'Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\' + product_id + '_is1'
env = dict(os.environ, PYTHONUTF8='1')

def run(args, success=True):
    result = subprocess.run(list(map(str, args)), cwd=scratch, env=env, text=True, encoding='utf-8',
                            errors='replace', capture_output=True, timeout=120)
    if success and result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result

def powershell(code):
    prefix = '[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); '
    return run(['powershell', '-NoProfile', '-Command', prefix + code]).stdout.strip()

def snapshot(directory):
    return {p.relative_to(directory).as_posix(): p.read_bytes() for p in directory.rglob('*') if p.is_file()}

def uninstall_exists():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, registry_key, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            return winreg.QueryValueEx(key, 'DisplayName')[0]
    except FileNotFoundError:
        return None

run([compiler, '/Qp', '/DSourceDir=' + str(root / 'dist/portable/ProjectInfra'),
     '/DProductVersion=' + __version__, '/DProductId=' + product_id, '/DProductName=' + product_name, '/DOutputName=TestSetup',
     '/DRuntimeMutex=Local\\' + product_id,
     '/O' + str(scratch), root / 'installer/ProjectInfra.iss'])
setup = scratch / 'TestSetup.exe'
desktop = Path(powershell("[Environment]::GetFolderPath('Desktop')"))
programs = Path(powershell("[Environment]::GetFolderPath('Programs')"))
desktop_link = desktop / (product_name + '.lnk')
start_link = programs / (product_name + '.lnk')
assert not desktop_link.exists() and not start_link.exists() and uninstall_exists() is None
try:
    run([setup, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/DIR=' + str(target),
         '/TASKS=desktopicon', '/LOG=' + str(scratch / 'install.log')])
    assert uninstall_exists() == product_name + ' ' + __version__, uninstall_exists()
    assert desktop_link.is_file() and start_link.is_file()
    quoted = str(desktop_link).replace("'", "''")
    shortcut = json.loads(powershell("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('" + quoted + "'); @{target=$s.TargetPath; working=$s.WorkingDirectory; icon=$s.IconLocation}|ConvertTo-Json"))
    assert Path(shortcut['target']) == target / 'ProjectInfra.exe'
    assert Path(shortcut['working']) == target
    icon = target / '_internal/project_infra/assets/pi-monogram.ico'
    assert Path(shortcut['icon'].rsplit(',', 1)[0].strip('"')) == icon
    assert icon.read_bytes() == (root / 'project_infra/assets/pi-monogram.ico').read_bytes()
    cli = target / 'project-infra.exe'
    run([cli, '--root', project, 'init'])
    run([cli, '--root', project, 'new', 'plan', '--title', '卸载后必须保留'])
    external_before = snapshot(project)
    # Even unknown project files located inside the installation directory are retained.
    internal_project = target / 'user-project'
    run([cli, '--root', internal_project, 'init'])
    internal_before = snapshot(internal_project)
    settings = target / 'settings.json'
    settings.write_text(json.dumps({'projects': []}), encoding='utf-8')
    before_settings = settings.read_bytes()
    report = scratch / 'desktop.json'
    run([target / 'ProjectInfra.exe', '--check-ui', report])
    assert json.loads(report.read_text())['visible']
    # Reinstall preserves preferences and unrelated project data.
    run([setup, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', '/DIR=' + str(target), '/TASKS=desktopicon'])
    assert settings.read_bytes() == before_settings
    assert snapshot(internal_project) == internal_before
finally:
    uninstaller = target / 'unins000.exe'
    if uninstaller.is_file():
        run([uninstaller, '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/LOG=' + str(scratch / 'uninstall.log')])
for _ in range(100):
    if not desktop_link.exists() and uninstall_exists() is None and not (target / 'ProjectInfra.exe').exists():
        break
    time.sleep(.1)
assert not desktop_link.exists() and not start_link.exists()
assert uninstall_exists() is None
assert not (target / 'ProjectInfra.exe').exists()
assert not (target / 'project-infra.exe').exists()
assert snapshot(project) == external_before
assert snapshot(internal_project) == internal_before
assert settings.read_bytes() == before_settings
print('PASS: chosen Chinese/space install path, desktop/start shortcuts, Apps uninstall record, installed GUI, reinstall preserves settings; uninstall removes app/shortcuts/registration and retains both external and nested project data')
print('Retained test logs:', scratch)
