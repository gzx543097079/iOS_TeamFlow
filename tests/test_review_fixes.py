"""v1.3.0 复查问题的回归：人工证据白名单、钩子、阶段提交后的自动选择、重开、安装文件豁免与 CI 覆盖。"""
import json
import sys
import unittest
from unittest.mock import patch
import test_teamflow
import diagnostics
import setup_project

flow = test_teamflow.flow


class ReviewFixTests(unittest.TestCase):
    setUp = test_teamflow.TeamFlowTests.setUp
    git = test_teamflow.TeamFlowTests.git
    configure_checks = test_teamflow.TeamFlowTests.configure_checks
    create = test_teamflow.TeamFlowTests.create
    fill = test_teamflow.TeamFlowTests.fill
    card_path = test_teamflow.TeamFlowTests.card_path
    baseline = test_teamflow.TeamFlowTests.baseline

    def set_profiles(self, profiles):
        (self.root / '.agents/project-checks.json').write_text(
            json.dumps({'schema_version': 2, 'profiles': profiles}))

    def ok(self):
        return {'ok': {'argv': [sys.executable, '-c', 'pass']}}

    # 1. 人工证据与提交检查共用文档白名单
    def test_manual_evidence_rejects_godot_and_config_changes(self):
        self.baseline()
        req = self.create(); self.fill(req)
        for name in ('player.gd', 'main.tscn', 'export_presets.cfg', 'settings.json'):
            with self.subTest(name=name):
                (self.root / name).write_text('changed')
                with self.assertRaisesRegex(ValueError, '非文档改动：' + name):
                    flow.complete(self.root, req, evidence='看过了')
                (self.root / name).unlink()
        (self.root / 'notes.md').write_text('doc')
        flow.complete(self.root, req, evidence='核对文档')

    # 2. 钩子不绑定 profile，接受文档人工证据，并优先核对暂存与进行中的卡
    def test_hook_accepts_manual_document_evidence(self):
        self.baseline()
        req = self.create(); self.fill(req, done=False)
        (self.root / 'docs').mkdir(); (self.root / 'docs/a.md').write_text('doc')
        flow.complete(self.root, req, evidence='核对文档', evidence_inputs=['docs'], confirm_ac=['AC-01'])
        self.git('add', '-A')
        self.assertEqual(req, flow.hook_check(self.root)['requirement'])

    def test_hook_checks_staged_and_active_cards_before_history(self):
        old = self.create('历史'); self.fill(old)
        flow.complete(self.root, old, profile='change')
        self.baseline()
        (self.root / 'source.txt').write_text('next')
        current = self.create('当前'); self.fill(current)
        flow.complete(self.root, current, profile='change')
        self.git('add', '-A')
        calls = []
        original = flow.git_check

        def record(root, requirement, *args, **kwargs):
            calls.append(requirement)
            return original(root, requirement, *args, **kwargs)
        with patch.object(flow, 'git_check', side_effect=record):
            self.assertEqual(current, flow.hook_check(self.root)['requirement'])
        self.assertEqual([current], calls)

    def test_hook_points_document_only_changes_to_lightweight_path(self):
        self.baseline()
        (self.root / 'README.md').write_text('typo fixed')
        self.git('add', 'README.md')
        with self.assertRaisesRegex(ValueError, '--no-verify'):
            flow.hook_check(self.root)
        (self.root / 'App.swift').write_text('let a = 1')
        self.git('add', 'App.swift')
        with self.assertRaises(ValueError) as caught:
            flow.hook_check(self.root)
        self.assertNotIn('--no-verify', str(caught.exception))

    def test_legacy_hook_still_runs_but_doctor_requests_migration(self):
        args = flow.build_parser().parse_args(['git', 'hook', '--profile', 'change'])
        self.assertEqual(('git', 'hook'), (args.area, args.command))
        hook = setup_project.hook_path(self.root)
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text("#!/bin/sh\n" + setup_project.HOOK_MARK +
                        "\nexec python3 scripts/teamflow.py git hook --profile 'change'\n")
        status = setup_project.hook_status(self.root)[0]
        self.assertEqual('需处理', status['status'])
        self.assertIn('迁移', status['detail'])
        hook.write_text(setup_project.HOOK.format(mark=setup_project.HOOK_MARK))
        self.assertEqual('就绪', setup_project.hook_status(self.root)[0]['status'])

    # 3. 自动选择计入本需求带尾注的已提交改动
    def test_auto_selection_includes_stage_commits_of_requirement(self):
        (self.root / 'notes.md').write_text('notes')
        self.set_profiles({
            'docs': {'inputs': ['notes.md'], 'priority': 10, 'checks': self.ok()},
            'full': {'inputs': ['source.txt', 'notes.md', '.gitignore'], 'checks': self.ok()}})
        self.baseline()
        req = self.create(); self.fill(req)
        (self.root / 'source.txt').write_text('stage one')
        self.git('add', '-A'); self.git('commit', '-qm', 'stage\n\nRequirement: ' + req)
        checks = flow.checks_module()
        self.assertEqual('full', checks.select_profile(self.root, req))
        (self.root / 'notes.md').write_text('notes changed')
        self.assertEqual('docs', checks.select_profile(self.root))
        self.assertEqual('full', checks.select_profile(self.root, req))
        flow.complete(self.root, req)
        self.assertEqual('full', flow.parse_card(self.card_path(req))['evidence']['profile'])

    def test_auto_selection_after_everything_is_committed(self):
        self.baseline()
        req = self.create(); self.fill(req)
        (self.root / 'source.txt').write_text('done')
        self.git('add', '-A'); self.git('commit', '-qm', 'all\n\nRequirement: ' + req)
        self.assertEqual('change', flow.checks_module().select_profile(self.root, req))

    # 4. 重开完成卡须说明原因并取消指定 AC
    def test_reopen_requires_reason_and_unchecks_acceptance(self):
        req = self.create(); card = self.fill(req, done=False)
        flow.complete(self.root, req, profile='change', user_confirmed=['AC-01'])
        self.assertEqual('完成', flow.parse_card(card)['state'])
        with self.assertRaisesRegex(ValueError, '--reopen-ac'):
            flow.set_state(self.root, req, '进行中', '复发')
        with self.assertRaisesRegex(ValueError, '重开必须填写 --reason'):
            flow.set_state(self.root, req, '进行中', reopen_ac=['AC-01'])
        with self.assertRaisesRegex(ValueError, '未知 AC'):
            flow.set_state(self.root, req, '进行中', '复发', reopen_ac=['AC-09'])
        with self.assertRaisesRegex(ValueError, '只用于恢复为进行中'):
            flow.set_state(self.root, req, '阻塞', '复发', '外部', reopen_ac=['AC-01'])
        flow.set_state(self.root, req, '进行中', '同一缺陷复发', reopen_ac=['AC-01'])
        reopened = flow.parse_card(card)
        self.assertEqual('进行中', reopened['state'])
        self.assertIn('- [ ] AC-01', card.read_text())
        self.assertNotIn('user_confirmed', reopened['meta'])
        self.assertIn('（重开 AC-01） — 同一缺陷复发', reopened['body'])
        self.assertEqual('进行中', flow.complete(self.root, req)['state_key'])

    # 5. AGENTS 与宿主权限只在未改动项目自有内容时豁免；其他 profile 的变化明确提示
    def test_project_rules_and_permissions_need_coverage(self):
        agents = self.root / 'AGENTS.md'
        agents.write_text('# 项目规则\n\n' + setup_project.BLOCK)
        self.baseline()
        req = self.create(); self.fill(req)
        flow.complete(self.root, req, profile='change')
        agents.write_text(agents.read_text().replace('读取并遵循', '请读取并遵循'))
        self.git('add', '-A')
        flow.git_check(self.root, req)
        agents.write_text(agents.read_text().replace('# 项目规则', '# 项目规则\n\n禁止直接改数据库'))
        self.git('add', '-A')
        with self.assertRaisesRegex(ValueError, '未覆盖暂存文件：AGENTS.md'):
            flow.git_check(self.root, req)
        self.git('checkout', 'HEAD', '--', 'AGENTS.md')
        settings = self.root / '.claude/settings.json'
        settings.parent.mkdir()
        template = flow.Path(setup_project.__file__).resolve().parents[1] / 'assets/permissions/claude-settings.json'
        settings.write_text(template.read_text())
        self.git('add', '-A')
        flow.git_check(self.root, req)
        settings.write_text('{"permissions": {"allow": ["Bash(*)"]}}')
        self.git('add', '-A')
        with self.assertRaisesRegex(ValueError, '未覆盖暂存文件：.claude/settings.json'):
            flow.git_check(self.root, req)

    def test_other_profile_changes_are_reported(self):
        self.baseline()
        req = self.create(); self.fill(req)
        self.set_profiles({'change': {'inputs': ['source.txt', '.gitignore'], 'checks': self.ok()},
                           'extra': {'inputs': ['source.txt'], 'checks': {
                               'net': {'argv': ['curl', 'https://example.invalid']}}}})
        flow.complete(self.root, req, profile='change')
        self.git('add', '-A')
        report = flow.git_check(self.root, req)
        self.assertEqual(['extra'], report['unverified_profiles'])
        self.assertIn('未经本次证据执行，请人工核对：extra', flow.render('git', report))

    # 6. CI 核对非文档改动的覆盖
    def test_ci_requires_coverage_for_code_without_card(self):
        self.baseline()
        base = self.git('rev-parse', 'HEAD')
        (self.root / 'README.md').write_text('docs')
        self.git('add', '-A'); self.git('commit', '-qm', 'docs')
        report = diagnostics.ci_check(self.root, base)
        self.assertFalse(report['needs_action'])
        self.assertIn('文档改动', [item['item'] for item in report['checks']])
        (self.root / 'App.swift').write_text('let a = 1')
        self.git('add', '-A'); self.git('commit', '-qm', 'code')
        report = diagnostics.ci_check(self.root, base)
        self.assertTrue(report['needs_action'])
        uncovered = next(item for item in report['checks'] if item['item'] == '未覆盖改动')
        self.assertIn('App.swift', uncovered['detail'])
        self.set_profiles({'change': {'inputs': ['source.txt', '.gitignore', 'App.swift'], 'checks': self.ok()}})
        req = self.create(); self.fill(req)
        flow.complete(self.root, req, profile='change')
        self.git('add', '-A'); self.git('commit', '-qm', 'deliver\n\nRequirement: ' + req)
        self.assertFalse(diagnostics.ci_check(self.root, base)['needs_action'])


if __name__ == '__main__':
    unittest.main()
