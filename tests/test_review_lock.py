import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from project_infra.store import Store
from project_infra import review_lock as lock
from project_infra.winacl import ACL


@unittest.skipUnless(os.name == 'nt', 'Windows native permission tests')
class ReviewLockTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.environment = patch.dict(os.environ, {'INFRA_REVIEW_STATE': str(self.base / 'control')})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        root = self.base / 'project'
        root.mkdir()
        self.store = Store(root)
        self.addCleanup(lock.recover, self.store, 'test-cleanup')
        (root / '.project').mkdir()
        (root / '.project/config.toml').write_text('schema_version = 2\n')
        self.source = root / 'code.py'
        self.source.write_text('value = 1\n')
        self.folder = '.work/reviews/PLAN-0001/round'
        self.output = self.store.path(self.folder)
        self.output.mkdir(parents=True)
        for name in ('NOTE.md', 'context.md', 'manifest.json'):
            (self.output / name).write_text(name)

    def begin(self, **kwargs):
        return lock.begin(self.store, self.folder, time.time() + 30, 'host', watchdog=False, **kwargs)

    def test_real_filesystem_blocks_all_project_writes_but_allows_review_outputs(self):
        self.begin()
        operations = [lambda: self.source.write_text('bad'), lambda: self.source.unlink(),
            lambda: self.source.rename(self.source.with_name('renamed.py')),
            lambda: (self.store.root / 'created.py').write_text('bad'),
            lambda: (self.store.root / 'new-folder').mkdir(),
            lambda: (self.output / 'context.md').write_text('bad'),
            lambda: (self.output / 'manifest.json').unlink()]
        for operation in operations:
            with self.assertRaises(PermissionError):
                operation()
        (self.output / 'NOTE.md').write_text('review findings')
        (self.output / 'checks/result.txt').write_text('evidence')
        self.assertEqual(self.source.read_text(), 'value = 1\n')
        with self.assertRaisesRegex(ValueError, '只读'):
            with self.store.locked():
                pass

    def test_every_original_dacl_is_restored_exactly(self):
        api = ACL()
        originals = {p.relative_to(self.store.root).as_posix(): api.snapshot(p) for p in lock.paths(self.store)}
        self.begin()
        self.assertFalse(lock.journal_path(self.store).is_relative_to(self.store.root))
        lock.recover(self.store, 'fixture-finished')
        for relative, acl in originals.items():
            self.assertEqual(api.snapshot(self.store.root / relative), acl, relative)
        self.source.write_text('writing resumes')

    def test_partial_application_failure_rolls_back_before_returning(self):
        api = ACL()
        original = api.snapshot(self.source)
        actual = ACL.deny
        calls = []
        def fail_after_first(instance, path, snapshot):
            calls.append(path)
            if len(calls) == 2:
                raise OSError('fixture failure applying ACL')
            return actual(instance, path, snapshot)
        with patch.object(ACL, 'deny', fail_after_first):
            with self.assertRaisesRegex(OSError, 'fixture failure'):
                self.begin()
        self.assertFalse(lock.active(self.store))
        self.assertEqual(api.snapshot(self.source), original)
        self.source.write_text('unlocked')

    def test_recovery_failure_keeps_original_backup_for_retry(self):
        self.begin()
        actual = ACL.restore
        def fail_once(instance, path, snapshot):
            if path == self.source:
                raise OSError('fixture transient failure')
            return actual(instance, path, snapshot)
        with patch.object(ACL, 'restore', fail_once):
            with self.assertRaisesRegex(OSError, '原权限尚未恢复'):
                lock.recover(self.store, 'fixture-finished')
        self.assertTrue(lock.active(self.store))
        self.assertTrue(lock.read(self.store)['entries'])
        lock.recover(self.store, 'retry')
        self.assertFalse(lock.active(self.store))
        self.source.write_text('restored after retry')

    def test_detached_watchdog_restores_without_any_status_or_import_call(self):
        lock.begin(self.store, self.folder, time.time() + 1, 'host')
        limit = time.time() + 8
        while True:
            try:
                self.source.write_text('restored by watchdog')
                break
            except PermissionError:
                if time.time() > limit:
                    self.fail('Watchdog did not restore project writing')
                time.sleep(.1)
        while lock.read(self.store).get('state') != 'released' and time.time() < limit:
            time.sleep(.05)
        self.assertEqual(lock.read(self.store)['release_reason'], 'timeout')

    def test_owner_crash_is_recovered_by_the_external_watchdog(self):
        command = '''from project_infra.store import Store
from project_infra.review_lock import begin
import os,time,sys
begin(Store(sys.argv[1]),sys.argv[2],time.time()+30,'process')
os._exit(0)
'''
        process = subprocess.run([sys.executable, '-c', command, str(self.store.root), self.folder],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=15)
        self.assertEqual(process.returncode, 0, process.stderr)
        limit = time.time() + 8
        while True:
            try:
                self.source.write_text('recovered after owner exit')
                break
            except PermissionError:
                if time.time() > limit:
                    self.fail('Owner exit left the project frozen')
                time.sleep(.1)
        while lock.read(self.store).get('state') != 'released' and time.time() < limit:
            time.sleep(.05)
        self.assertEqual(lock.read(self.store)['release_reason'], 'owner-exited')

    def test_crash_partway_through_freezing_is_automatically_rolled_back(self):
        command = '''from project_infra.store import Store
from project_infra.review_lock import begin
from project_infra.winacl import ACL
import os,time,sys
original = ACL.deny
def interrupted(self,path,snapshot):
    original(self,path,snapshot)
    if path.name == 'code.py': os._exit(0)
ACL.deny = interrupted
begin(Store(sys.argv[1]),sys.argv[2],time.time()+30,'host')
'''
        result = subprocess.run([sys.executable, '-c', command, str(self.store.root), self.folder],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        limit = time.time() + 8
        while lock.read(self.store).get('state') != 'released' and time.time() < limit:
            time.sleep(.05)
        self.assertEqual(lock.read(self.store).get('release_reason'), 'owner-exited')
        self.source.write_text('recovered after partial freeze')

    def test_recovery_does_not_follow_links_or_leave_the_project(self):
        with self.assertRaises(ValueError):
            lock.checked_path(self.store, '../outside')

    def test_controller_crash_stops_its_worker_tree_before_permissions_resume(self):
        command = '''from project_infra.store import Store
from project_infra.review_lock import begin
from project_infra.reviewer_runtime import invoke
import os,time,sys,threading
from pathlib import Path
store=Store(sys.argv[1]);folder=sys.argv[2]
begin(store,folder,time.time()+30,'process')
def crash_after_worker_starts():
    marker=store.path(folder+'/checks/worker-pid.txt')
    until=time.time()+10
    while not marker.exists() and time.time()<until: time.sleep(.02)
    os._exit(0 if marker.exists() else 4)
threading.Thread(target=crash_after_worker_starts,daemon=True).start()
invoke(store,{'command':[sys.executable,sys.argv[3],'hold-tree'],'timeout':20},{'action':'review'},folder)
'''
        result = subprocess.run([sys.executable, '-c', command, str(self.store.root), self.folder,
            str(Path(__file__).with_name('reviewer_fixture.py'))],
            cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        limit = time.time() + 8
        while lock.read(self.store).get('state') != 'released' and time.time() < limit:
            time.sleep(.05)
        self.assertEqual(lock.read(self.store).get('release_reason'), 'owner-exited')
        pid = int((self.output / 'checks/worker-pid.txt').read_text())
        self.assertFalse(lock.alive(pid))
        self.source.write_text('workers stopped, writes resumed')

    def test_hardlinks_are_rejected_before_changing_external_alias_permissions(self):
        alias = self.base / 'outside-alias.py'
        os.link(self.source, alias)
        original = ACL().snapshot(alias)
        with self.assertRaisesRegex(ValueError, '硬链接'):
            self.begin()
        self.assertFalse(lock.active(self.store))
        self.assertEqual(ACL().snapshot(alias), original)
        self.source.write_text('still writable')

    def test_second_round_cannot_freeze_the_same_project(self):
        self.begin()
        with self.assertRaises((ValueError, PermissionError)):
            lock.begin(self.store, self.folder, time.time() + 30, 'host', watchdog=False)
        self.assertTrue(lock.active(self.store))

    def test_note_can_be_saved_atomically_but_manifest_cannot_be_replaced(self):
        self.begin()
        temporary = self.output / 'note.tmp'
        temporary.write_text('atomic note')
        os.replace(temporary, self.output / 'NOTE.md')
        self.assertEqual((self.output / 'NOTE.md').read_text(), 'atomic note')
        replacement = self.output / 'manifest.tmp'
        replacement.write_text('bad')
        with self.assertRaises(PermissionError):
            os.replace(replacement, self.output / 'manifest.json')
        self.assertEqual((self.output / 'manifest.json').read_text(), 'manifest.json')
