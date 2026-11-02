import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from project_infra.bootstrap import initialize
from project_infra.documents import Document, digest
from project_infra.service import Service
from project_infra.store import Store, Conflict
from project_infra.web import make_server, ProjectionCache


class Fixture(unittest.TestCase):
    def setUp(self):
        scratch = Path(__file__).resolve().parents[1] / '.work' / 'tests'
        scratch.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.tmp.cleanup)
        self.store = Store(self.tmp.name)
        initialize(self.store)
        self.service = Service(self.store)

    def get(self, ident):
        return self.service.checked()[0][ident]

    def update(self, ident, fields=None, sections=None):
        doc = self.get(ident)
        return self.service.update(doc.path, doc.revision, fields, sections)

    def plan(self):
        return self.service.create('plan', '能否可靠接续探索？')


class ProjectTests(Fixture):
    def test_compact_context_preserves_continuation_and_reusable_setup_guidance(self):
        plan = self.plan()
        exp = self.service.create('experiment', '界面试用', plan)
        self.update(plan, sections={'Continuation': 'PLAN_WAITING_FOR_OWNER; tests do not replace acceptance'})
        self.update(exp, sections={'Continuation': 'EXP_WAITING_FOR_FEEDBACK; continue only after response'})
        self.assertIn('EXP_WAITING_FOR_FEEDBACK', self.service.context(plan))
        self.assertIn('PLAN_WAITING_FOR_OWNER', self.service.context(exp))
        self.assertIn('EXP_WAITING_FOR_FEEDBACK', self.service.context(plan, full=True))
        self.assertIn('docs/verification.md', self.service.context(exp))
        guide = self.store.path('docs/verification.md').read_text(encoding='utf-8')
        self.assertIn('环境阻断', guide)
        self.assertNotIn(str(Path.home()), guide, 'New projects must not inherit this machine path')

    def test_plan_starts_active_and_draft_is_rejected_without_writes(self):
        proposal = self.service.create('proposal', '尚未决定开展的方向')
        plan = self.service.create('plan', '开始探索', proposal)
        self.assertEqual(self.get(plan).meta['status'], 'active')
        self.assertEqual(self.service.state()['states']['plan'], ['active', 'paused', 'closed'])
        self.assertNotIn('status', self.get(proposal).meta)
        original = self.get(plan).raw
        with self.assertRaises(ValueError):
            self.update(plan, {'status': 'draft'})
        self.assertEqual(self.get(plan).raw, original)
        self.update(plan, {'status': 'paused'})
        self.update(plan, {'status': 'active'})
        self.assertEqual(self.service.checked()[1], [])

    def test_shared_toolkit_is_visible_editable_and_in_agent_context(self):
        plan = self.plan()
        index = self.store.read('TOOLKIT.md')
        self.service.update('TOOLKIT.md', index.revision, raw='# 共享工具包\n\nSHARED_REUSE_SENTINEL\n先复用现有代码。\n')
        self.assertIn('SHARED_REUSE_SENTINEL', self.service.state()['toolkit']['body'])
        self.assertIn('SHARED_REUSE_SENTINEL', self.service.context(plan))
        with self.assertRaises(Conflict):
            self.service.update('TOOLKIT.md', index.revision, raw='stale overwrite')
        self.assertIn('TOOLKIT.md', self.store.path('AGENTS.md').read_text(encoding='utf-8'))

    def test_invalid_toolkit_keeps_last_valid_projection(self):
        cache = ProjectionCache(self.service)
        good = cache.get()
        self.store.path('TOOLKIT.md').write_text('+++\ninvalid=[\n+++\n', encoding='utf-8')
        result = cache.get()
        self.assertTrue(result['errors'])
        self.assertTrue(result['stale'])
        self.assertEqual(result['toolkit'], good['toolkit'])

    def test_experiment_lineage_supports_parallel_chain_fork_and_merge(self):
        plan = self.plan()
        a = self.service.create('experiment', '独立验证 A', plan)
        b = self.service.create('experiment', '独立验证 B', plan)
        c = self.service.create('experiment', '根据 A 继续', plan, predecessors=[a])
        d = self.service.create('experiment', '从 A 分支', plan, predecessors=[a])
        e = self.service.create('experiment', '综合 B C D', plan, predecessors=[b, c, d])
        self.assertEqual(self.get(a).meta['predecessors'], [])
        self.assertEqual(self.get(e).meta['predecessors'], [b, c, d])
        self.assertEqual(self.service.checked()[1], [])
        self.assertIn(f'{e} <- {b}, {c}, {d}', self.service.context(plan))
        self.assertIn(f'{e} <- {b}, {c}, {d}', self.service.context(c))
        self.assertFalse(any(o['kind'] == 'task' for o in self.service.state()['objects']))

    def test_experiment_lineage_rejects_invalid_edges_without_writes(self):
        plan = self.plan()
        other_plan = self.plan()
        a = self.service.create('experiment', 'A', plan)
        b = self.service.create('experiment', 'B', plan, predecessors=[a])
        foreign = self.service.create('experiment', 'different Plan', other_plan)
        original = self.get(a).raw
        for invalid, message in [([a], 'itself'), ([b], 'cycle'), ([foreign], 'same Plan'),
                                 (['EXP-9999'], 'invalid reference'), ([plan], 'invalid reference'),
                                 ([b, b], 'duplicate'), ('EXP-0001', 'string array'), ([1], 'string array')]:
            with self.subTest(invalid=invalid), self.assertRaisesRegex(ValueError, message):
                self.update(a, {'predecessors': invalid})
            self.assertEqual(self.get(a).raw, original)

    def test_failed_lineage_creation_does_not_change_parent_or_allocate_id(self):
        plan = self.plan()
        old = self.get(plan).raw
        with self.assertRaises(ValueError):
            self.service.create('experiment', 'invalid', plan, predecessors=['EXP-9999'])
        self.assertEqual(self.get(plan).raw, old)
        self.assertEqual(self.service.create('experiment', 'valid', plan), 'EXP-0001')

    def test_legacy_experiment_without_predecessors_remains_a_root(self):
        plan = self.plan()
        exp = self.service.create('experiment', 'legacy', plan)
        self.update(exp, {'predecessors': None})
        self.assertEqual(self.service.checked()[1], [])
        self.assertIn(f'{exp} <- {plan}', self.service.context(plan))

    def test_experiment_predecessors_do_not_replace_before_after_evidence(self):
        plan = self.plan()
        a = self.service.create('experiment', '基线', plan)
        b = self.service.create('experiment', '候选', plan, predecessors=[a])
        self.store.path('before.txt').write_text('baseline', encoding='utf-8')
        self.store.path('after.txt').write_text('candidate', encoding='utf-8')
        self.update(b, {'before': ['before.txt'], 'after': ['after.txt']})
        self.assertEqual(self.service.checked()[1], [])
        self.assertEqual(self.get(b).meta['predecessors'], [a])
        self.assertEqual(self.get(b).meta['after'], ['after.txt'])

    def test_closed_plan_does_not_require_task_after_exploration(self):
        plan = self.plan()
        exp = self.service.create('experiment', '完成验证', plan)
        self.update(exp, {'status': 'closed'}, {'Conclusion': '支持保留已有方案，无需交付改动。'})
        self.update(plan, {'status': 'closed', 'resolution': 'supported'},
                    {'Synthesis': '已有方案符合要求，不创建 Task。', 'Review': '测试记录，不冒充实际项目审查。'})
        self.assertEqual(self.service.checked()[1], [])
        self.assertNotIn('follow_up_tasks', self.get(plan).meta)

    def test_bootstrap_is_valid_and_does_not_overwrite(self):
        p = self.store.path('AGENTS.md')
        p.write_text('user instructions', encoding='utf-8')
        initialize(self.store)
        self.assertEqual(p.read_text(encoding='utf-8'), 'user instructions')
        self.assertEqual(self.service.checked()[1], [])

    def test_create_reciprocal_plan_and_experiment(self):
        prop = self.service.create('proposal', '方向')
        plan = self.service.create('plan', '问题', prop)
        exp = self.service.create('experiment', '试一次', plan)
        self.assertEqual(self.get(exp).meta['plan'], plan)
        self.assertEqual(self.get(plan).meta['experiments'], [exp])
        self.assertEqual(self.get(prop).meta['plans'], [plan])
        self.assertEqual(self.service.checked()[1], [])

    def test_experiment_cannot_be_orphaned(self):
        with self.assertRaises(ValueError):
            self.service.create('experiment', 'missing Plan')

    def test_deleted_ids_are_not_reused(self):
        first = self.plan()
        self.store.path(self.get(first).path).unlink()
        self.assertEqual(self.plan(), 'PLAN-0002')

    def test_new_field_patch_preserves_toml_tables_comments_and_crlf(self):
        raw = '+++\r\n# keep\r\ntitle = "old"\r\n\r\n[[mainline]]\r\nid = "a"\r\n+++\r\n\r\n## Notes\r\nkeep body\r\n'
        doc = Document('x', raw, '')
        result = doc.patch({'summary': '中文摘要', 'title': 'new'})
        self.assertIn('# keep\r\n', result)
        self.assertIn('[[mainline]]', result)
        self.assertEqual(Document('x', result, '').meta['summary'], '中文摘要')
        self.assertNotIn('\n', result.replace('\r\n', ''))

    def test_code_fence_headings_do_not_split_sections(self):
        doc = Document('x', '## Notes\n```md\n## Conclusion\nnot real\n```\n## Conclusion\nreal\n', '')
        self.assertEqual(doc.section('Conclusion'), 'real')
        result = Document('x', doc.patch(sections={'Conclusion': 'changed'}), '')
        self.assertIn('not real', result.section('Notes'))
        self.assertEqual(result.section('Conclusion'), 'changed')

    def test_stale_revision_is_rejected_and_file_preserved(self):
        plan = self.plan()
        old = self.get(plan)
        self.update(plan, {'summary': 'external change'})
        with self.assertRaises(Conflict):
            self.service.update(old.path, old.revision, {'title': 'stale browser'})
        self.assertEqual(self.get(plan).meta['summary'], 'external change')

    def test_invalid_references_and_false_close_do_not_write(self):
        plan = self.plan()
        original = self.get(plan).raw
        with self.assertRaises(ValueError):
            self.update(plan, {'status': 'closed', 'resolution': 'supported'})
        with self.assertRaises(ValueError):
            self.update(plan, {'experiments': ['EXP-9999']})
        self.assertEqual(self.get(plan).raw, original)

    def test_plan_resolution_and_experiment_conclusion(self):
        plan = self.plan()
        exp = self.service.create('experiment', '实际尝试', plan)
        with self.assertRaises(ValueError):
            self.update(exp, {'status': 'closed'})
        self.update(exp, {'status': 'closed'}, {'Conclusion': '对这个例子有效，尚不能推广。'})
        self.update(plan, {'status': 'closed', 'resolution': 'supported'},
                    {'Synthesis': '此问题有支持证据；当前主干保持原状。', 'Review': '有限审查：测试夹具，仅检查对象结构。'})
        self.assertEqual(self.get(plan).meta['resolution'], 'supported')
        self.assertEqual(self.get(exp).meta['status'], 'closed')

    def test_abandoned_plan_does_not_require_experiment_or_review(self):
        plan = self.plan()
        self.update(plan, {'status': 'closed', 'resolution': 'abandoned'}, {'Synthesis': '停止投入，没有有效结论。'})
        self.assertEqual(self.service.checked()[1], [])

    def test_mainline_cycle_or_missing_anchor_rejected(self):
        project = self.get('PROJECT')
        invalid = '+++\n[[mainline]]\nid="a"\nsection="x"\nafter=["a"]\n+++\n\n<a id="x"></a>\n## A\nbody\n'
        with self.assertRaisesRegex(ValueError, 'cycle'):
            self.service.update(project.path, project.revision, raw=invalid)

    def test_context_outline_does_not_expand_every_experiment(self):
        plan = self.plan()
        exp = self.service.create('experiment', '解释清楚尝试', plan)
        self.update(exp, {'summary': '尝试用脚本同步，发现可以省去手工维护。'}, {'Notes': 'DETAIL_SENTINEL'})
        compact = self.service.context(plan, reviewer=True)
        self.assertIn('省去手工维护', compact)
        self.assertIn('质疑者初始化', compact)
        self.assertNotIn('DETAIL_SENTINEL', compact)
        self.assertIn('DETAIL_SENTINEL', self.service.context(plan, full=True))

    def test_invalid_file_keeps_last_valid_projection(self):
        plan = self.plan()
        cache = ProjectionCache(self.service)
        first = cache.get()
        self.store.path(self.get(plan).path).write_text('+++\ninvalid = [\n+++\n', encoding='utf-8')
        state = cache.get()
        self.assertTrue(state['stale'])
        self.assertEqual(state['objects'], first['objects'])
        self.assertTrue(state['errors'])

    def test_unpaired_before_after_blocks_comparison_save(self):
        plan = self.plan()
        exp = self.service.create('experiment', '比较', plan)
        with self.assertRaisesRegex(ValueError, 'Before / After'):
            self.update(exp, {'before': ['before.txt']})

    def prepared_experiment(self):
        plan = self.plan()
        exp = self.service.create('experiment', '实际变更', plan)
        self.store.path('before.txt').write_text('before', encoding='utf-8')
        self.store.path('after.txt').write_text('after', encoding='utf-8')
        self.update(exp, {'status': 'active', 'before': ['before.txt'], 'after': ['after.txt'],
                          'verify': [f'"{sys.executable}" -c "print(123)"']},
                    {'Conclusion': '测试夹具结论，不是真实方案审查。', 'Verification': '已准备重跑验证。',
                     'Before / After': '同一测试场景的前后输出。'})
        return exp

    def test_experiment_close_requires_current_successful_verification(self):
        exp = self.prepared_experiment()
        with self.assertRaisesRegex(ValueError, 'verify'):
            self.update(exp, {'status': 'closed'})
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.service.execute(exp, True), 0)
        self.update(exp, {'status': 'closed'})
        self.assertEqual(self.get(exp).meta['status'], 'closed')

    def test_source_change_invalidates_verification_receipt(self):
        exp = self.prepared_experiment()
        self.service.execute(exp, True)
        self.store.path('model.py').write_text('changed', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'verify'):
            self.update(exp, {'status': 'closed'})

    def test_cannot_change_evidence_while_closing_using_old_receipt(self):
        exp = self.prepared_experiment()
        self.service.execute(exp, True)
        with self.assertRaisesRegex(ValueError, 'Save changed'):
            self.update(exp, {'status': 'closed'}, {'Conclusion': '偷换结论'})

    def test_no_task_kind_states_templates_or_creation(self):
        from project_infra.documents import KINDS, STATES
        self.assertNotIn('task', KINDS)
        self.assertNotIn('task', STATES)
        self.assertFalse(self.store.path('.project/tasks').exists())
        self.assertFalse(self.store.path('.project/templates/task.md').exists())
        with self.assertRaises(ValueError):
            self.service.create('task', '退役对象')

    def test_plan_acceptance_is_retained_without_forcing_experiment_review(self):
        plan = self.plan()
        exp = self.service.create('experiment', '具体尝试', plan)
        self.update(exp, {'status': 'closed'}, {'Conclusion': '已验证此例，未声称独立审查。'})
        self.update(plan, sections={'Acceptance criteria': '- [ ] 人工确认'})
        with self.assertRaisesRegex(ValueError, 'acceptance'):
            self.update(plan, {'status': 'closed', 'resolution': 'supported'},
                        {'Synthesis': '综合结论', 'Review': '夹具审查记录'})

    def test_single_result_is_not_forced_into_before_after_fields(self):
        plan = self.plan()
        exp = self.service.create('experiment', '一张图包含全部指标', plan)
        self.store.path('metrics.csv').write_text('method,accuracy\nbaseline,0.8\ncandidate,0.9\n', encoding='utf-8')
        self.update(exp, {'status': 'closed', 'evidence': ['metrics.csv']},
                    {'Results': '测试夹具数据，不是真实性能。', 'Conclusion': '仅检验单个结果引用可保存。'})
        doc = self.get(exp)
        self.assertNotIn('before', doc.meta)
        self.assertNotIn('after', doc.meta)
        self.assertEqual(self.service.checked()[1], [])
        self.assertIn('metrics.csv', self.service.context(plan))

    def test_inline_results_and_no_artifact_exploration_can_close(self):
        plan = self.plan()
        exp = self.service.create('experiment', '直接记录结果表', plan)
        self.update(exp, {'status': 'closed'}, {'Results': '| A | B |\n|---|---|\n| 1 | 2 |', 'Conclusion': '仅为格式夹具。'})
        self.assertEqual(self.service.checked()[1], [])
        other = self.service.create('experiment', '仅得出定性结论', plan)
        self.update(other, {'status': 'closed'}, {'Conclusion': '没有图表或对照，保留有价值的定性结论。'})
        self.assertEqual(self.service.checked()[1], [])

    def test_general_results_validate_paths_and_array_types(self):
        exp = self.service.create('experiment', '结果路径检查', self.plan())
        for evidence in [['missing.png'], '../private.txt', [1], ['../private.txt']]:
            with self.subTest(evidence=evidence), self.assertRaises(ValueError):
                self.update(exp, {'evidence': evidence})

    def test_context_includes_paired_demonstration_paths(self):
        exp = self.prepared_experiment()
        plan = self.get(exp).meta['plan']
        self.assertIn('before.txt', self.service.context(plan))
        self.assertIn('after.txt', self.service.context(plan))

    def test_cannot_write_through_path_traversal(self):
        with self.assertRaises(ValueError):
            self.store.path('../secret')
        with self.assertRaises(ValueError):
            self.service.update('../secret.md', 'x', raw='bad')

    def test_transaction_rolls_back_on_replace_failure(self):
        plan = self.plan()
        old = self.get(plan)
        real_replace = __import__('os').replace
        def fail_second(src, dst):
            if str(dst).endswith('second.txt'):
                raise OSError('injected failure')
            return real_replace(src, dst)
        with self.store.locked():
            with patch('project_infra.store.os.replace', side_effect=fail_second):
                with self.assertRaises(OSError):
                    self.store.commit_locked({old.path: old.patch({'title': 'changed'}), 'second.txt': 'new'},
                                             {old.path: old.revision, 'second.txt': None})
        self.assertEqual(self.get(plan).raw, old.raw)
        self.assertFalse(self.store.path('.project/transaction.json').exists())

    def test_library_local_file_must_exist(self):
        path = 'library/index.toml'
        old = self.store.path(path).read_bytes()
        with self.assertRaisesRegex(ValueError, 'Missing file'):
            self.service.update(path, digest(old), raw='[[entry]]\nid="REF-0001"\ntitle="manual"\nlocation="files/missing.pdf"\n')

    def test_invalid_initial_project_does_not_project_partial_objects(self):
        self.plan()
        self.store.path('PROJECT.md').write_text('+++\nmainline=[\n+++\n', encoding='utf-8')
        state = ProjectionCache(self.service).get()
        self.assertTrue(state['errors'])
        self.assertEqual(state['objects'], [])


