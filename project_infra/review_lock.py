"""Project-wide serial review freeze, with external recovery journal and watchdog."""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from .winacl import ACL
_watchdogs = {}


def control_directory():
    base = os.environ.get('INFRA_REVIEW_STATE')
    return Path(base) if base else Path(os.environ.get('LOCALAPPDATA', Path.home() / '.local/state')) / 'ProjectInfra/review-locks'


def journal_path(store):
    ident = hashlib.sha256(str(store.root).casefold().encode()).hexdigest()
    return control_directory() / (ident + '.json')


def read(store):
    path = journal_path(store)
    data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if data and Path(data['root']) != store.root:
        raise ValueError('Review recovery journal belongs to another project')
    return data


def write(store, data):
    path = journal_path(store)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.resolve().is_relative_to(store.root):
        raise ValueError('Review recovery journal must be outside the protected project')
    temp = path.with_suffix('.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False)
        stream.flush()
        os.fsync(stream.fileno())
    for attempt in range(20):
        try:
            os.replace(temp, path)
            break
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.01)


@contextmanager
def control_lock(store):
    path = journal_path(store).with_suffix('.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(100):
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError:
            try:
                owner = int(path.read_text())
                if not alive(owner):
                    path.unlink(missing_ok=True)
            except (ValueError, OSError):
                if path.exists() and not path.stat().st_size and time.time() - path.stat().st_mtime > 5:
                    path.unlink(missing_ok=True)
            time.sleep(.05)
    else:
        raise OSError('Review permission recovery is busy; retry shortly')
    try:
        os.write(fd, str(os.getpid()).encode())
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)


def alive(pid):
    if not pid:
        return True
    if os.name == 'nt':
        import ctypes as c
        from ctypes import wintypes as w
        k = c.WinDLL('kernel32', use_last_error=True)
        k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
        k.OpenProcess.restype = w.HANDLE
        k.GetExitCodeProcess.argtypes = [w.HANDLE, c.POINTER(w.DWORD)]
        k.CloseHandle.argtypes = [w.HANDLE]
        handle = k.OpenProcess(0x1000, False, pid)
        if not handle:
            return c.get_last_error() == 5
        try:
            code = w.DWORD()
            return bool(k.GetExitCodeProcess(handle, c.byref(code))) and code.value == 259
        finally:
            k.CloseHandle(handle)
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def process_stamp(pid):
    """Creation time prevents terminating an unrelated process after PID reuse."""
    import ctypes as c
    from ctypes import wintypes as w
    k = c.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.argtypes = [w.DWORD, w.BOOL, w.DWORD]
    k.OpenProcess.restype = w.HANDLE
    k.GetProcessTimes.argtypes = [w.HANDLE] + [c.POINTER(w.FILETIME)] * 4
    k.CloseHandle.argtypes = [w.HANDLE]
    handle = k.OpenProcess(0x1000, False, pid)
    if not handle:
        return None
    try:
        times = [w.FILETIME() for _ in range(4)]
        if not k.GetProcessTimes(handle, *(c.byref(t) for t in times)):
            return None
        return times[0].dwLowDateTime | (times[0].dwHighDateTime << 32)
    finally:
        k.CloseHandle(handle)


def register_child(store, pid, job_name=None):
    with control_lock(store):
        data = read(store)
        if data.get('state') != 'active':
            raise ValueError('Reviewer freeze is no longer active')
        stamp = process_stamp(pid)
        if stamp is None and alive(pid):
            raise OSError('无法监护本轮审查进程，拒绝开始审查')
        data.update(child=pid, child_stamp=stamp)
        if job_name:
            data['job_name'] = job_name
        write(store, data)


def stop_child(data):
    if data.get('job_name'):
        from .review_process import stop_named
        stop_named(data['job_name'])
        return
    pid = data.get('child')
    if pid and data.get('child_stamp') is not None and alive(pid) and process_stamp(pid) == data['child_stamp']:
        subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], capture_output=True,
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
        limit = time.time() + 2
        while alive(pid) and time.time() < limit:
            time.sleep(.05)
        if alive(pid):
            raise OSError('审查进程尚未停止，暂不恢复项目写入')


def active(store):
    data = read(store)
    return bool(data and data.get('state') != 'released')


def checked_path(store, relative):
    if Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Recovery path must stay inside the project')
    path = store.root / relative
    if not path.resolve().is_relative_to(store.root) or path.resolve() != path.absolute():
        raise ValueError('Refusing to change permissions through a link or outside the project')
    if path.lstat().st_file_attributes & 0x400:
        raise ValueError('Review write protection does not follow reparse points: ' + str(path))
    return path


def paths(store):
    result = [store.root]
    for base, dirs, files in os.walk(store.root, followlinks=False):
        for name in dirs + files:
            p = Path(base) / name
            checked_path(store, p.relative_to(store.root))
            result.append(p)
    return result


