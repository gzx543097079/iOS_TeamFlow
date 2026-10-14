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
        self.assertIn('[历史] 已交付需求证据无法对应交付提交 1 张', diagnostics.format_report(report))
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