class HTTPTests(Fixture):
    def setUp(self):
        super().setUp()
        self.server = make_server(self.service, 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        self.url = f'http://127.0.0.1:{self.server.server_port}'

    def request(self, path, body=None, token=None):
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['X-Infra-Token'] = token
        req = Request(self.url + path, data=json.dumps(body).encode() if body is not None else None, headers=headers)
        with urlopen(req, timeout=5) as r:
            return json.loads(r.read())

    def test_http_create_update_and_reject_stale_browser(self):
        state = self.request('/api/state')
        ident = self.request('/api/create', {'kind': 'plan', 'title': '浏览器探索'}, state['token'])['id']
        obj = self.request('/api/state')['objects'][0]
        payload = {'path': obj['path'], 'revision': obj['revision'], 'fields': {'summary': '来自界面'}}
        self.request('/api/update', payload, state['token'])
        self.assertEqual(self.get(ident).meta['summary'], '来自界面')
        with self.assertRaises(HTTPError) as conflict:
            self.request('/api/update', payload, state['token'])
        self.assertEqual(conflict.exception.code, 409)

    def test_original_visual_asset_is_served_only_at_fixed_static_path(self):
        with urlopen(self.url + '/facets.svg', timeout=5) as response:
            self.assertEqual(response.headers.get_content_type(), 'image/svg+xml')
            self.assertIn(b'<svg', response.read())
            self.assertIn("object-src 'none'", response.headers['Content-Security-Policy'])
        with self.assertRaises(HTTPError) as denied:
            self.request('/project_infra/static/facets.svg')
        self.assertEqual(denied.exception.code, 404)

    def test_no_unauthorized_post_or_arbitrary_file_read(self):
        with self.assertRaises(HTTPError) as denied:
            self.request('/api/create', {'kind': 'plan', 'title': 'bad'})
        self.assertEqual(denied.exception.code, 403)
        with self.assertRaises(HTTPError):
            self.request('/api/artifact?path=AGENTS.md')

    def test_http_experiment_lineage_creation_and_update(self):
        token = self.request('/api/state')['token']
        plan = self.plan()
        a = self.request('/api/create', {'kind': 'experiment', 'title': 'A', 'parent': plan}, token)['id']
        b = self.request('/api/create', {'kind': 'experiment', 'title': 'B', 'parent': plan, 'predecessors': [a]}, token)['id']
        self.assertEqual(self.get(b).meta['predecessors'], [a])
        doc = self.get(a)
        with self.assertRaises(HTTPError) as bad:
            self.request('/api/update', {'path': doc.path, 'revision': doc.revision, 'fields': {'predecessors': [b]}}, token)
        self.assertEqual(bad.exception.code, 400)
        self.assertEqual(self.get(a).meta['predecessors'], [])
        with self.assertRaises(HTTPError):
            self.request('/api/artifact?path=' + a)  # predecessor IDs are not evidence paths

    def test_general_result_reference_is_served_without_paired_fields(self):
        exp = self.service.create('experiment', '单份指标表', self.plan())
        self.store.path('metrics.csv').write_text('method,score\na,1\nb,2\n', encoding='utf-8')
        doc = self.get(exp)
        token = self.request('/api/state')['token']
        self.request('/api/update', {'path': doc.path, 'revision': doc.revision,
                                     'fields': {'evidence': ['metrics.csv']}}, token)
        with urlopen(self.url + '/api/artifact?path=metrics.csv', timeout=5) as response:
            self.assertIn(b'method,score', response.read())
        self.assertNotIn('before', self.get(exp).meta)
        self.assertNotIn('after', self.get(exp).meta)


if __name__ == '__main__':
    unittest.main()
