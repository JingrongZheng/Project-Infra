import json
from pathlib import Path
import tempfile
import threading
import unittest
import subprocess
import sys
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from project_infra.bootstrap import initialize
from project_infra.documents import Document
from project_infra.review import deliver, prepare
from project_infra.service import Service
from project_infra.store import Store
from project_infra.web import make_server
from project_infra import reviewer_runtime as runtime

DONE = '- [x] **共享实现整理**：结果：沿用 shared/metrics.py，实验只保留调用入口；已核对 TOOLKIT.md 并重跑受影响入口。'


class ExecutionWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        initialize(self.store)
        from project_infra.review_lock import recover
        self.addCleanup(recover, self.store, "test-cleanup")
        self.service = Service(self.store)
        self.plan = self.service.create('plan', 'A real pending execution step')

    def doc(self):
        return self.service.checked()[0][self.plan]

    def steps(self, text):
        doc = self.doc()
        self.service.update(doc.path, doc.revision, sections={'Execution plan': text})

    def close(self):
        doc = self.doc()
        return self.service.update(doc.path, doc.revision, {'status': 'closed', 'resolution': 'inconclusive'},
                                   {'Synthesis': 'Protocol fixture, no research claim.'})

    def test_new_plan_contains_an_actual_unfinished_step(self):
        self.assertIn('- [ ] **共享实现整理**', self.doc().section('Execution plan'))
        before = self.doc().raw
        with self.assertRaisesRegex(ValueError, '先执行'):
            self.close()
        self.assertEqual(self.doc().raw, before)
        with self.assertRaisesRegex(ValueError, '先执行'):
            deliver(self.service, self.plan)

    def test_missing_step_and_merely_checking_template_do_not_complete_work(self):
        self.steps('1. Investigate the actual problem.\n2. Compare alternatives.')
        with self.assertRaisesRegex(ValueError, '复选步骤'):
            self.close()
        self.steps('- [x] **共享实现整理**：完成后在本步骤写“结果：”及具体处理。')
        with self.assertRaisesRegex(ValueError, '缺少'):
            self.close()

    def test_fenced_examples_and_duplicate_items_are_not_a_completed_step(self):
        for text in ['```md\n' + DONE + '\n```', DONE + '\n- [ ] **共享实现整理**：another pending item']:
            with self.subTest(text=text):
                self.steps(text)
                with self.assertRaisesRegex(ValueError, '复选步骤'):
                    self.close()

    def test_steps_can_move_and_change_while_shared_work_is_recorded(self):
        self.steps('1. [ ] Run the next research experiment.\n' + DONE + '\n3. [ ] Owner decides future work.')
        self.close()
        self.assertEqual(self.doc().meta['status'], 'closed')
        self.assertIn('未执行独立审查', self.doc().section('Delivery'))

    def test_no_extraction_is_valid_only_when_a_reason_is_written(self):
        self.steps('- [x] 共享实现整理：\n  结果：本 Plan 仅分析论文，无新增代码，无需抽取。')
        self.close()
        self.assertEqual(self.service.checked()[1], [])

    def test_extracting_a_real_shared_module_then_recording_the_result_allows_close(self):
        runner = self.store.path('experiments/measure.py')
        runner.write_text('def score(values): return sum(values)\nprint(score([1, 2, 3]))\n', encoding='utf-8')
        command = [sys.executable, '-m', 'experiments.measure']
        before = subprocess.check_output(command, cwd=self.store.root, text=True).strip()
        self.store.path('shared/metrics.py').write_text('def score(values): return sum(values)\n', encoding='utf-8')
        runner.write_text('from shared.metrics import score\nprint(score([1, 2, 3]))\n', encoding='utf-8')
        after = subprocess.check_output(command, cwd=self.store.root, text=True).strip()
        self.assertEqual(before, after)
        self.assertEqual(after, '6')
        toolkit = self.store.read('TOOLKIT.md')
        self.service.update('TOOLKIT.md', toolkit.revision, raw='# Shared code\n\nshared/metrics.py: from shared.metrics import score\n')
        self.steps('- [x] **共享实现整理**：检查本轮实现。\n  结果：score 已抽到 shared/metrics.py，实验改为导入，更新 TOOLKIT.md；实际重跑前后输出均为 6。')
        self.close()
        self.assertEqual(self.service.checked()[1], [])

    def test_independent_review_does_not_start_before_the_step_is_done(self):
        runtime.probe(self.store, 'test host')
        runtime.accept(self.store, {'nonce': runtime.read(self.store)['nonce'], 'independent': True, 'session': 'fixture'})
        with self.assertRaisesRegex(ValueError, '先执行'):
            prepare(self.service, self.plan)
        self.assertFalse(self.store.path('.work/reviews').exists())
        self.steps(DONE)
        self.assertTrue(prepare(self.service, self.plan).startswith('.work/reviews/'))

    def test_experiment_completion_does_not_repeat_the_plan_step(self):
        exp = self.service.create('experiment', 'Continue exploration', self.plan)
        doc = self.service.checked()[0][exp]
        self.service.update(doc.path, doc.revision, {'status': 'closed'}, {'Conclusion': 'Fixture observation'})
        self.assertEqual(self.service.checked()[0][exp].meta['status'], 'closed')
        self.assertIn('- [ ] **共享实现整理**', self.doc().section('Execution plan'))

    def test_abandoned_plan_does_not_force_code_extraction(self):
        doc = self.doc()
        self.service.update(doc.path, doc.revision, {'status': 'closed', 'resolution': 'abandoned'},
                            {'Synthesis': 'No valuable implementation was retained.'})
        self.assertEqual(self.service.checked()[1], [])

    def test_direct_file_edit_is_caught_by_validate(self):
        doc = self.doc()
        self.store.path(doc.path).write_text(doc.patch({'status': 'closed', 'resolution': 'inconclusive'},
            {'Synthesis': 'fixture', 'Delivery': 'No independent reviewer'}), encoding='utf-8')
        self.assertTrue(any('先执行' in e for e in self.service.checked()[1]))

    def test_web_close_uses_the_same_gate_and_preserves_failed_write(self):
        server = make_server(self.service, 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 3)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        url = f'http://127.0.0.1:{server.server_port}'
        with urlopen(url + '/api/state') as response:
            state = json.load(response)
        doc = self.doc()
        request = Request(url + '/api/update', json.dumps({'path': doc.path, 'revision': doc.revision,
            'fields': {'status': 'closed', 'resolution': 'inconclusive'},
            'sections': {'Synthesis': 'Fixture conclusion'}}).encode(),
            {'Content-Type': 'application/json', 'X-Infra-Token': state['token']})
        with self.assertRaises(HTTPError) as failure:
            urlopen(request)
        self.assertEqual(failure.exception.code, 400)
        self.assertEqual(self.doc().revision, doc.revision)
