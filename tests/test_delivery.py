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
REQ = 'REQ-20260911-120000999Z-abcdef01'


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
        self.assertFalse((self.root / 'requirements/DELIVERY.md').exists())
        subprocess.run(['python3', str(ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py'),
                        '--project', str(self.root), '--requirement', REQ, 'refresh'],
                       check=True, capture_output=True)
        self.assertFalse((self.root / 'requirements/DELIVERY.md').exists())
        overview = subprocess.check_output(['python3', str(ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py'),
                                            '--project', str(self.root), 'list', '--delivery'], text=True)
        self.assertIn(REQ, overview)

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
        path, _ = d.load(self.root, REQ)
        self.assertFalse(path.exists())
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

    def test_batch_finish_does_not_write_overview_and_preserves_readback_checks(self):
        card = self.v2_card()
        second = 'REQ-20260911-120001999Z-abcdef02'
        (self.root / 'requirements' / (second + '.md')).write_text(card.read_text())
        with patch.object(d, 'overview', wraps=d.overview) as render:
            self.assertTrue(d.finish(self.root, [REQ, second]))
            self.assertEqual(0, render.call_count)
        self.assertFalse((self.root / 'requirements/DELIVERY.md').exists())
        for check in (False, True):
            with patch.object(d, 'overview', wraps=d.overview) as render:
                self.assertTrue(d.finish(self.root, [REQ, second], check=check))
                self.assertEqual(0, render.call_count)
        original_save = d.save
        def corrupt_after_save(root, path, data, action):
            original_save(root, path, data, action)
            stored = json.loads(path.read_text())
            stored['acceptance_baseline']['implementation_fingerprint'] = '被改写'
            path.write_text(json.dumps(stored))
        card.write_text(card.read_text().replace('🔄 执行中', '✅ 执行完成')
                        .replace('实施并验收', '无').replace('未验证 | —', '通过 | 实际证据'))
        with patch.object(d, 'save', side_effect=corrupt_after_save):
            with self.assertRaisesRegex(ValueError, '写后验收基线不一致'):
                d.finish(self.root, [REQ], accept=True)

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
        self.assertEqual({**json.loads(before)['acceptance_baseline'], 'reopened': True},
                         data['acceptance_baseline'])
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
        self.v2_card('✅ 执行完成', '通过', '实际证据')
        with patch.object(d, 'save'):
            with self.assertRaises(OSError):
                d.finish(self.root, [REQ], accept=True)

    def test_sealed_acceptance_survives_other_requirement_and_reopens(self):
        app = self.root / 'App'; app.mkdir()
        (app / 'A.swift').write_text('A')
        card = self.v2_card('✅ 执行完成', '通过', 'A实际验收')
        card.write_text(card.read_text().replace(d.CARD_V2, d.CARD_V3))
        d.finish(self.root, [REQ], accept=True, inputs=['App'])
        self.commit('one', 'A implementation\n\nRequirement: ' + REQ)
        d.finish(self.root, [REQ])
        _, sealed = d.load(self.root, REQ)
        self.assertNotIn('accepted_commit', sealed['acceptance_baseline'])
        d.refresh(self.root, sealed)
        self.assertIn('accepted_commit', sealed['acceptance_baseline'])
        (app / 'B.swift').write_text('unrelated B')
        self.commit('one', 'B implementation\n\nRequirement: REQ-20260911-120000888Z-abcdef01')
        d.finish(self.root, [REQ])
        _, after = d.load(self.root, REQ)
        self.assertEqual(d.durable_baseline(sealed['acceptance_baseline']), after['acceptance_baseline'])
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
        self.commit('B changed same file', 'Requirement: REQ-20260911-120000888Z-abcdef01')
        d.finish(self.root, [REQ])
        _, data = d.load(self.root, REQ)
        d.refresh(self.root, data)
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

    def test_history_delta_preserves_complete_snapshots(self):
        self.v2_card('✅ 执行完成', '通过', '第一次证据')
        d.finish(self.root, [REQ], accept=True)
        _, before = d.load(self.root, REQ)
        self.v2_card('✅ 执行完成', '通过', '第二次证据')
        d.finish(self.root, [REQ], accept=True)
        _, after = d.load(self.root, REQ)
        self.assertNotIn('snapshot', after['events'][-1])
        expanded = d.history_snapshots(after)
        self.assertEqual(before['snapshot'], expanded[0]['snapshot'])
        self.assertEqual(after['snapshot'], expanded[-1]['snapshot'])
        mixed = {'events': [{'snapshot': {'a': 1, 'b': 2}}, {'changes': {'a': 3}, 'removed': ['b']}]}
        self.assertEqual({'a': 3}, d.history_snapshots(mixed)[-1]['snapshot'])

    def test_status_full_snapshot_and_history_without_writes(self):
        import sys
        self.v2_card('✅ 执行完成', '通过', '实际证据')
        d.finish(self.root, [REQ], accept=True)
        path, data = d.load(self.root, REQ)
        before = path.read_bytes()
        command = [sys.executable, str(ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py'),
                   '--project', str(self.root), '--requirement', REQ, 'status']
        full = json.loads(subprocess.check_output(command, text=True))
        self.assertEqual(data['snapshot']['development'], full['development'])
        self.assertIn('card', full)
        self.assertEqual(data['snapshot']['warnings'], full['warnings'])
        history = json.loads(subprocess.check_output(command + ['--history'], text=True))
        self.assertEqual(d.history_snapshots(data), history['events'])
        self.assertEqual(before, path.read_bytes())

    def test_status_unsynced_does_not_claim_completion_or_create_record(self):
        import sys
        self.v2_card()
        path, _ = d.load(self.root, REQ)
        command = [sys.executable, str(ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py'),
                   '--project', str(self.root), '--requirement', REQ, 'status']
        snapshot = json.loads(subprocess.check_output(command, text=True))
        self.assertEqual('🔄 执行中', snapshot['development'])
        self.assertTrue(snapshot['committed'])
        self.assertFalse(path.exists())

    def test_unknown_template_rejected_without_writing(self):
        before = {p: p.read_bytes() for p in (self.root / 'requirements').rglob('*') if p.is_file()}
        for name in ('../requirement', 'missing', ''):
            with self.assertRaises(ValueError):
                d.create(self.root, '缺陷', name)
        self.assertEqual(before, {p: p.read_bytes() for p in (self.root / 'requirements').rglob('*') if p.is_file()})

    def test_bug_list_reads_current_cards_without_manual_index(self):
        import sys
        bug = d.create(self.root, '缺陷初始标题', 'bug-fix')
        normal = d.create(self.root, '普通需求')
        command = [sys.executable, str(ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py'),
                   '--project', str(self.root), 'list', '--type', 'bug-fix']
        rows = json.loads(subprocess.check_output(command + ['--json'], text=True))
        self.assertEqual([bug.stem], [row['requirement'] for row in rows])
        self.assertNotIn(normal.stem, subprocess.check_output(command, text=True))
        bug.write_text(bug.read_text().replace('缺陷初始标题', '改名后的缺陷')
                       .replace('⬜ 未执行', '🔄 执行中'))
        second = d.create(self.root, '另一缺陷', 'bug-fix')
        before = {p: p.read_bytes() for p in (self.root / 'requirements').rglob('*') if p.is_file()}
        output = subprocess.check_output(command, text=True)
        self.assertIn('改名后的缺陷', output)
        self.assertIn('🔄 执行中', output)
        self.assertIn(f'[{bug.stem}](requirements/{bug.name})', output)
        rows = json.loads(subprocess.check_output(command + ['--json', '--reverse'], text=True))
        self.assertEqual([second.stem, bug.stem], [row['requirement'] for row in rows])
        self.assertEqual([2, 1], [row['number'] for row in rows])
        self.assertEqual(before, {p: p.read_bytes() for p in before})
        self.assertFalse((self.root / 'requirements/BUGFIX-HISTORY.md').exists())
        self.assertFalse((self.root / 'requirements/delivery').exists())

    def test_lightweight_card_is_listed_without_delivery_record(self):
        import sys
        card = d.create(self.root, '更新说明', 'lightweight')
        self.assertIn(d.LIGHTWEIGHT_V1, card.read_text())
        command = [sys.executable, str(ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py'),
                   '--project', str(self.root), 'list', '--type', 'lightweight', '--json']
        rows = json.loads(subprocess.check_output(command, text=True))
        self.assertEqual([card.stem], [row['requirement'] for row in rows])
        self.assertFalse((self.root / 'requirements/delivery' / (card.stem + '.json')).exists())

    def test_timestamp_ids_sort_and_retry_without_overwrite(self):
        from datetime import datetime, timezone
        from types import SimpleNamespace
        now = datetime(2026, 9, 12, 10, 30, 15, 123000, tzinfo=timezone.utc)
        with patch.object(d, 'datetime') as clock, patch.object(d.uuid, 'uuid4') as random:
            clock.now.return_value = now
            random.side_effect = [SimpleNamespace(hex='a1b2c3d4' + '0' * 24),
                                  SimpleNamespace(hex='a1b2c3d4' + '0' * 24),
                                  SimpleNamespace(hex='b1b2c3d4' + '0' * 24)]
            first = d.create(self.root, '先创建')
            before = first.read_bytes()
            second = d.create(self.root, '同毫秒')
        self.assertEqual('REQ-20260912-103015123Z-a1b2c3d4', first.stem)
        self.assertLess(first.name, second.name)
        self.assertEqual(before, first.read_bytes())
        self.assertEqual(now, d.created_time(first.stem))
        self.assertIn(first.stem, first.read_text())
        self.assertNotIn('REQ-YYYYMMDD', first.read_text())

    def test_list_and_overview_order_titles_unfinished_and_read_only(self):
        import sys
        (self.root / 'requirements' / (REQ + '.md')).unlink()
        ids = ['REQ-20260912-000000002Z-bbbbbbbb', 'REQ-20260911-235959999Z-aaaaaaaa',
               'REQ-20260912-000000001Z-cccccccc']
        for i, identifier in enumerate(ids):
            (self.root / 'requirements' / (identifier + '.md')).write_text(
                '# ' + identifier + '：标题|' + str(i) + '\n- 状态：⬜ 未执行\n')
        before = {str(p): p.read_bytes() for p in (self.root / 'requirements').rglob('*') if p.is_file()}
        rows = d.requirement_rows(self.root)
        self.assertEqual(sorted(ids), [r['requirement'] for r in rows])
        self.assertEqual([1, 2, 3], [r['number'] for r in rows])
        self.assertEqual(list(reversed(rows)), d.requirement_rows(self.root, True))
        overview = d.overview(self.root)
        self.assertIn('标题&#124;', overview)
        self.assertLess(overview.index(ids[1]), overview.index(ids[2]))
        command = [sys.executable, str(ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py'),
                   '--project', str(self.root), 'list']
        output = subprocess.check_output(command + ['--reverse', '--json'], text=True)
        self.assertEqual(list(reversed(rows)), json.loads(output))
        self.assertIn('创建时间（UTC）', subprocess.check_output(command, text=True))
        self.assertEqual(before, {str(p): p.read_bytes() for p in (self.root / 'requirements').rglob('*') if p.is_file()})

    def test_old_identifiers_and_invalid_timestamp_rejected(self):
        for identifier in ('REQ-20260911-001', 'REQ-20260911-' + 'a' * 32,
                           'REQ-20260230-120000000Z-aaaaaaaa', 'REQ-20260912-250000000Z-aaaaaaaa'):
            with self.assertRaises(ValueError):
                d.load(self.root, identifier)
        legacy = self.root / 'requirements/REQ-20260911-001.md'
        legacy.write_text('# 历史原件')
        self.assertNotIn(legacy.stem, d.list_requirements(self.root))
        self.assertEqual('# 历史原件', legacy.read_text())


    def test_list_isolates_bad_cards_and_preserves_json_and_files(self):
        import sys
        bad_date = self.root / 'requirements/REQ-20260230-120000000Z-aaaaaaaa.md'
        bad_date.write_text('# invalid date')
        bad_text = self.root / 'requirements/REQ-20260912-120000000Z-bbbbbbbb.md'
        bad_text.write_bytes(b'\xff')
        link = self.root / 'requirements/REQ-20260912-120000001Z-cccccccc.md'
        link.symlink_to(self.root / 'code.txt')
        before = {p.name: p.read_bytes() for p in (self.root / 'requirements').iterdir()}
        command = [sys.executable, str(ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py'),
                   '--project', str(self.root), 'list']
        for args in (['--json'], ['--reverse', '--json'], []):
            result = subprocess.run(command + args, capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            if '--json' in args:
                rows = json.loads(result.stdout)
                self.assertEqual([REQ], [row['requirement'] for row in rows])
                self.assertEqual([1], [row['number'] for row in rows])
            else:
                self.assertIn(REQ, result.stdout)
            for bad in (bad_date, bad_text, link):
                self.assertIn(bad.name, result.stderr)
                self.assertNotIn(bad.name, result.stdout)
        overview = d.overview(self.root)
        self.assertIn(REQ, overview)
        self.assertIn('以下异常需求卡未纳入概览', overview)
        for bad in (bad_date, bad_text, link):
            self.assertIn(bad.name, overview)
        self.assertEqual(before, {p.name: p.read_bytes() for p in (self.root / 'requirements').iterdir()})
        with self.assertRaises(ValueError):
            d.load(self.root, bad_date.stem)
        d.finish(self.root, [REQ])
        self.assertIn(bad_date.name, d.overview(self.root))
        (self.root / 'requirements' / (REQ + '.md')).unlink()
        result = subprocess.run(command + ['--json'], capture_output=True, text=True)
        self.assertEqual(0, result.returncode)
        self.assertEqual([], json.loads(result.stdout))
        self.assertIn(bad_date.name, result.stderr)
