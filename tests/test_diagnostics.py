import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path
import test_teamflow
import diagnostics

flow = test_teamflow.flow


class DiagnosticsTests(unittest.TestCase):
    setUp = test_teamflow.TeamFlowTests.setUp
    git = test_teamflow.TeamFlowTests.git
    configure_checks = test_teamflow.TeamFlowTests.configure_checks
    create = test_teamflow.TeamFlowTests.create
    fill = test_teamflow.TeamFlowTests.fill

    def test_suggestion_reports_uncovered_without_running(self):
        (self.root / 'other.swift').write_text('let a = 1')
        report = flow.checks_module().suggest(self.root)
        self.assertIn('other.swift', report['uncovered_files'])
        self.assertIn('source.txt', report['profiles'][0]['covered_files'])
        self.assertFalse((self.root / 'logs').exists())

    def test_resume_is_read_only_and_checks_stale_evidence(self):
        req = self.create(); card = self.fill(req)
        flow.complete(self.root, req, profile='change')
        original = card.read_bytes()
        self.assertEqual('有效', diagnostics.resume(self.root, req)['evidence_status'])
        (self.root / 'source.txt').write_text('changed')
        report = diagnostics.resume(self.root, req)
        self.assertEqual('缺失或失效', report['evidence_status'])
        self.assertEqual(original, card.read_bytes())
        flow.set_state(self.root, req, '暂停', '等待用户')
        self.assertIn('不得自动继续', diagnostics.resume(self.root, req)['next_step'])

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
