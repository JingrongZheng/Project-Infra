"""Environment-local reviewer capability handshake and optional process adapter.

An adapter implements probe/review JSON over stdin/stdout. Host agents can perform
the same handshake without a subprocess. Independence is a declared capability,
not an attempt to prove the honesty of an agent or enforce an OS security boundary.
"""
import getpass
import json
import os
from pathlib import Path
import platform
import signal
import subprocess
import sys
import time
import uuid

from .documents import digest
from . import __version__

RUNTIME = '.work/reviewer/runtime.json'


def environment(store):
    return digest(json.dumps([platform.node(), getpass.getuser(), str(store.root),
                              str(Path(sys.executable).resolve().parent), __version__]).encode())


def read(store):
    p = store.path(RUNTIME)
    data = json.loads(p.read_text(encoding='utf-8')) if p.exists() else {}
    if not isinstance(data, dict):
        raise ValueError('Reviewer capability record must be a JSON object')
    return data


def save(store, data):
    with store.locked():
        p = store.path(RUNTIME)
        store.commit_locked({RUNTIME: json.dumps(data, ensure_ascii=False, indent=2)},
                            {RUNTIME: digest(p.read_bytes()) if p.exists() else None})


def disable(store, reason='当前环境尚未完成质疑者能力自检'):
    data = {'enabled': False, 'reason': reason, 'environment': environment(store),
            'runtime_id': uuid.uuid4().hex, 'expires': 0}
    save(store, data)
    return data


def status(store):
    try:
        data = read(store)
        if data.get('environment') != environment(store):
            return {'enabled': False, 'reason': '当前运行环境未自检，质疑功能已关闭'}
        if data.get('enabled') and data.get('expires', 0) <= time.time():
            return {'enabled': False, 'reason': '能力自检已过期，请重新检查；质疑功能已关闭'}
        if not data.get('enabled') and data.get('deadline') and data['deadline'] <= time.time():
            return {'enabled': False, 'reason': '能力握手超时；质疑功能已关闭，请重新自检'}
        for active in store.path('.work/reviewer/active').glob('*.json'):
            pending = json.loads(active.read_text(encoding='utf-8'))
            if (pending.get('runtime_id') == data.get('runtime_id') and pending['deadline'] <= time.time()
                    and not store.path(pending['archive']).exists()):
                return {'enabled': False, 'reason': '本轮审查超时；质疑功能已关闭，未记为完成'}
        return {k: data[k] for k in ('enabled', 'reason', 'mode', 'label', 'expires', 'runtime_id') if k in data}
    except (ValueError, OSError, TypeError, KeyError, AttributeError):
        return {'enabled': False, 'reason': '能力记录不可读，质疑功能已关闭'}


def probe(store, label, command=None, timeout=120):
    if not label.strip() or not 1 <= timeout <= 3600:
        raise ValueError('Provide a reviewer label and a timeout between 1 and 3600 seconds')
    if command is not None and (not isinstance(command, list) or not command or
                               not all(isinstance(x, str) and x for x in command)):
        raise ValueError('Adapter command must be a nonempty JSON array of arguments')
    data = disable(store, '正在检查独立审查会话能力，尚未启用')
    nonce = uuid.uuid4().hex
    folder = f'.work/reviewer/probes/{nonce}'
    p = store.path(folder)
    p.mkdir(parents=True)
    request = {'action': 'probe', 'nonce': nonce, 'project': str(store.root),
               'instruction': 'Create a separate reviewer session which has not participated in planning or implementation. Return JSON with nonce, independent=true and session (nonempty identifier). This is a capability probe, not a project review.'}
    (p / 'request.json').write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding='utf-8')
    data.update(mode='process' if command else 'host', label=label, command=command,
                nonce=nonce, deadline=time.time() + timeout, timeout=timeout, probe_folder=folder)
    save(store, data)
    if command:
        try:
            response = invoke(store, data, request, folder)
            return accept(store, response)
        except (ValueError, OSError) as exc:
            disable(store, f'自检失败：{exc}')
            raise
    return {'enabled': False, 'request': folder + '/request.json', 'response': folder + '/response.json',
            'reason': '请宿主将 request 交给独立会话并返回 response，然后运行 reviewer accept'}


def accept(store, response):
    data = read(store)
    if not isinstance(response, dict):
        disable(store, '能力响应格式错误')
        raise ValueError('Capability response must be a JSON object')
    if data.get('environment') != environment(store) or data.get('deadline', 0) <= time.time():
        disable(store, '能力自检超时或环境发生变化')
        raise ValueError('Capability probe expired; start a fresh probe')
    if (response.get('nonce') != data.get('nonce') or response.get('independent') is not True
            or not isinstance(response.get('session'), str) or not response['session'].strip()):
        disable(store, '未能建立独立审查会话')
        raise ValueError('Probe response requires matching nonce, independent=true and a session identifier')
    data.update(enabled=True, reason='独立审查入口已完成能力握手（不代表方案已经审查）',
                expires=time.time() + 8 * 3600, session=response['session'])
    data.pop('nonce', None)
    data.pop('deadline', None)
    save(store, data)
    return status(store)


def invoke(store, data, request, folder):
    """Launch only a locally configured argv, never a browser-supplied shell string."""
    destination = store.path(folder)
    destination.mkdir(parents=True, exist_ok=True)
    kwargs = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
    process = subprocess.Popen(data['command'], cwd=store.root, stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, **kwargs)
    try:
        out, err = process.communicate(json.dumps(request, ensure_ascii=False).encode('utf-8'),
                                       timeout=data['timeout'])
    except subprocess.TimeoutExpired:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            os.killpg(process.pid, signal.SIGKILL)
        process.kill() if process.poll() is None else None
        out, err = process.communicate()
        (destination / 'stdout.log').write_bytes(out)
        (destination / 'stderr.log').write_bytes(err)
        raise ValueError('Reviewer process timed out; no review was recorded')
    (destination / 'stdout.log').write_bytes(out)
    (destination / 'stderr.log').write_bytes(err)
    if process.returncode:
        raise ValueError(f'Reviewer process exited with code {process.returncode}; see {folder}/stderr.log')
    try:
        response = json.loads(out.decode('utf-8-sig'))
    except (ValueError, UnicodeError) as exc:
        raise ValueError('Reviewer adapter must return one JSON object on stdout') from exc
    if not isinstance(response, dict):
        raise ValueError('Reviewer adapter must return a JSON object')
    return response
