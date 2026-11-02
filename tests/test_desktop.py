from pathlib import Path
import shutil
import tempfile
import unittest
from urllib.request import urlopen
import json

from project_infra.bootstrap import initialize
from project_infra.desktop import load_recent, save_recent, ProjectSessions, write_runtime_hint
from project_infra.store import Store


class DesktopTests(unittest.TestCase):
    def test_recent_projects_follow_application_and_project_moved_together(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            old = base / 'old'
            app = old / '应用'
            project = old / '项目'
            initialize(Store(project))
            save_recent(app, [project.resolve()])
            relocated = base / 'new'
            assert old.resolve().is_relative_to(base.resolve()) and relocated.resolve().is_relative_to(base.resolve())
            shutil.move(str(old), str(relocated))
            self.assertEqual(load_recent(relocated / '应用'), [(relocated / '项目').resolve()])

    def test_move_only_application_falls_back_to_project_original_location(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            project = base / 'project'
            initialize(Store(project))
            save_recent(base / 'app', [project.resolve()])
            moved = base / 'nested/app'
            moved.parent.mkdir()
            assert (base / 'app').resolve().is_relative_to(base.resolve()) and moved.resolve().is_relative_to(base.resolve())
            shutil.move(str(base / 'app'), str(moved))
            self.assertEqual(load_recent(moved), [project.resolve()])
            moved.joinpath('settings.json').write_text('{broken', encoding='utf-8')
            self.assertEqual(load_recent(moved), [])

    def test_same_project_reuses_service_and_close_releases_sessions(self):
        with tempfile.TemporaryDirectory() as temporary:
            initialize(Store(temporary))
            manager = ProjectSessions()
            try:
                url = manager.open(temporary)
                self.assertEqual(manager.open(temporary), url)
                with urlopen(url + 'api/state') as response:
                    state = json.load(response)
                self.assertEqual(state['objects'], [])
                self.assertEqual(len(manager.sessions), 1)
                manager.close(temporary)
                self.assertEqual(manager.sessions, {})
            finally:
                manager.close()

    def test_runtime_hint_is_replaced_after_application_moves(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            project = base / 'project'
            initialize(Store(project))
            for name in ['app1', 'app2']:
                app = base / name
                app.mkdir()
                (app / 'project-infra.exe').touch()
                write_runtime_hint(project, app)
            text = (project / '.work/infra-runtime.md').read_text(encoding='utf-8')
            self.assertIn('app2', text)
            self.assertNotIn('app1', text)
