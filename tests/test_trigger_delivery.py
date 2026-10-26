"""按检查触发的验收、提交、历史交付与 CI 集成。"""
import json
import sys
import unittest
from unittest.mock import patch
import test_teamflow
import diagnostics

flow = test_teamflow.flow


class TriggerDeliveryTests(unittest.TestCase):
    setUp = test_teamflow.TeamFlowTests.setUp
    git = test_teamflow.TeamFlowTests.git
    baseline = test_teamflow.TeamFlowTests.baseline
    configure_checks = test_teamflow.TeamFlowTests.configure_checks
    create = test_teamflow.TeamFlowTests.create
    fill = test_teamflow.TeamFlowTests.fill
    card_path = test_teamflow.TeamFlowTests.card_path

    def configure(self):
        for name in ('a.py', 'b.py'):
            (self.root / name).write_text('# original\n')
        config = {'schema_version': 2, 'profiles': {'change': {
            'inputs': ['a.py', 'b.py'], 'checks': {
                name: {'argv': [sys.executable, '-c', 'pass'],
                       'covers': [name + '.py'], 'inputs': [name + '.py']}
                for name in ('a', 'b')}}}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))
        self.baseline()
        return self.git('rev-parse', 'HEAD')

    def test_partial_evidence_survives_without_logs_but_cannot_cover_new_code(self):
        base = self.configure()
        req = self.create(); self.fill(req)
        (self.root / 'a.py').write_text('# changed\n')
        flow.complete(self.root, req, profile='change')
        card = flow.parse_card(self.card_path(req))
        self.assertEqual(['a'], card['evidence']['checks'])
        import shutil
        shutil.rmtree(self.root / 'logs/project-checks')
        self.git('add', '-A')
        with patch.object(flow.checks_module(), 'run', side_effect=AssertionError('gate ran tests')):
            flow.git_check(self.root, req)
            flow.hook_check(self.root)
        self.git('commit', '-qm', 'deliver\n\nRequirement: ' + req)
        self.assertFalse(diagnostics.ci_check(self.root, base)['needs_action'])
        (self.root / 'b.py').write_text('# untested\n')
        self.git('add', 'b.py')
        with self.assertRaises(ValueError):
            flow.git_check(self.root, req)
        self.git('commit', '-qm', 'unverified b')
        self.assertTrue(diagnostics.ci_check(self.root, base)['needs_action'])

    def test_historical_evidence_rejects_later_edits_to_same_path(self):
        base = self.configure()
        req = self.create(); self.fill(req)
        (self.root / 'a.py').write_text('# verified\n')
        flow.complete(self.root, req, profile='change')
        self.git('add', '-A'); self.git('commit', '-qm', 'deliver\n\nRequirement: ' + req)
        self.assertFalse(diagnostics.ci_check(self.root, base)['needs_action'])
        for content in ('# unverified\n', None):
            with self.subTest(content=content):
                path = self.root / 'a.py'
                if content is None:
                    path.unlink()
                else:
                    path.write_text(content)
                self.git('add', '-A'); self.git('commit', '-qm', 'later unverified change')
                report = diagnostics.ci_check(self.root, base)
                self.assertTrue(report['needs_action'])
                item = next(i for i in report['checks'] if i['item'] == '未覆盖改动')
                self.assertIn('a.py', item['detail'])

    def test_changed_acceptance_needs_new_confirmation(self):
        self.configure()
        req = self.create(); self.fill(req, done=False)
        (self.root / 'a.py').write_text('# changed\n')
        flow.complete(self.root, req, profile='change', user_confirmed=['AC-01'])
        card = self.card_path(req)
        card.write_text(card.read_text().replace('错误时显示提示', '错误时显示新的视觉布局'))
        result = flow.complete(self.root, req, profile='change')
        self.assertEqual('进行中', result['state_key'])
        parsed = flow.parse_card(card)
        self.assertFalse(parsed['ac'][0]['done'])
        self.assertNotIn('AC-01', parsed['meta'].get('user_confirmed', []))
        result = flow.complete(self.root, req, user_confirmed=['AC-01'])
        self.assertEqual('完成', result['state_key'])

    def test_legacy_v5_summary_and_report_remain_verifiable(self):
        self.configure()
        req = self.create(); self.fill(req)
        (self.root / 'a.py').write_text('# changed\n')
        result = flow.complete(self.root, req, profile='change')
        checks = flow.checks_module()
        config = checks.load_config(self.root)
        source = checks.source_snapshot(self.root, config, 'change', requirement=req,
                                        checks=['a'], algorithm='sha256-files-v5')
        proof = dict(result['evidence'], fingerprint='sha256:' + source['fingerprint'])
        proof.pop('algorithm')
        checks.verify_summary(self.root, req, proof)
        target = self.root / proof['log']
        report = json.loads(target.read_text())
        report.update(source=source, end_fingerprint=source['fingerprint'])
        target.write_text(json.dumps(report))
        checks.verify(self.root, proof['log'])
        self.git('add', '-A')
        checks.verify_summary(self.root, req, proof, staged=True)

    def test_changed_ac_does_not_clear_unmodified_confirmation(self):
        self.configure()
        req = self.create(); self.fill(req, done=False)
        card = self.card_path(req)
        card.write_text(card.read_text().replace('## 决策与异常',
            '- [ ] AC-02：其他条件\n\n## 决策与异常'))
        (self.root / 'a.py').write_text('# changed\n')
        flow.complete(self.root, req, profile='change', user_confirmed=['AC-01', 'AC-02'])
        card.write_text(card.read_text().replace('错误时显示提示', '错误时显示新提示'))
        flow.complete(self.root, req, profile='change')
        parsed = flow.parse_card(card)
        self.assertEqual([False, True], [item['done'] for item in parsed['ac']])
        self.assertEqual(['AC-02'], parsed['meta']['user_confirmed'])

    def test_complete_reuses_valid_daily_result_without_running_again(self):
        self.configure()
        req = self.create(); self.fill(req, done=False)
        (self.root / 'a.py').write_text('# changed\n')
        checks = flow.checks_module()
        target, passed = checks.run(self.root, 'change', req)
        self.assertTrue(passed)
        self.assertIsNone(flow.parse_card(self.card_path(req))['evidence'])
        with patch.object(checks, 'run', side_effect=AssertionError('重复运行检查')):
            result = flow.complete(self.root, req, profile='change', confirm_ac=['AC-01'])
        self.assertEqual('完成', result['state_key'])
        self.assertIn('未运行测试', result['verification'])
        self.assertEqual(['a'], result['evidence']['checks'])
        self.git('add', '-A')
        flow.git_check(self.root, req)
        (self.root / 'a.py').write_text('# later change\n')
        with self.assertRaises(ValueError):
            flow.git_check(self.root, req)

    def test_complete_runs_missing_checks_after_daily_result(self):
        self.configure()
        req = self.create(); self.fill(req)
        (self.root / 'a.py').write_text('# changed\n')
        checks = flow.checks_module()
        target, passed = checks.run(self.root, 'change', req)
        self.assertTrue(passed)
        (self.root / 'b.py').write_text('# newly affected\n')
        with patch.object(checks, 'run', wraps=checks.run) as runner:
            result = flow.complete(self.root, req, profile='change')
        self.assertEqual('完成', result['state_key'])
        runner.assert_called_once()
        self.assertEqual(['a', 'b'], result['evidence']['checks'])

    def test_complete_does_not_reuse_stale_or_failed_daily_result(self):
        self.configure()
        req = self.create(); self.fill(req)
        (self.root / 'a.py').write_text('# initial change\n')
        checks = flow.checks_module()
        self.assertTrue(checks.run(self.root, 'change', req)[1])
        (self.root / 'a.py').write_text('# updated after check\n')
        with patch.object(checks, 'run', wraps=checks.run) as runner:
            flow.complete(self.root, req, profile='change')
        runner.assert_called_once()

        other = self.create(); self.fill(other)
        (self.root / 'a.py').write_text('# another task\n')
        with patch.object(checks, 'run', wraps=checks.run) as runner:
            flow.complete(self.root, other, profile='change')
        runner.assert_called_once()

    def test_failed_latest_daily_result_cannot_reuse_older_pass(self):
        self.configure()
        req = self.create(); self.fill(req)
        (self.root / 'a.py').write_text('# changed\n')
        checks = flow.checks_module()
        self.assertTrue(checks.run(self.root, 'change', req)[1])
        config_path = self.root / '.agents/project-checks.json'
        config = json.loads(config_path.read_text())
        config['profiles']['change']['checks']['a']['argv'] = [sys.executable, '-c', 'raise SystemExit(1)']
        config_path.write_text(json.dumps(config))
        self.assertFalse(checks.run(self.root, 'change', req)[1])
        with self.assertRaises(ValueError):
            flow.complete(self.root, req, profile='change')
        self.assertIsNone(flow.parse_card(self.card_path(req))['evidence'])

    def test_complete_reruns_check_with_cache_disabled(self):
        self.configure()
        req = self.create(); self.fill(req)
        config_path = self.root / '.agents/project-checks.json'
        config = json.loads(config_path.read_text())
        config['profiles']['change']['checks']['a']['cache'] = False
        config_path.write_text(json.dumps(config))
        (self.root / 'a.py').write_text('# changed\n')
        checks = flow.checks_module()
        self.assertTrue(checks.run(self.root, 'change', req)[1])
        with patch.object(checks, 'run', wraps=checks.run) as runner:
            flow.complete(self.root, req, profile='change')
        runner.assert_called_once()

    def test_needless_check_does_not_complete_card(self):
        self.configure()
        req = self.create(); self.fill(req, done=False)
        before = self.card_path(req).read_bytes()
        with self.assertRaises(ValueError):
            flow.complete(self.root, req, profile='change', confirm_ac=['AC-01'])
        self.assertEqual(before, self.card_path(req).read_bytes())

    def test_explicit_rerun_bypasses_incremental_and_runs_all_checks(self):
        self.configure()
        p = self.root / '.agents/project-checks.json'
        config = json.loads(p.read_text())
        config['profiles']['change']['incremental'] = True
        p.write_text(json.dumps(config))
        self.baseline()
        req = self.create(); self.fill(req)
        (self.root / 'a.py').write_text('# changed\n')
        flow.complete(self.root, req, profile='change')
        flow.complete(self.root, req, profile='change', rerun=True)
        proof = flow.parse_card(self.card_path(req))['evidence']
        report = json.loads((self.root / proof['log']).read_text())
        self.assertEqual(['a', 'b'], proof['checks'])
        self.assertFalse(any(item.get('reused') for item in report['results']))

    def test_requirement_display_changes_reuse_existing_evidence(self):
        self.configure()
        req = self.create(); self.fill(req, done=False)
        (self.root / 'a.py').write_text('# changed\n')
        flow.complete(self.root, req, profile='change')
        p = self.card_path(req)
        p.write_text(p.read_text() + '\n## 决策与异常\n仅追加记录\n')
        with patch.object(flow.checks_module(), 'run', side_effect=AssertionError('unnecessary run')):
            result = flow.complete(self.root, req, confirm_ac=['AC-01'])
        self.assertEqual('完成', result['state_key'])

    def test_semantic_change_revalidates_previous_checks_without_code_change(self):
        self.configure()
        req = self.create(); self.fill(req)
        (self.root / 'a.py').write_text('# changed\n')
        flow.complete(self.root, req, profile='change')
        self.baseline()
        p = self.card_path(req)
        p.write_text(p.read_text().replace('实现登录错误提示', '实现新的登录错误提示'))
        result = flow.complete(self.root, req)
        self.assertEqual(['a'], result['evidence']['checks'])
        report = json.loads((self.root / result['evidence']['log']).read_text())
        self.assertFalse(any(item.get('reused') for item in report['results']))

    def test_historical_partial_coverage_uses_delivered_configuration(self):
        base = self.configure()
        req = self.create(); self.fill(req)
        (self.root / 'a.py').write_text('# changed\n')
        flow.complete(self.root, req, profile='change')
        self.git('add', '-A'); self.git('commit', '-qm', 'deliver')
        p = self.root / '.agents/project-checks.json'
        config = json.loads(p.read_text())
        config['profiles']['change']['checks']['a']['covers'] = ['a.py', 'b.py']
        config['profiles']['change']['checks']['a']['inputs'] = ['a.py', 'b.py']
        p.write_text(json.dumps(config))
        (self.root / 'b.py').write_text('# changed without evidence\n')
        self.git('add', '-A'); self.git('commit', '-qm', 'expand current covers')
        report = diagnostics.ci_check(self.root, base)
        self.assertTrue(report['needs_action'])
        uncovered = next(item for item in report['checks'] if item['item'] == '未覆盖改动')
        self.assertIn('b.py', uncovered['detail'])
