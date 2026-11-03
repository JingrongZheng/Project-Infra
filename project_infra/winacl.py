"""Windows DACL snapshots and non-inheriting write-deny entries for review."""
import base64
import ctypes as c
from ctypes import wintypes as w
import os


WRITE_DENY = 0x10000 | 0x2 | 0x4 | 0x10 | 0x40 | 0x100


class ACL:
    def __init__(self):
        if os.name != 'nt':
            raise OSError('Project write protection currently requires Windows file permissions')
        self.a = c.WinDLL('advapi32', use_last_error=True)
        self.k = c.WinDLL('kernel32', use_last_error=True)
        self.a.GetNamedSecurityInfoW.argtypes = [w.LPWSTR, w.DWORD, w.DWORD] + [c.POINTER(c.c_void_p)] * 5
        self.a.GetNamedSecurityInfoW.restype = w.DWORD
        self.a.SetNamedSecurityInfoW.argtypes = [w.LPWSTR, w.DWORD, w.DWORD] + [c.c_void_p] * 4
        self.a.SetNamedSecurityInfoW.restype = w.DWORD
        self.a.GetSecurityDescriptorControl.argtypes = [c.c_void_p, c.POINTER(w.WORD), c.POINTER(w.DWORD)]
        self.a.GetSecurityDescriptorControl.restype = w.BOOL
        self.a.InitializeAcl.argtypes = [c.c_void_p, w.DWORD, w.DWORD]
        self.a.InitializeAcl.restype = w.BOOL
        self.a.AddAccessDeniedAceEx.argtypes = [c.c_void_p, w.DWORD, w.DWORD, w.DWORD, c.c_void_p]
        self.a.AddAccessDeniedAceEx.restype = w.BOOL
        self.a.AddAccessAllowedAce.argtypes = [c.c_void_p, w.DWORD, w.DWORD, c.c_void_p]
        self.a.AddAccessAllowedAce.restype = w.BOOL
        self.a.AddAce.argtypes = [c.c_void_p, w.DWORD, w.DWORD, c.c_void_p, w.DWORD]
        self.a.AddAce.restype = w.BOOL
        self.a.GetAce.argtypes = [c.c_void_p, w.DWORD, c.POINTER(c.c_void_p)]
        self.a.GetAce.restype = w.BOOL
        self.a.GetLengthSid.argtypes = [c.c_void_p]
        self.a.GetLengthSid.restype = w.DWORD
        self.a.ConvertStringSidToSidW.argtypes = [w.LPCWSTR, c.POINTER(c.c_void_p)]
        self.a.ConvertStringSidToSidW.restype = w.BOOL
        self.k.GetCurrentProcess.restype = w.HANDLE
        self.k.CloseHandle.argtypes = [w.HANDLE]
        self.k.LocalFree.argtypes = [c.c_void_p]
        self.k.LocalFree.restype = c.c_void_p
        everyone = c.c_void_p()
        self.check(self.a.ConvertStringSidToSidW('S-1-1-0', c.byref(everyone)))
        try:
            self.sid = c.create_string_buffer(c.string_at(everyone, self.a.GetLengthSid(everyone)))
        finally:
            self.k.LocalFree(everyone)

    @staticmethod
    def check(ok):
        if not ok:
            raise c.WinError(c.get_last_error())

    def snapshot(self, path):
        acl, sd = c.c_void_p(), c.c_void_p()
        code = self.a.GetNamedSecurityInfoW(str(path), 1, 4, None, None, c.byref(acl), None, c.byref(sd))
        if code:
            raise c.WinError(code)
        try:
            control, revision = w.WORD(), w.DWORD()
            self.check(self.a.GetSecurityDescriptorControl(sd, c.byref(control), c.byref(revision)))
            # ACL header: revision, padding, size, ACE count, padding.
            size = c.c_ushort.from_address(acl.value + 2).value if acl.value else 0
            return {'dacl': base64.b64encode(c.string_at(acl, size)).decode() if size else None,
                    'protected': bool(control.value & 0x1000)}
        finally:
            self.k.LocalFree(sd)

    def check_volume(self, path):
        self.k.GetVolumePathNameW.argtypes = [w.LPCWSTR, w.LPWSTR, w.DWORD]
        self.k.GetVolumeInformationW.argtypes = [w.LPCWSTR, w.LPWSTR, w.DWORD,
            c.POINTER(w.DWORD), c.POINTER(w.DWORD), c.POINTER(w.DWORD), w.LPWSTR, w.DWORD]
        volume, flags = c.create_unicode_buffer(32768), w.DWORD()
        self.check(self.k.GetVolumePathNameW(str(path), volume, len(volume)))
        self.check(self.k.GetVolumeInformationW(volume.value, None, 0, None, None, c.byref(flags), None, 0))
        if not flags.value & 8:  # FILE_PERSISTENT_ACLS
            raise OSError('当前文件系统不支持持久文件权限，不能建立项目审查写保护')

    def check_can_change(self, path):
        self.k.CreateFileW.argtypes = [w.LPCWSTR, w.DWORD, w.DWORD, c.c_void_p, w.DWORD, w.DWORD, w.HANDLE]
        self.k.CreateFileW.restype = w.HANDLE
        handle = self.k.CreateFileW(str(path), 0x60000, 7, None, 3, 0x02000000, None)
        if handle == c.c_void_p(-1).value:
            raise c.WinError(c.get_last_error())
        self.k.CloseHandle(handle)

    def set(self, path, data, protected):
        buf = c.create_string_buffer(data) if data is not None else None
        code = self.a.SetNamedSecurityInfoW(str(path), 1, 4 | (0x80000000 if protected else 0x20000000),
                                            None, None, buf, None)
        if code:
            raise c.WinError(code)

    def restore(self, path, original):
        data = base64.b64decode(original['dacl']) if original['dacl'] is not None else None
        self.set(path, data, original['protected'])

    def deny(self, path, original):
        raw = base64.b64decode(original['dacl']) if original['dacl'] is not None else None
        old = c.create_string_buffer(raw) if raw else None
        revision = raw[0] if raw else 2
        buf = c.create_string_buffer((len(raw) if raw else 8) + len(self.sid) + 128)
        self.check(self.a.InitializeAcl(buf, len(buf), revision))
        self.check(self.a.AddAccessDeniedAceEx(buf, revision, 0, WRITE_DENY, self.sid))
        if old is not None:
            count = c.c_ushort.from_buffer(old, 4).value
            for index in range(count):
                ace = c.c_void_p()
                self.check(self.a.GetAce(old, index, c.byref(ace)))
                size = c.c_ushort.from_address(ace.value + 2).value
                self.check(self.a.AddAce(buf, revision, 0xffffffff, ace, size))
        else:
            # A null DACL originally granted everyone full access.
            everyone = c.c_void_p()
            self.check(self.a.ConvertStringSidToSidW('S-1-1-0', c.byref(everyone)))
            try:
                self.check(self.a.AddAccessAllowedAce(buf, revision, 0x1f01ff, everyone))
            finally:
                self.k.LocalFree(everyone)
        size = c.c_ushort.from_buffer(buf, 2).value
        self.set(path, bytes(buf[:size]), True)
