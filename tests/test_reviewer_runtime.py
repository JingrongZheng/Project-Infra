import json
import shutil
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from project_infra.bootstrap import initialize
from project_infra.documents import Document
from project_infra.service import Service
from project_infra.store import Store, Conflict
from project_infra import reviewer_runtime as runtime
from project_infra.review import deliver, prepare, record, history

NOTE = 'Reviewer: test-only fixture\n\n## 已核查\nFixture check.\n\n## 主要疑点\nFixture limitation.\n'


class ReviewerRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        initialize(self.store)
        self.service = Service(self.store)
        self.plan = self.service.create('plan', 'Test delivery')

    def host(self, timeout=120):
        runtime.probe(self.store, 'host fixture', timeout=timeout)
        data = runtime.read(self.store)
        return runtime.accept(self.store, {'nonce': data['nonce'], 'independent': True, 'session': 'new-fixture-session'})

    def process(self, mode='ok', timeout=10):
        return runtime.probe(self.store, 'process fixture',
            [sys.executable, str(Path(__file__).with_name('reviewer_fixture.py')), mode], timeout)

    def write_note(self, folder):
        self.store.path(folder + '/NOTE.md').write_text(NOTE, encoding='utf-8')
        record(self.service, self.plan, folder + '/NOTE.md')

    def test_default_unavailable_and_delivery_explicitly_records_no_review(self):
        self.assertFalse(runtime.status(self.store)['enabled'])
        with self.assertRaises(ValueError):
            prepare(self.service, self.plan)
        result = deliver(self.service, self.plan)
        self.assertFalse(result['reviewed'])
        doc = self.service.checked()[0][self.plan]
        self.assertIn('未执行独立审查', doc.section('Delivery'))
        self.assertEqual(doc.section('Review'), '')

    def test_host_probe_does_not_review_or_start_exploration_work(self):
        result = self.host()
        self.assertTrue(result['enabled'])
        self.assertEqual(history(self.store, self.plan), [])
        self.assertFalse(self.store.path('.work/reviews').exists())

    def test_invalid_probe_disables_feature(self):
        runtime.probe(self.store, 'host fixture')
        with self.assertRaises(ValueError):
            runtime.accept(self.store, {'nonce': 'wrong', 'independent': True, 'session': 's'})
        self.assertFalse(runtime.status(self.store)['enabled'])

    def test_probe_timeout_and_lease_expiry(self):
        runtime.probe(self.store, 'host fixture', timeout=1)
        data = runtime.read(self.store)
        data['deadline'] = time.time() - 1
        runtime.save(self.store, data)
        with self.assertRaises(ValueError):
            runtime.accept(self.store, {'nonce': data['nonce'], 'independent': True, 'session': 's'})
        self.host()
        data = runtime.read(self.store)
        data['expires'] = time.time() - 1
        runtime.save(self.store, data)
        self.assertFalse(runtime.status(self.store)['enabled'])

    def test_environment_change_and_server_restart_require_new_probe(self):
        self.host()
        with patch('project_infra.reviewer_runtime.environment', return_value='different-machine'):
            self.assertFalse(runtime.status(self.store)['enabled'])
        from project_infra.web import make_server
        server = make_server(self.service, 0)
        server.server_close()
        self.assertFalse(runtime.status(self.store)['enabled'])

    def test_gui_and_cli_in_one_installation_share_capability(self):
        install = self.store.root / 'application'
        with patch('sys.executable', str(install / 'project-infra.exe')):
            self.host()
        with patch('sys.executable', str(install / 'ProjectInfra.exe')):
            self.assertTrue(runtime.status(self.store)['enabled'])
        with patch('sys.executable', str(self.store.root / 'other-install' / 'project-infra.exe')):
            self.assertFalse(runtime.status(self.store)['enabled'])

    def test_host_delivery_waits_for_actual_note_and_blocks_duplicate(self):
        deliver(self.service, self.plan)  # Earlier degraded delivery must not remain the latest label.
        self.host()
        result = deliver(self.service, self.plan)
        self.assertTrue(result['pending'])
        self.assertEqual(history(self.store, self.plan), [])
        with self.assertRaises(Conflict):
            deliver(self.service, self.plan)
        self.write_note(result['handoff'])
        self.assertEqual(len(history(self.store, self.plan)), 1)
        self.assertNotIn('未执行独立审查', self.service.checked()[0][self.plan].section('Delivery'))

    def test_two_rounds_survive_work_cleanup_and_both_enter_context(self):
        self.host()
        first = deliver(self.service, self.plan)['handoff']
        self.write_note(first)
        doc = self.service.checked()[0][self.plan]
        self.service.update(doc.path, doc.revision, sections={'Synthesis': 'Changed after first findings'})
        second = deliver(self.service, self.plan)['handoff']
        self.store.path(second + '/NOTE.md').write_text(NOTE.replace('Fixture limitation.', 'Second round: original limitation remains.'), encoding='utf-8')
        record(self.service, self.plan, second + '/NOTE.md')
        rounds = history(self.store, self.plan)
        self.assertEqual(len(rounds), 2)
        for entry in rounds:
            self.assertTrue(self.store.path(entry['note']).is_file())
        # Start with a new environment capability, retaining only long-term project files.
        runtime.disable(self.store, 'fixture new environment')
        scratch = self.store.path('.work')
        assert scratch.is_relative_to(self.store.root) and scratch.name == '.work'
        shutil.rmtree(scratch)
        context = self.service.context(self.plan, reviewer=True)
        self.assertIn('Fixture limitation.', context)
        self.assertIn('Second round:', context)
        self.assertIn(rounds[0]['note'], context)
        self.assertIn(rounds[1]['note'], context)

    def test_legacy_review_is_preserved_on_first_new_round(self):
        doc = self.service.checked()[0][self.plan]
        self.service.update(doc.path, doc.revision, sections={'Review': 'Legacy v0.2 finding'})
        self.host()
        self.write_note(deliver(self.service, self.plan)['handoff'])
        self.assertIn('Legacy v0.2 finding', self.service.context(self.plan, reviewer=True))

    def test_host_review_timeout_and_capability_reset_reject_notes(self):
        self.host()
        folder = deliver(self.service, self.plan)['handoff']
        self.store.path(folder + '/NOTE.md').write_text(NOTE, encoding='utf-8')
        manifest_path = self.store.path(folder + '/manifest.json')
        manifest = json.loads(manifest_path.read_text())
        manifest['deadline'] = time.time() - 1
        manifest_path.write_text(json.dumps(manifest))
        with self.assertRaises(ValueError):
            record(self.service, self.plan, folder + '/NOTE.md')
        self.assertFalse(runtime.status(self.store)['enabled'])
        self.assertEqual(history(self.store, self.plan), [])

    def test_process_probe_and_delivery_use_real_subprocess_and_save_logs(self):
        self.assertTrue(self.process()['enabled'])
        result = deliver(self.service, self.plan)
        self.assertTrue(result['reviewed'])
        self.assertEqual(len(history(self.store, self.plan)), 1)
        self.assertTrue(self.store.path(result['handoff'] + '/stdout.log').exists())

    def test_process_failures_and_timeout_disable_without_recording_review(self):
        for mode in ('failure', 'invalid', 'timeout'):
            with self.subTest(mode=mode):
                with self.assertRaises(ValueError):
                    self.process(mode, timeout=1)
                self.assertFalse(runtime.status(self.store)['enabled'])
                self.assertEqual(history(self.store, self.plan), [])

    def test_process_source_mutation_is_not_accepted(self):
        self.process('mutate')
        with self.assertRaises(Conflict):
            deliver(self.service, self.plan)
        self.assertFalse(runtime.status(self.store)['enabled'])
        self.assertEqual(history(self.store, self.plan), [])

    def test_review_process_timeout_retains_logs_without_completion(self):
        self.process('review-timeout', timeout=1)
        with self.assertRaisesRegex(ValueError, 'timed out'):
            deliver(self.service, self.plan)
        self.assertFalse(runtime.status(self.store)['enabled'])
        self.assertEqual(history(self.store, self.plan), [])
        self.assertTrue(list(self.store.path('.work/reviews').rglob('stderr.log')))

    def test_recheck_rejects_old_pending_note(self):
        self.host()
        folder = deliver(self.service, self.plan)['handoff']
        self.host()
        with self.assertRaisesRegex(ValueError, 'changed'):
            self.write_note(folder)
        self.assertEqual(history(self.store, self.plan), [])

    def test_review_then_verify_then_close(self):
        doc = self.service.checked()[0][self.plan]
        command = '"' + sys.executable + '" -c "print(123)"'
        self.service.update(doc.path, doc.revision, {'verify': [command]}, {'Synthesis': 'Fixture only'})
        self.process()
        deliver(self.service, self.plan)
        self.assertEqual(self.service.execute(self.plan, verification=True), 0)
        doc = self.service.checked()[0][self.plan]
        self.service.update(doc.path, doc.revision, {'status': 'closed', 'resolution': 'inconclusive'})
        self.assertEqual(self.service.checked()[1], [])

    def test_close_enforces_review_for_current_content_when_enabled(self):
        doc = self.service.checked()[0][self.plan]
        self.service.update(doc.path, doc.revision, sections={'Synthesis': 'Inconclusive, fixture only'})
        self.process()
        doc = self.service.checked()[0][self.plan]
        with self.assertRaises(ValueError):
            self.service.update(doc.path, doc.revision, {'status': 'closed', 'resolution': 'inconclusive'})
        deliver(self.service, self.plan)
        doc = self.service.checked()[0][self.plan]
        with self.assertRaises(ValueError):
            self.service.update(doc.path, doc.revision, {'status': 'closed', 'resolution': 'inconclusive'}, {'Synthesis': 'Changed while closing'})
        self.service.update(doc.path, doc.revision, {'status': 'closed', 'resolution': 'inconclusive'})
        self.assertEqual(self.service.checked()[0][self.plan].meta['status'], 'closed')

    def test_changed_source_invalidates_delivery_receipt(self):
        self.process()
        deliver(self.service, self.plan)
        self.store.path('shared/change.py').write_text('changed = True')
        from project_infra.review import require_delivery
        with self.assertRaises(ValueError):
            require_delivery(self.service, self.plan)

    def test_disabled_close_records_degradation_without_fake_review(self):
        doc = self.service.checked()[0][self.plan]
        self.service.update(doc.path, doc.revision, {'status': 'closed', 'resolution': 'inconclusive'},
                            {'Synthesis': 'Fixture conclusion'})
        doc = self.service.checked()[0][self.plan]
        self.assertIn('未执行独立审查', doc.section('Delivery'))
        self.assertEqual(doc.section('Review'), '')
