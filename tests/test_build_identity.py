from pathlib import Path
import tempfile
import unittest

from scripts.build_support import source_digest


class BuildIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        for path in ['LICENSE', 'THIRD_PARTY_NOTICES.md', 'scripts/desktop_entry.py',
                     'scripts/cli_entry.py', 'project_infra/core.py']:
            p = self.root / path
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'content\n')

    def test_git_line_endings_do_not_change_build_identity(self):
        p = self.root / 'project_infra/core.py'
        p.write_bytes(b'a = 1\r\nb = 2\r\n')
        before = source_digest(self.root)
        p.write_bytes(b'a = 1\nb = 2\n')
        self.assertEqual(source_digest(self.root), before)

    def test_actual_source_changes_are_detected(self):
        before = source_digest(self.root)
        (self.root / 'project_infra/core.py').write_bytes(b'changed\n')
        self.assertNotEqual(source_digest(self.root), before)

    def test_binary_bytes_are_never_line_normalized(self):
        p = self.root / 'project_infra/icon.png'
        p.write_bytes(b'fixture\r\n')
        before = source_digest(self.root)
        p.write_bytes(b'fixture\n')
        self.assertNotEqual(source_digest(self.root), before)
