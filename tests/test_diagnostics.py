import unittest
import test_teamflow
import diagnostics

flow = test_teamflow.flow


class DiagnosticsTests(unittest.TestCase):
    setUp = test_teamflow.TeamFlowTests.setUp
    git = test_teamflow.TeamFlowTests.git
    configure_checks = test_teamflow.TeamFlowTests.configure_checks
    create = test_teamflow.TeamFlowTests.create
    fill = test_teamflow.TeamFlowTests.fill
    card_path = test_teamflow.TeamFlowTests.card_path
    saved = test_teamflow.TeamFlowTests.saved

    def test_suggestion_reports_uncovered_without_running(self):
        (self.root / 'other.swift').write_text('let a = 1')
        report = flow.checks_module().suggest(self.root)
        self.assertIn('other.swift', report['uncovered_files'])
        self.assertIn('source.txt', report['profiles'][0]['covered_files'])
        self.assertFalse((self.root / 'logs').exists())

    def test_source_repository_needs_no_managed_entry(self):
        import setup_project
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        entry = next(item for item in setup_project.diagnose(root)['checks'] if item['item'] == 'Skill 与入口')
        self.assertEqual('就绪', entry['status'])
        self.assertIn('源码仓库', entry['detail'])

    def test_in_progress_and_waiting_cards_are_not_action_items(self):
        req = self.create(); self.fill(req, done=False)
        report = diagnostics.doctor(self.root)
        item = next(entry for entry in report['checks'] if entry['item'] == req)
        self.assertEqual('进行中', item['status'])
        self.assertIn('统一验收', item['detail']['next_step'])
        self.assertIn('[进行中] ' + req, diagnostics.format_report(report))
        flow.complete(self.root, req, profile='change', wait_user=True)
        status = flow.status(self.root, req)
        self.assertIn('--user-confirmed', status['next_step'])
        self.assertIn('--user-confirmed', flow.render('status', status))
        self.assertIn('--user-confirmed', flow.render('complete', flow.complete(self.root, req, wait_user=True)))

    def test_missing_check_config_is_reported_once(self):
        (self.root / '.agents/project-checks.json').unlink()
        items = [entry['item'] for entry in diagnostics.doctor(self.root)['checks']]
        self.assertIn('项目验证', items)
        self.assertNotIn('验证配置及输入', items)

    def test_status_is_read_only_and_checks_stale_evidence(self):
        req = self.create(); card = self.fill(req)
        flow.complete(self.root, req, profile='change')
        original = card.read_bytes()
        report = flow.status(self.root, req)
        self.assertEqual(('有效', []), (report['evidence_status'], report['problems']))
        self.assertIn('（有效）', flow.render('status', report))
        (self.root / 'source.txt').write_text('changed')
        report = flow.status(self.root, req)
        self.assertEqual('缺失或失效', report['evidence_status'])
        brief = flow.render('status', report)
        self.assertIn('问题：测试后源码或配置已变化', brief)
        self.assertIn('下一步：', brief)
        self.assertEqual(original, card.read_bytes())
        flow.set_state(self.root, req, '阻塞', '等待用户', '暂停')
        self.assertIn('不得自动继续', flow.status(self.root, req)['next_step'])

    def doctor_status(self, req):
        report = diagnostics.doctor(self.root)
        return next(i for i in report['checks'] if i['item'] == req)['status'], report

    def test_finished_evidence_is_checked_against_delivery_commit(self):
        req = self.create(); self.fill(req)
        flow.complete(self.root, req, profile='change')
        # 完成后尚未提交即修改输入：交付内容已偏离验证结果，必须处理。
        (self.root / 'source.txt').write_text('changed')
        self.assertEqual('需处理', self.doctor_status(req)[0])
        (self.root / 'source.txt').write_text('source')
        self.git('add', '-A'); self.git('commit', '-qm', 'deliver')
        delivered = self.git('rev-parse', 'HEAD')
        # 交付后代码继续演进，不影响已交付结论；完成与提交检查仍按当前内容校验。
        (self.root / 'source.txt').write_text('evolved')
        self.git('commit', '-qam', 'evolve')
        status, report = self.doctor_status(req)
        self.assertEqual('就绪', status)
        self.assertNotIn('[历史]', diagnostics.format_report(report))
        summary = flow.status(self.root, req)
        self.assertEqual(('交付时有效（提交 ' + delivered[:7] + '）', []),
                         (summary['evidence_status'], summary['problems']))
        with self.assertRaisesRegex(ValueError, '已变化'):
            self.saved(req)

    def test_committed_evidence_not_matching_delivery_is_history(self):
        req = self.create(); self.fill(req)
        flow.complete(self.root, req, profile='change')
        (self.root / 'source.txt').write_text('changed before commit')
        self.git('add', '-A'); self.git('commit', '-qm', 'deliver')
        status, report = self.doctor_status(req)
        self.assertEqual('历史', status)
        self.assertFalse(any(i['status'] == '需处理' and i['item'].startswith('REQ-') for i in report['checks']))
        self.assertIn('[历史] 已交付需求证据无法对应交付提交 1 张，仅提示（--json 查看）', diagnostics.format_report(report))
        self.assertNotIn(req, diagnostics.format_report(report))
        self.assertIn('无需重开', flow.status(self.root, req)['next_step'])

    def test_doctor_reports_placeholders_bad_config_and_symlink(self):
        req = self.create()
        (self.root / '.agents/project-checks.json').write_text('{}')
        target = self.root / 'requirements/REQ-0002.md'
        target.symlink_to(self.root / 'requirements' / (req + '.md'))
        before = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*')
                  if p.is_file() and '.git' not in p.parts}
        report = diagnostics.doctor(self.root)
        self.assertTrue(report['needs_action'])
        self.assertTrue(any('占位' in str(item['detail']) for item in report['checks']))
        self.assertTrue(any('符号链接' in str(item['detail']) for item in report['checks']))
        after = {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*')
                 if p.is_file() and '.git' not in p.parts}
        self.assertEqual(before, after)


