"""Windows job-owned adapter tree; feed work only after job assignment."""
import ctypes as c
from ctypes import wintypes as w
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import uuid


class Limits(c.Structure):
    _fields_ = [('process_time', c.c_longlong), ('job_time', c.c_longlong), ('flags', w.DWORD),
                ('min_working', c.c_size_t), ('max_working', c.c_size_t), ('active_limit', w.DWORD),
                ('affinity', c.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]


class Extended(c.Structure):
    _fields_ = [('basic', Limits), ('io', c.c_ulonglong * 6), ('memory', c.c_size_t * 4)]


class Accounting(c.Structure):
    _fields_ = [('times', c.c_longlong * 4), ('faults', w.DWORD), ('total', w.DWORD),
                ('active', w.DWORD), ('terminated', w.DWORD)]


class Job:
    def __init__(self, name=None, create=True):
        self.k = c.WinDLL('kernel32', use_last_error=True)
        self.k.CreateJobObjectW.argtypes = [c.c_void_p, w.LPCWSTR]
        self.k.CreateJobObjectW.restype = w.HANDLE
        self.k.OpenJobObjectW.argtypes = [w.DWORD, w.BOOL, w.LPCWSTR]
        self.k.OpenJobObjectW.restype = w.HANDLE
        self.k.SetInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD]
        self.k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
        self.k.TerminateJobObject.argtypes = [w.HANDLE, w.UINT]
        self.k.QueryInformationJobObject.argtypes = [w.HANDLE, c.c_int, c.c_void_p, w.DWORD, c.c_void_p]
        self.k.CloseHandle.argtypes = [w.HANDLE]
        self.name = name or ('Local\\ProjectInfra.Review.' + uuid.uuid4().hex)
        self.handle = self.k.CreateJobObjectW(None, self.name) if create else self.k.OpenJobObjectW(0xc, False, self.name)
        if not self.handle:
            if not create and c.get_last_error() == 2:
                return
            raise c.WinError(c.get_last_error())
        if create:
            limits = Extended()
            limits.basic.flags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not self.k.SetInformationJobObject(self.handle, 9, c.byref(limits), c.sizeof(limits)):
                error = c.WinError(c.get_last_error())
                self.k.CloseHandle(self.handle)
                self.handle = None
                raise error

    def attach(self, process):
        if not self.k.AssignProcessToJobObject(self.handle, int(process._handle)):
            raise c.WinError(c.get_last_error())

    def stop(self):
        if not self.handle:
            return
        if not self.k.TerminateJobObject(self.handle, 1):
            raise c.WinError(c.get_last_error())
        until = time.monotonic() + 5
        while True:
            counts = Accounting()
            if not self.k.QueryInformationJobObject(self.handle, 1, c.byref(counts), c.sizeof(counts), None):
                raise c.WinError(c.get_last_error())
            if not counts.active:
                return
            if time.monotonic() >= until:
                raise OSError('审查进程树尚未退出，暂不恢复项目写入')
            time.sleep(.02)

    def close(self):
        if self.handle:
            try:
                self.stop()
            finally:
                self.k.CloseHandle(self.handle)
                self.handle = None


def stop_named(name):
    job = Job(name, create=False)
    job.close()


def wrapper_command(store):
    if getattr(sys, 'frozen', False):
        return [str(Path(sys.executable).with_name('project-infra.exe')), '--root', str(store.root), '_review-exec'], Path(sys.executable).parent
    return [sys.executable, '-m', 'project_infra', '--root', str(store.root), '_review-exec'], Path(__file__).resolve().parents[1]


def run_wrapper(store):
    data = json.loads(sys.stdin.buffer.read().decode('utf-8'))
    command = data.get('command')
    if not isinstance(command, list) or not command or not all(isinstance(x, str) and x for x in command):
        raise ValueError('Invalid reviewer adapter arguments')
    # The parent feeds this request only after assigning this trusted wrapper to its job.
    return subprocess.run(command, cwd=store.root,
        input=json.dumps(data['request'], ensure_ascii=False).encode('utf-8')).returncode
