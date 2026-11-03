from pathlib import Path
import tempfile
import unittest

from project_infra.bootstrap import initialize
from project_infra.review import prepare, record
from project_infra.service import Service
from project_infra.store import Store, Conflict
from project_infra import reviewer_runtime as runtime


class ProjectCoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Store(self.temp.name)
        initialize(self.store)
        from project_infra.review_lock import recover
        self.addCleanup(recover, self.store, "test-cleanup")
        self.service = Service(self.store)
        self.plan = self.service.create('plan', 'test exploration')
        fixture_plan = self.service.checked()[0][self.plan]
        self.service.update(fixture_plan.path, fixture_plan.revision, sections={'Execution plan': '- [x] **共享实现整理**：结果：测试夹具没有业务实现需要抽取；不代表真实项目整理完成。'})
        self.exp = self.service.create('experiment', 'test attempt', self.plan)
        runtime.probe(self.store, 'test-only host fixture', timeout=120)
        runtime.accept(self.store, {'nonce': runtime.read(self.store)['nonce'], 'independent': True,
                                   'session': 'fixture-session-not-a-real-review'})

    def update(self, ident, fields=None, sections=None):
        doc = self.service.checked()[0][ident]
        return self.service.update(doc.path, doc.revision, fields, sections)

    def filled_note(self, folder):
        path = folder + '/NOTE.md'
        self.store.path(path).write_text('''# Review note
Reviewer: independent test fixture (not an actual model review)

## 已核查
FIXTURE_EVIDENCE: checked the supplied sample, not a production claim.

## 主要疑点
FIXTURE_FINDING: the sample does not establish general applicability.

## 未覆盖与下一步
Need actual review before any real delivery.
''', encoding='utf-8')
        return path

    def test_blank_project_has_knowledge_and_independent_code_directories(self):
        for path in ['knowledge/index.md', 'shared/README.md', 'experiments/README.md']:
            self.assertTrue(self.store.path(path).is_file())
        p = self.store.path('knowledge/index.md')
        p.write_text('owner-maintained knowledge', encoding='utf-8')
        initialize(self.store)
        self.assertEqual(p.read_text(), 'owner-maintained knowledge')

    def test_unsupported_project_format_refuses_update_create_and_reinitialization(self):
        target = self.service.checked()[0][self.plan]
        original = self.store.path(target.path).read_bytes()
        config = self.store.path('.project/config.toml')
        for schema in ('3', '"2"'):
            with self.subTest(schema=schema):
                config.write_text('schema_version = ' + schema + '\n')
                self.assertTrue(any('schema_version' in error for error in self.service.checked()[1]))
                with self.assertRaises(ValueError):
                    self.service.update(target.path, target.revision, {'title': 'must not write'})
                with self.assertRaises(ValueError):
                    self.service.create('plan', 'must not create')
                with self.assertRaises(ValueError):
                    initialize(self.store)
                self.assertEqual(self.store.path(target.path).read_bytes(), original)

    def test_context_reads_only_index_and_explicitly_promoted_knowledge(self):
        self.store.path('knowledge/scope.md').write_text('REUSABLE_NEGATIVE_BOUNDARY', encoding='utf-8')
        self.store.path('knowledge/unrelated.md').write_text('DO_NOT_LOAD_EVERYTHING', encoding='utf-8')
        self.update(self.exp, {'artifacts_promoted': ['knowledge/scope.md']})
        text = self.service.context(self.plan)
        self.assertIn('knowledge/index.md', text)
        self.assertIn('REUSABLE_NEGATIVE_BOUNDARY', text)
        self.assertNotIn('DO_NOT_LOAD_EVERYTHING', text)

    def test_review_context_contains_prior_conclusion_and_review(self):
        self.update(self.exp, sections={'Conclusion': 'PRIOR_CONCLUSION', 'Review': 'PRIOR_REVIEW_NOTE'})
        text = self.service.context(self.plan, reviewer=True)
        self.assertIn('PRIOR_CONCLUSION', text)
        self.assertIn('PRIOR_REVIEW_NOTE', text)

    def test_experiment_context_follows_updated_parent_execution_plan(self):
        self.update(self.plan, sections={'Execution plan': '1. Compare candidate inputs.\n2. Reuse shared/metrics.py before parallel validation.'})
        first = self.service.context(self.exp)
        self.assertIn('Compare candidate inputs.', first)
        self.assertIn('shared/metrics.py', first)
        self.update(self.plan, sections={'Execution plan': '1. New evidence: defer parallel validation.\n2. Extract the confirmed shared entry before the next batch.'})
        current = self.service.context(self.exp)
        self.assertIn('New evidence: defer', current)
        self.assertNotIn('Compare candidate inputs.', current)
        self.assertEqual(self.service.checked()[0][self.exp].section('Execution plan'), '')

    def test_prepare_does_not_fabricate_review_and_empty_note_is_rejected(self):
        folder = prepare(self.service, self.plan)
        self.assertIn('冻结项目写权限', self.store.path(folder + '/context.md').read_text(encoding='utf-8'))
        self.assertEqual(self.service.checked()[0][self.plan].section('Review'), '')
        with self.assertRaises(ValueError):
            record(self.service, self.plan, folder + '/NOTE.md')

    def test_review_import_retains_findings_in_review_without_closing(self):
        folder = prepare(self.service, self.plan)
        path = self.filled_note(folder)
        record(self.service, self.plan, path)
        doc = self.service.checked()[0][self.plan]
        self.assertIn('FIXTURE_FINDING', doc.section('Review'))
        self.assertEqual(doc.section('主要疑点'), '')
        self.assertEqual(doc.meta['status'], 'active')

    def test_review_blocks_source_changes_and_rejects_cancelled_handoff(self):
        folder = prepare(self.service, self.plan)
        path = self.filled_note(folder)
        with self.assertRaises(PermissionError):
            self.store.path('shared/metrics.py').write_text('def score(): return 1\n')
        runtime.disable(self.store, 'cancel fixture review')
        self.store.path('shared/metrics.py').write_text('def score(): return 1\n')
        with self.assertRaises(ValueError):
            record(self.service, self.plan, path)
        self.assertEqual(self.service.checked()[0][self.plan].section('Review'), '')

    def test_review_from_different_target_or_arbitrary_note_is_rejected(self):
        self.store.path('random.md').write_text('Not a prepared review')
        folder = prepare(self.service, self.plan)
        path = self.filled_note(folder)
        with self.assertRaises(ValueError):
            record(self.service, self.exp, path)
        with self.assertRaises(ValueError):
            record(self.service, self.plan, 'random.md')