if __name__ == '__main__':
    unittest.main()


class DeliveryTests(unittest.TestCase):
    setUp = test_teamflow.TeamFlowTests.setUp
    git = test_teamflow.TeamFlowTests.git
    configure_checks = test_teamflow.TeamFlowTests.configure_checks
    create = test_teamflow.TeamFlowTests.create
    fill = test_teamflow.TeamFlowTests.fill
    card_path = test_teamflow.TeamFlowTests.card_path

    def ci_status(self, base, req):
        report = diagnostics.ci_check(self.root, base)
        return next((i['status'] for i in report['checks'] if i['item'] == req), None), report

    def test_pr_body_comes_from_card(self):
        req = self.create('登录提示'); self.fill(req, done=False)
        body = diagnostics.pr_body(self.root, req)
        self.assertEqual('[阶段] 登录提示', body['title'])
        self.assertIn('- [ ] AC-01：错误时显示提示', body['body'])
        self.assertIn('- 未验证', body['body'])
        self.assertIn('未确认：AC-01', body['body'])
        self.assertTrue(body['body'].endswith('Requirement: ' + req))
        flow.complete(self.root, req, profile='change', confirm_ac=['AC-01'])
        body = diagnostics.pr_body(self.root, req)['body']
        self.assertIn('change：通过，证据有效', body)
        self.assertNotIn('未确认', body)
        self.assertEqual('登录提示', diagnostics.pr_body(self.root, req)['title'])

    def test_ci_check_requires_delivered_evidence_for_changed_cards(self):
        self.git('add', '-A'); self.git('commit', '-qm', 'base')
        base = self.git('rev-parse', 'HEAD')
        draft = self.create('进行中')
        self.git('add', '-A'); self.git('commit', '-qm', 'draft')
        self.assertEqual('提示', self.ci_status(base, draft)[0])
        req = self.create(); self.fill(req)
        flow.complete(self.root, req, profile='change')
        self.git('add', '-A'); self.git('commit', '-qm', 'deliver')
        status, report = self.ci_status(base, req)
        self.assertEqual('就绪', status)
        self.assertFalse(report['needs_action'])
        # 验证后又改了输入并一同提交：交付内容与证据不符，CI 必须拦下。
        stale = self.create('失效'); self.fill(stale)
        flow.complete(self.root, stale, profile='change')
        (self.root / 'source.txt').write_text('changed after verify')
        self.git('add', '-A'); self.git('commit', '-qm', 'stale')
        status, report = self.ci_status(base, stale)
        self.assertEqual('需处理', status)
        self.assertTrue(report['needs_action'])
        # 已交付的卡不受后续提交影响。
        self.assertEqual('就绪', self.ci_status(base, req)[0])
        with self.assertRaisesRegex(ValueError, 'fetch-depth'):
            diagnostics.ci_check(self.root, 'missing-ref')


class ModuleHintTests(unittest.TestCase):
    setUp = test_teamflow.TeamFlowTests.setUp
    git = test_teamflow.TeamFlowTests.git
    configure_checks = test_teamflow.TeamFlowTests.configure_checks

    def hint(self):
        return next((i for i in diagnostics.doctor(self.root)['checks'] if i['item'] == '模块索引'), None)

    def test_large_project_without_index_gets_hint(self):
        self.git('add', '-A')
        self.assertIsNone(self.hint())
        from unittest.mock import patch
        with patch.object(diagnostics, 'LARGE_PROJECT_FILES', 2):
            item = self.hint()
        self.assertEqual('提示', item['status'])
        self.assertIn('MODULE-CONTEXT', item['detail'])


