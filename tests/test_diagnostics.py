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

    def test_doctor_treats_stale_finished_evidence_as_history(self):
        req = self.create(); self.fill(req)
        flow.complete(self.root, req, profile='change')
        (self.root / 'source.txt').write_text('changed')
        report = diagnostics.doctor(self.root)
        item = next(i for i in report['checks'] if i['item'] == req)
        self.assertEqual('历史', item['status'])
        self.assertFalse(any(i['status'] == '需处理' and i['item'].startswith('REQ-') for i in report['checks']))
        self.assertIn('[历史] 已完成需求证据失效 1 张', diagnostics.format_report(report))

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
