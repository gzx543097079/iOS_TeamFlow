import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('delivery', ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
REQ = 'REQ-20260911-999'


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        d.git(self.root, 'init', '-q')
        d.git(self.root, 'config', 'user.name', 'Test')
        d.git(self.root, 'config', 'user.email', 'test@example.invalid')
        (self.root / 'requirements').mkdir()
        (self.root / 'requirements' / (REQ + '.md')).write_text('# 需求')
        self.commit('one', 'Requirement: ' + REQ)

    def commit(self, content, message):
        (self.root / 'code.txt').write_text(content)
        d.git(self.root, 'add', '.')
        d.git(self.root, 'commit', '-qm', message)
        return d.resolve(self.root, 'HEAD')

    def test_local_commit_and_tag_not_release_or_merge(self):
        d.git(self.root, 'tag', 'v1')
        path, data = d.load(self.root, REQ)
        d.refresh(self.root, data)
        self.assertTrue(data['snapshot']['committed'])
        self.assertEqual('未核实', data['snapshot']['merged'])
        self.assertEqual([], data['snapshot']['releases'])
        d.save(self.root, path, data, 'refresh')
        self.assertIn(REQ, (self.root / 'requirements/DELIVERY.md').read_text())

    def test_complete_stales_when_implementation_changes(self):
        _, data = d.load(self.root, REQ)
        data['development'] = {'state': '✅ 开发完成', 'commits': d.commits_for(self.root, REQ)}
        self.commit('two', 'Requirement: ' + REQ)
        d.refresh(self.root, data)
        self.assertIn('需复核', data['snapshot']['development'])

    def test_verified_merge_release_and_draft(self):
        sha = d.resolve(self.root, 'HEAD')
        d.git(self.root, 'tag', 'v1')
        _, data = d.load(self.root, REQ)
        data['prs'] = ['https://github.com/example/repo/pull/1']
        pr = {'state': 'MERGED', 'mergedAt': 'date', 'mergeCommit': {'oid': sha}, 'commits': [{'oid': sha}]}
        release = {'isDraft': False, 'isPrerelease': False, 'publishedAt': 'date', 'url': 'https://example.invalid/v1'}
        with patch.object(d, 'gh_json', side_effect=[pr, release]), patch.object(d, 'remote_tag_commit', return_value=sha):
            d.refresh(self.root, data, True)
        self.assertEqual('✅ 已合并', data['snapshot']['merged'])
        self.assertEqual('✅ 已发布', data['snapshot']['release_status'])
        release['isDraft'] = True
        with patch.object(d, 'gh_json', side_effect=[pr, release]), patch.object(d, 'remote_tag_commit', return_value=sha):
            d.refresh(self.root, data, True)
        self.assertEqual([], data['snapshot']['releases'])

    def test_remote_tag_mismatch_not_published(self):
        d.git(self.root, 'tag', 'v1')
        _, data = d.load(self.root, REQ)
        release = {'isDraft': False, 'isPrerelease': False, 'publishedAt': 'date', 'url': 'https://example.invalid/v1'}
        with patch.object(d, 'gh_json', return_value=release), patch.object(d, 'remote_tag_commit', return_value='different'):
            d.refresh(self.root, data, True)
        self.assertEqual([], data['snapshot']['releases'])
        self.assertIn('未核实', data['snapshot']['release_status'])

    def test_old_release_does_not_cover_new_commit(self):
        d.git(self.root, 'tag', 'v1')
        self.commit('two', 'Requirement: ' + REQ)
        _, data = d.load(self.root, REQ)
        with patch.object(d, 'gh_json') as gh:
            d.refresh(self.root, data, True)
            gh.assert_not_called()
        self.assertEqual([], data['snapshot']['releases'])

    def test_remote_failure_not_marked_pass(self):
        _, data = d.load(self.root, REQ)
        data['prs'] = ['https://github.com/example/repo/pull/1']
        with patch.object(d, 'gh_json', side_effect=OSError('offline')):
            d.refresh(self.root, data, True)
        self.assertNotEqual('✅ 已合并', data['snapshot']['merged'])
        self.assertTrue(data['snapshot']['warnings'])

    def test_metadata_only_commit_not_implementation(self):
        expected = d.commits_for(self.root, REQ)
        (self.root / 'requirements/DELIVERY.md').write_text('归档')
        d.git(self.root, 'add', '.')
        d.git(self.root, 'commit', '-qm', 'Requirement: ' + REQ)
        self.assertEqual(expected, d.commits_for(self.root, REQ))

    def test_bad_id_and_unknown_commit_rejected(self):
        with self.assertRaises(ValueError):
            d.load(self.root, '../bad')
        with self.assertRaises(subprocess.CalledProcessError):
            d.resolve(self.root, 'not-found')

    def test_finish_updates_stale_card_and_reports_without_approving(self):
        card = self.root / 'requirements' / (REQ + '.md')
        card.write_text('# 需求\n- Git 状态：未提交\n- 产品验收：待确认\n')
        self.assertFalse(d.finish(self.root, [REQ], check=True))
        self.assertIn('未提交', card.read_text())
        self.assertTrue(d.finish(self.root, [REQ]))
        self.assertIn(d.resolve(self.root, 'HEAD'), card.read_text())
        self.assertIn('产品验收：待确认', card.read_text())
        self.assertTrue(d.finish(self.root, [REQ], check=True))
        (self.root / 'requirements/DELIVERY.md').unlink()
        self.assertFalse(d.finish(self.root, [REQ], check=True))
        self.assertTrue(d.finish(self.root, [REQ]))
        self.assertTrue(d.finish(self.root, [REQ], check=True))
        _, record = d.load(self.root, REQ)
        self.assertEqual('未登记', record['development']['state'])
        self.assertEqual('- Git 状态：未提交', record['card_history'][0]['previous_git_status'])
        self.commit('next', 'Requirement: ' + REQ)
        self.assertFalse(d.finish(self.root, [REQ], check=True))

    def v2_card(self, state='🔄 执行中', result='未验证', evidence='—', policy='自审'):
        card = self.root / 'requirements' / (REQ + '.md')
        card.write_text(f'''# 需求
{d.CARD_V2}
- 状态：{state}
- 验收方式：{policy}
- 验收依据：明确的低风险测试场景
- 下一步：{'无' if state == '✅ 执行完成' else '实施并验收'}
- 阻塞项：无

| 编号 | 条件 | 结果 | 证据 |
| --- | --- | --- | --- |
| AC-01 | 输入与期望 | {result} | {evidence} |
''')
        return card

    def test_v2_single_source_and_idempotent_finish(self):
        card = self.v2_card()
        original = card.read_bytes()
        self.assertTrue(d.finish(self.root, [REQ]))
        self.assertEqual(original, card.read_bytes())
        _, data = d.load(self.root, REQ)
        self.assertNotIn('development', data)
        self.assertEqual('🔄 执行中', data['snapshot']['development'])
        files = {p: p.read_bytes() for p in (self.root / 'requirements').rglob('*') if p.is_file()}
        self.assertTrue(d.finish(self.root, [REQ]))
        self.assertTrue(d.finish(self.root, [REQ], check=True))
        self.assertEqual(files, {p: p.read_bytes() for p in files})
        self.v2_card('✅ 执行完成', '通过', '实际测试证据')
        with self.assertRaisesRegex(ValueError, '基线缺失'):
            d.finish(self.root, [REQ], check=True)
        self.assertTrue(d.finish(self.root, [REQ], accept=True))
        _, data = d.load(self.root, REQ)
        self.assertEqual('✅ 执行完成', data['snapshot']['development'])

    def test_v2_inconsistent_completion_duplicate_and_team_confirmation_rejected(self):
        card = self.v2_card('✅ 执行完成')
        with self.assertRaisesRegex(ValueError, '尚未全部通过'):
            d.finish(self.root, [REQ])
        self.assertFalse((self.root / 'requirements/delivery').exists())
        card = self.v2_card('✅ 执行完成', '通过', '证据', '团队')
        card.write_text(card.read_text() + '\n- 团队确认：待确认\n')
        with self.assertRaisesRegex(ValueError, '团队实际确认'):
            d.finish(self.root, [REQ])
        card.write_text(card.read_text().replace('团队确认：待确认', '团队确认：用户；2026-09-11+08:00；build 1；通过'))
        self.assertTrue(d.finish(self.root, [REQ], accept=True))
        card.write_text(card.read_text() + '\n- 状态：🔄 执行中\n')
        with self.assertRaisesRegex(ValueError, '只能填写一处'):
            d.finish(self.root, [REQ])

    def test_v2_new_implementation_requires_revalidation(self):
        self.v2_card('✅ 执行完成', '通过', '第一版测试证据')
        d.finish(self.root, [REQ], accept=True)
        self.commit('changed', 'Requirement: ' + REQ)
        with self.assertRaisesRegex(ValueError, '尚未复核'):
            d.finish(self.root, [REQ])
        self.v2_card('✅ 执行完成', '通过', '第二版实际复测证据')
        self.assertTrue(d.finish(self.root, [REQ], accept=True))

    def test_all_ignores_legacy_and_v2_development_rejected(self):
        import sys
        legacy = self.root / 'requirements' / (REQ + '.md')
        before = legacy.read_bytes()
        run = subprocess.run([sys.executable, str(ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py'),
                              '--project', str(self.root), 'finish', '--all'], capture_output=True, text=True)
        self.assertEqual(0, run.returncode, run.stderr)
        self.assertEqual(before, legacy.read_bytes())
        self.assertFalse((self.root / 'requirements/delivery' / (REQ + '.json')).exists())
        self.v2_card()
        run = subprocess.run([sys.executable, str(ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py'),
                              '--project', str(self.root), '--requirement', REQ,
                              'development', '--state', '开发完成', '--evidence', '证据'], capture_output=True, text=True)
        self.assertNotEqual(0, run.returncode)
        self.assertIn('无需 development', run.stderr)

    def test_v2_local_finish_preserves_timestamped_remote_evidence(self):
        self.v2_card()
        _, data = d.load(self.root, REQ)
        d.refresh(self.root, data, True)
        previous = data['snapshot'].copy()
        d.refresh(self.root, data, False)
        self.assertEqual(previous['github_checked_at'], data['snapshot']['github_checked_at'])
        self.assertEqual(previous['release_status'], data['snapshot']['release_status'])
        self.commit('another', 'Requirement: ' + REQ)
        d.refresh(self.root, data, False)
        self.assertEqual('未核实', data['snapshot']['release_status'])
        self.assertNotIn('github_checked_at', data['snapshot'])


    def test_v2_finish_before_initial_commit_and_remote_check_idempotence(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            d.git(root, 'init', '-q')
            (root / 'requirements').mkdir()
            original = self.root
            try:
                self.root = root
                self.v2_card()
            finally:
                self.root = original
            self.assertTrue(d.finish(root, [REQ]))
            self.assertTrue(d.finish(root, [REQ], check=True))
            self.assertTrue(d.finish(root, [REQ], github=True))
            self.assertTrue(d.finish(root, [REQ], github=True, check=True))

    def test_v2_precommit_acceptance_is_reused_after_commit_without_repeat(self):
        self.v2_card('✅ 执行完成', '通过', '第一次证据')
        d.finish(self.root, [REQ], accept=True)
        (self.root / 'code.txt').write_text('fixed and tested')
        self.v2_card('✅ 执行完成', '通过', '修复后实际复测证据')
        d.finish(self.root, [REQ], accept=True)
        self.commit('fixed and tested', 'Requirement: ' + REQ)
        self.assertTrue(d.finish(self.root, [REQ]))
        self.assertTrue(d.finish(self.root, [REQ], check=True))


    def test_finish_cannot_overwrite_accepted_baseline_before_commit(self):
        (self.root / 'code.txt').write_text('pending accepted code')
        self.v2_card('✅ 执行完成', '通过', '初版实际证据')
        d.finish(self.root, [REQ], accept=True, inputs=['code.txt'])
        record = self.root / 'requirements/delivery' / (REQ + '.json')
        before = record.read_bytes()
        (self.root / 'code.txt').write_text('unverified change')
        for check in (False, True):
            with self.assertRaisesRegex(ValueError, '尚未复核'):
                d.finish(self.root, [REQ], check=check)
        with self.assertRaisesRegex(ValueError, '复核证据'):
            d.finish(self.root, [REQ], accept=True)
        self.assertEqual(before, record.read_bytes())
        self.commit('unverified change', 'Requirement: ' + REQ)
        with self.assertRaisesRegex(ValueError, '尚未复核'):
            d.finish(self.root, [REQ])
        self.v2_card('🔄 执行中')
        d.finish(self.root, [REQ])
        _, data = d.load(self.root, REQ)
        self.assertEqual(json.loads(before)['acceptance_baseline'], data['acceptance_baseline'])
        self.v2_card('✅ 执行完成', '通过', '新版本实际复测证据')
        d.finish(self.root, [REQ], accept=True)
        self.assertTrue(d.finish(self.root, [REQ], check=True))

    def test_acceptance_scope_ignores_unrelated_work_and_accept_is_idempotent(self):
        self.v2_card('✅ 执行完成', '通过', '真实证据')
        d.finish(self.root, [REQ], accept=True, inputs=['code.txt'])
        files = {p: p.read_bytes() for p in (self.root / 'requirements').rglob('*') if p.is_file()}
        (self.root / 'unrelated.txt').write_text('another task')
        d.finish(self.root, [REQ])
        d.finish(self.root, [REQ], accept=True)
        self.assertEqual(files, {p: p.read_bytes() for p in files})
        with self.assertRaises(ValueError):
            d.finish(self.root, [REQ], check=True, accept=True)
        with self.assertRaises(ValueError):
            d.finish(self.root, [REQ], accept=True, inputs=['../outside'])

    def test_finish_detects_failed_persistence_without_second_command(self):
        self.v2_card()
        with patch.object(d, 'save'):
            with self.assertRaises(OSError):
                d.finish(self.root, [REQ])

    def test_sealed_acceptance_survives_other_requirement_and_reopens(self):
        app = self.root / 'App'; app.mkdir()
        (app / 'A.swift').write_text('A')
        card = self.v2_card('✅ 执行完成', '通过', 'A实际验收')
        card.write_text(card.read_text().replace(d.CARD_V2, d.CARD_V3))
        d.finish(self.root, [REQ], accept=True, inputs=['App'])
        self.commit('one', 'A implementation\n\nRequirement: ' + REQ)
        d.finish(self.root, [REQ])
        _, sealed = d.load(self.root, REQ)
        self.assertIn('accepted_commit', sealed['acceptance_baseline'])
        (app / 'B.swift').write_text('unrelated B')
        self.commit('one', 'B implementation\n\nRequirement: REQ-20260911-888')
        d.finish(self.root, [REQ])
        _, after = d.load(self.root, REQ)
        self.assertEqual(sealed['acceptance_baseline'], after['acceptance_baseline'])
        self.assertTrue(d.finish(self.root, [REQ], check=True))
        self.v2_card('🔄 执行中')
        d.finish(self.root, [REQ])
        _, reopened = d.load(self.root, REQ)
        self.assertNotIn('accepted_commit', reopened['acceptance_baseline'])
        (app / 'A.swift').write_text('A changed')
        self.v2_card('✅ 执行完成', '通过', 'A实际验收')
        with self.assertRaisesRegex(ValueError, '尚未复核'):
            d.finish(self.root, [REQ])
        self.v2_card('✅ 执行完成', '通过', 'A变更实际复核')
        d.finish(self.root, [REQ], accept=True)

    def test_delayed_sealing_uses_accepted_commit_not_later_worktree(self):
        (self.root / 'code.txt').write_text('accepted A')
        self.v2_card('✅ 执行完成', '通过', 'A evidence')
        d.finish(self.root, [REQ], accept=True, inputs=['code.txt'])
        sha = self.commit('accepted A', 'Requirement: ' + REQ)
        self.commit('B changed same file', 'Requirement: REQ-20260911-888')
        d.finish(self.root, [REQ])
        _, data = d.load(self.root, REQ)
        self.assertEqual(sha, data['acceptance_baseline']['accepted_commit'])
        self.commit('unverified A followup', 'Requirement: ' + REQ)
        with self.assertRaisesRegex(ValueError, '尚未复核'):
            d.finish(self.root, [REQ])

    def test_dot_scope_ignores_metadata_and_ignored_outputs_in_both_tools(self):
        checks = d.checks_module()
        (self.root / '.gitignore').write_text('build/\n')
        config = {'inputs': ['.'], 'profiles': {}}
        before = d.implementation_snapshot(self.root, ['.'])
        tested = checks.source_snapshot(self.root, config)
        output = self.root / 'build'; output.mkdir(); (output / 'out').write_text('generated')
        (self.root / '.git/probe').write_text('metadata')
        self.assertEqual(before, d.implementation_snapshot(self.root, ['.']))
        self.assertEqual(tested, checks.source_snapshot(self.root, config))
        self.commit('one', 'normal commit')
        self.assertEqual(before, d.implementation_snapshot(self.root, ['.']))
        self.assertEqual(before, d.implementation_snapshot(self.root, ['.'], 'HEAD'))
        self.assertEqual(tested, checks.source_snapshot(self.root, config, staged=True))
        (self.root / 'real.txt').write_text('new source')
        self.assertNotEqual(before, d.implementation_snapshot(self.root, ['.']))
        self.assertNotEqual(tested, checks.source_snapshot(self.root, config))

    def test_accept_result_reuses_profile_scope_and_rejects_stale_result(self):
        import sys
        checks = d.checks_module()
        (self.root / '.agents').mkdir()
        config = {'schema_version': 1, 'inputs': ['irrelevant'],
                  'checks': {'unit': {'argv': [sys.executable, '-c', 'pass']}},
                  'profiles': {'change': ['unit']}, 'profile_inputs': {'change': ['code.txt']}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))
        checks.run(self.root, 'change')
        result = next((self.root / 'logs/project-checks').glob('*/result.json'))
        relative = str(result.relative_to(self.root))
        self.v2_card('✅ 执行完成', '通过', relative)
        d.finish(self.root, [REQ], accept=True, results=[relative])
        _, data = d.load(self.root, REQ)
        self.assertEqual(['.agents/project-checks.json', 'code.txt'], data['acceptance_baseline']['inputs'])
        self.assertEqual(relative, data['acceptance_baseline']['results'][0]['path'])
        with self.assertRaisesRegex(ValueError, '重复指定'):
            d.finish(self.root, [REQ], accept=True, inputs=['code.txt'], results=[relative])
        (self.root / 'code.txt').write_text('changed after test')
        with self.assertRaisesRegex(ValueError, '旧结果'):
            d.finish(self.root, [REQ], accept=True, results=[relative])
        self.v2_card('✅ 执行完成', '通过', '修改后人工复核证据')
        d.finish(self.root, [REQ], accept=True, inputs=['code.txt'])
        _, manual = d.load(self.root, REQ)
        self.assertEqual([], manual['acceptance_baseline']['results'])

    def test_documented_failure_value_is_valid(self):
        self.v2_card('🔄 执行中', '失败', '真实复现证据')
        self.assertEqual('🔄 执行中', d.card_state(self.root, REQ)['state'])
        self.assertNotIn('标通过、未通过', (ROOT / '.agents/skills/ios-team-flow/references/ACCEPTANCE.md').read_text())

    def test_history_delta_preserves_complete_snapshots(self):
        self.v2_card()
        d.finish(self.root, [REQ])
        _, before = d.load(self.root, REQ)
        self.v2_card('🧪 待验证')
        d.finish(self.root, [REQ])
        _, after = d.load(self.root, REQ)
        self.assertNotIn('snapshot', after['events'][-1])
        expanded = d.history_snapshots(after)
        self.assertEqual(before['snapshot'], expanded[0]['snapshot'])
        self.assertEqual(after['snapshot'], expanded[-1]['snapshot'])
        mixed = {'events': [{'snapshot': {'a': 1, 'b': 2}}, {'changes': {'a': 3}, 'removed': ['b']}]}
        self.assertEqual({'a': 3}, d.history_snapshots(mixed)[-1]['snapshot'])
        import sys
        output = subprocess.check_output([sys.executable, str(ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py'),
                    '--project', str(self.root), '--requirement', REQ, 'status'], text=True)
        self.assertEqual(after['snapshot'], json.loads(output))
