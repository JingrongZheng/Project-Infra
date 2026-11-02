from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from project_infra.bootstrap import initialize
from project_infra.cli import project_root
from project_infra.service import Service
from project_infra.store import Store


class FreshProjectTests(unittest.TestCase):
    def test_empty_project_has_no_development_data_and_reinit_preserves_files(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(directory)
            initialize(store)
            service = Service(store)
            state = service.state()
            self.assertEqual(state['objects'], [])
            self.assertEqual(state['mainline'], [])
            self.assertEqual(state['errors'], [])
            for name in ['AGENTS.md', 'README.md', 'PROJECT.md', 'TOOLKIT.md', 'docs/verification.md']:
                text = store.path(name).read_text(encoding='utf-8')
                self.assertNotIn(str(Path.home()), text)
                self.assertNotIn(str(Path.home()).replace('\\','/'), text)
            store.path('AGENTS.md').write_text('user instructions', encoding='utf-8')
            store.path('README.md').write_text('user readme', encoding='utf-8')
            plan = service.create('plan', 'owner work')
            before = {p.relative_to(directory): p.read_bytes() for p in Path(directory).rglob('*') if p.is_file()}
            initialize(store)
            after = {p.relative_to(directory): p.read_bytes() for p in Path(directory).rglob('*') if p.is_file()}
            self.assertEqual(before, after)
            self.assertEqual(service.checked()[0][plan].meta['status'], 'active')

    def test_root_discovery_prefers_nearest_project_and_init_uses_current_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            outer = Path(directory) / 'outer'
            initialize(Store(outer))
            inner = outer / 'inner'
            initialize(Store(inner))
            child = inner / 'src'
            child.mkdir()
            with patch('pathlib.Path.cwd', return_value=child):
                self.assertEqual(project_root(), inner.resolve())
                self.assertEqual(project_root(initializing=True), child.resolve())
                self.assertEqual(project_root(outer), outer.resolve())
            with self.assertRaisesRegex(ValueError, 'No initialized project'):
                project_root(Path(directory) / 'uninitialized')