def begin(store, folder, deadline, mode, watchdog=True):
    api = ACL()  # Fail before changing anything on an unsupported platform.
    api.check_volume(store.root)
    output = store.path(folder)
    allowed = {output / name for name in ('NOTE.md', 'stdout.log', 'stderr.log')}
    checks = output / 'checks'
    checks.mkdir(exist_ok=True)
    for p in allowed:
        p.touch(exist_ok=True)
    with control_lock(store):
        if active(store):
            raise ValueError('项目正在独立审查；先完成或取消本轮，不能同时修改或启动另一轮')
        data = {'root': str(store.root), 'round': output.name, 'deadline': deadline, 'state': 'preparing',
                'owner': os.getpid(), 'mode': mode, 'entries': [], 'output': folder, 'applying': False}
        write(store, data)
        try:
            if store.path('.project/.write.lock').exists():
                raise ValueError('Project writer is still active; finish writing before review')
            for p in paths(store):
                if p in allowed or p == checks or p.is_relative_to(checks):
                    continue
                if p.is_file() and p.stat().st_nlink > 1:
                    raise ValueError('文件存在硬链接，拒绝同时改变项目外别名的权限：' + str(p))
                api.check_can_change(p)
                entry = {'path': p.relative_to(store.root).as_posix(), **api.snapshot(p)}
                if p == output:
                    # Permit temporary outputs/atomic NOTE saves, but never remove the
                    # round itself or delete protected context/manifest through its parent.
                    entry['deny_mask'] = 0x10000 | 0x40
                data['entries'].append(entry)
            # Persist ALL originals before applying any change. Recovery is idempotent.
            data['applying'] = True
            write(store, data)
            if watchdog:
                launch_watchdog(store, output.name)
            for entry in sorted(data['entries'], key=lambda e: len(Path(e['path']).parts), reverse=True):
                api.deny(checked_path(store, entry['path']), entry)
            data['state'] = 'active'
            data['owner'] = os.getpid() if mode == 'process' else None
            write(store, data)
        except BaseException:
            if data['applying']:
                restore_locked(store, data, 'prepare-failed')
            else:
                data.update(state='released', release_reason='prepare-failed')
                write(store, data)
            raise
    return data


def restore_locked(store, data, reason):
    stop_child(data)
    if not data.get('applying', True):
        data.update(state='released', release_reason=reason, released_at=time.time())
        write(store, data)
        return
    api = ACL()
    data['state'] = 'restoring'
    write(store, data)
    errors = []
    for entry in sorted(data['entries'], key=lambda e: len(Path(e['path']).parts)):
        try:
            api.restore(checked_path(store, entry['path']), entry)
        except (OSError, ValueError) as exc:
            errors.append(f'{entry["path"]}: {exc}')
    if errors:
        data['errors'] = errors
        write(store, data)
        raise OSError('部分原权限尚未恢复；备份已保留：' + '; '.join(errors[:3]))
    data.update(state='released', release_reason=reason, released_at=time.time())
    data.pop('errors', None)
    write(store, data)


def recover(store, reason='cancel', round_id=None):
    restored = False
    with control_lock(store):
        data = read(store)
        if not data or (round_id and data['round'] != round_id):
            return False
        if data['state'] != 'released':
            restore_locked(store, data, reason)
            restored = True
    for key, process in list(_watchdogs.items()):
        if key[0] == str(store.root):
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                continue
            del _watchdogs[key]
    return restored


def reap(store):
    data = read(store)
    if data and data.get('state') != 'released':
        if data['deadline'] <= time.time():
            recover(store, 'timeout', data['round'])
        elif data.get('owner') and not alive(data['owner']):
            recover(store, 'owner-exited', data['round'])


def assert_writable(store):
    reap(store)
    if active(store):
        from .store import Conflict
        raise Conflict('项目处于审查只读阶段；先完成本轮交接或运行 reviewer disable 取消审查')


def finish(store, round_id):
    data = read(store)
    if not data or data['round'] != round_id:
        raise ValueError('本轮没有对应的项目写保护交接，请重新准备审查')
    if data['state'] == 'released':
        raise ValueError('本轮审查已结束或已恢复写入，不能再次导入旧交接')
    expired = data['deadline'] <= time.time()
    recover(store, 'timeout' if expired else 'record', round_id)
    if expired:
        raise ValueError('Review deadline exceeded; project permissions restored')


def launch_watchdog(store, round_id):
    if getattr(sys, 'frozen', False):
        command = [str(Path(sys.executable).with_name('project-infra.exe'))]
        cwd = Path(sys.executable).parent
    else:
        command, cwd = [sys.executable, '-m', 'project_infra'], Path(__file__).resolve().parents[1]
    command += ['--root', str(store.root), '_review-watchdog', round_id]
    flags = {'creationflags': subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    _watchdogs[(str(store.root), round_id)] = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True, **flags)


def watch(store, round_id):
    while True:
        data = read(store)
        if not data or data['round'] != round_id or data['state'] == 'released':
            return
        reap(store)
        time.sleep(.25)