class LegacyLayoutTests(unittest.TestCase):
    """升级后旧形态验证配置的识别：日常 profile 含 Release 构建需处理，未声明 check covers 只提示。"""
    setUp = test_teamflow.TeamFlowTests.setUp
    git = test_teamflow.TeamFlowTests.git
    configure_checks = test_teamflow.TeamFlowTests.configure_checks

    def layout(self, profiles):
        import json
        (self.root / '.agents/project-checks.json').write_text(json.dumps({'schema_version': 2, 'profiles': profiles}))
        report = diagnostics.doctor(self.root)
        return next((i for i in report['checks'] if i['item'] == '验证配置形态'), None), report

    def test_release_build_in_daily_profile_needs_migration(self):
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts/check_app.py').write_text(
            'xcodebuild("-configuration", "Release", "-destination", "generic/platform=iOS Simulator", "build")\n')
        release = {'argv': ['xcodebuild', '-configuration', 'Release', 'build']}
        item, report = self.layout({
            'change': {'inputs': ['source.txt', 'scripts'], 'checks': {'app': {'argv': ['python3', 'scripts/check_app.py']}}},
            'cloud-release': {'inputs': ['source.txt'], 'manual': True, 'checks': {'release-build': release}}})
        self.assertEqual('需处理', item['status'])
        self.assertTrue(report['needs_action'])
        text = diagnostics.format_report(report)
        self.assertIn('change 的检查 app 含 Release 构建', text)
        self.assertIn('cloud-release', text)
        self.assertNotIn('cloud-release 的检查', text)

    def test_syntax_check_of_release_script_is_not_a_release_build(self):
        (self.root / 'scripts').mkdir()
        (self.root / 'scripts/verify_release.py').write_text("run(['xcodebuild', '-configuration', 'Release'])\n")
        item, _ = self.layout({'change': {'inputs': ['source.txt', 'scripts'], 'checks': {
            'release-script': {'argv': ['python3', '-m', 'py_compile', 'scripts/verify_release.py'],
                               'covers': ['scripts/verify_release.py']},
            'debug': {'argv': ['python3', '-c', 'pass'], 'covers': ['source.txt']}}}})
        self.assertIsNone(item)

    def test_missing_check_covers_is_only_a_hint(self):
        item, report = self.layout({'change': {'inputs': ['source.txt'], 'checks': {
            'all': {'argv': ['python3', '-c', 'pass']}}}})
        self.assertEqual('提示', item['status'])
        self.assertIn('未声明 check covers', diagnostics.format_report(report))
        self.assertFalse(any(i['status'] == '需处理' for i in report['checks'] if i['item'] == '验证配置形态'))

    def record(self, profile, name, seconds, status='通过', reused=False):
        import json
        run = self.root / 'logs/project-checks' / f'run-{profile}-{name}-{seconds}'
        run.mkdir(parents=True)
        (run / 'result.json').write_text(json.dumps({'profile': profile, 'started_at': f'2026-10-25T00:00:{seconds % 60:02d}Z',
            'results': [{'name': name, 'status': status, 'duration_seconds': seconds, 'reused': reused}]}))

    def test_long_daily_check_is_a_hint(self):
        profiles = {
            'change': {'inputs': ['source.txt'], 'checks': {
                'unit': {'argv': ['true'], 'covers': ['source.txt']},
                'lint': {'argv': ['true'], 'covers': ['source.txt']}}},
            'full': {'inputs': ['source.txt'], 'manual': True, 'checks': {'all': {'argv': ['true']}}}}
        item, _ = self.layout(profiles)
        self.assertIsNone(item)  # 无运行记录不提示
        self.record('change', 'unit', 489)
        self.record('change', 'lint', 12)
        self.record('full', 'all', 900)
        item, report = self.layout(profiles)
        self.assertEqual('提示', item['status'])
        text = diagnostics.format_report(report)
        self.assertIn('change 的检查 unit 最近实际执行 489 秒', text)
        self.assertIn('manual profile', text)
        self.assertNotIn('lint 最近', text)
        self.assertNotIn('all 最近', text)

    def test_reused_duration_does_not_count(self):
        profiles = {'change': {'inputs': ['source.txt'], 'checks': {'unit': {'argv': ['true'], 'covers': ['source.txt']}}}}
        self.record('change', 'unit', 400, reused=True)
        item, _ = self.layout(profiles)
        self.assertIsNone(item)

    def test_migrated_layout_reports_nothing(self):
        item, _ = self.layout({
            'change': {'inputs': ['source.txt'], 'checks': {'debug': {'argv': ['true'], 'covers': ['source.txt']}}},
            'release': {'inputs': ['source.txt'], 'manual': True, 'checks': {
                'release': {'argv': ['xcodebuild', '-configuration', 'Release', 'build']}}}})
        self.assertIsNone(item)
