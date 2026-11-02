from pathlib import Path
import tempfile
import unittest

from project_infra.bootstrap import initialize
from project_infra.store import Store
from project_infra.service import Service
from scripts.migrate_task_records import migrate


class MigrationTests(unittest.TestCase):
    def test_preserves_goals_acceptance_verification_and_binary_evidence(self):
        scratch = Path(__file__).resolve().parents[1] / '.work/tests'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as root:
            store = Store(root)
            initialize(store)
            store.path('PROJECT.md').write_text('''+++
[[mainline]]
id="views"
section="design-views"
after=[]
sources=[]
tasks=["TASK-0001"]
+++

# Fixture
<a id="design-views"></a>
## Views
test design
''', encoding='utf-8')
            assets = store.path('.project/tasks/TASK-0001.assets')
            assets.mkdir(parents=True)
            payload = b'\x00\x01historical bytes\xff'
            (assets/'before.txt').write_bytes(payload)
            (assets/'after.txt').write_bytes(payload + b'new')
            old = '''+++
id="TASK-0001"
title="Preserve delivery contents"
status="active"
verify=["echo verified"]
before=[".project/tasks/TASK-0001.assets/before.txt"]
after=[".project/tasks/TASK-0001.assets/after.txt"]
+++

## Goal
GOAL_SENTINEL
## Acceptance criteria
- [ ] AC_SENTINEL
## Implementation notes
IMPLEMENTATION_SENTINEL
## Verification
VERIFY_SENTINEL
## Before / After
DEMONSTRATION_SENTINEL
## Final summary
CONCLUSION_SENTINEL
'''
            store.path('.project/tasks/TASK-0001.md').write_text(old, encoding='utf-8')
            migrate(root)
            docs, errors = Service(store).checked()
            self.assertEqual(errors, [])
            self.assertIn('GOAL_SENTINEL', docs['PLAN-0001'].section('Question'))
            self.assertIn('AC_SENTINEL', docs['PLAN-0001'].section('Acceptance criteria'))
            self.assertIn('IMPLEMENTATION_SENTINEL', docs['EXP-0004'].section('Notes'))
            self.assertIn('VERIFY_SENTINEL', docs['EXP-0004'].section('Verification'))
            self.assertIn('DEMONSTRATION_SENTINEL', docs['EXP-0004'].section('Before / After'))
            self.assertEqual(docs['EXP-0004'].meta['verify'], ['echo verified'])
            self.assertEqual(store.path(docs['EXP-0004'].meta['before'][0]).read_bytes(), payload)
            self.assertFalse(store.path('.project/tasks').exists())
            self.assertTrue(store.path('.work/migrations/task-removal/legacy-tasks/TASK-0001.md').is_file())
            self.assertEqual(migrate(root), {'already_migrated': True})

    def test_unknown_legacy_ids_are_not_silently_discarded(self):
        scratch = Path(__file__).resolve().parents[1] / '.work/tests'
        scratch.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as root:
            store = Store(root)
            initialize(store)
            old = store.path('.project/tasks/TASK-9999.md')
            old.parent.mkdir()
            old.write_text('+++\nid="TASK-9999"\n+++\n', encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'Unexpected'):
                migrate(root)
            self.assertTrue(old.exists())
            self.assertTrue(Service(store).checked()[1])
