"""代表性消费项目链路演练；不宣称运行过真实 iOS App。"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / '.agents/skills/ios-team-flow'


class ConsumerScenarios(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='teamflow scenario ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(SKILL, self.root / '.agents/skills/ios-team-flow')

    def run_command(self, *argv, success=True):
        result = subprocess.run(argv, cwd=self.root, text=True, capture_output=True)
        if success:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def tool(self, name, *args, success=True):
        return self.run_command(sys.executable, '.agents/skills/ios-team-flow/scripts/' + name + '.py',
                                '--project', '.', *args, success=success)

    def test_new_project_setup_does_not_create_unconfirmed_app(self):
        self.tool('setup_project')
        self.assertTrue((self.root / 'AGENTS.md').exists())
        self.assertFalse((self.root / 'App').exists())
        self.tool('project_checks', 'init')
        self.tool('project_checks', 'run', '--profile', 'build', success=False)
        self.assertFalse(list(self.root.glob('logs/project-checks/*/result.json')))

    def test_existing_project_preserves_config_and_failing_baseline(self):
        app = self.root / 'Legacy'
        app.mkdir()
        config = app / 'Project.xcconfig'
        content = 'IPHONEOS_DEPLOYMENT_TARGET = 17.0\nPRODUCT_BUNDLE_IDENTIFIER = example.existing\n'
        config.write_text(content)
        (app / 'Home.swift').write_text('import SwiftUI\n// Existing TabView, no theme migration requested\n')
        self.tool('setup_project')
        self.assertEqual(config.read_text(), content)
        self.assertFalse((self.root / 'App').exists())
        checks = {'schema_version': 1, 'inputs': ['Legacy'], 'checks': {'baseline': {'argv': [sys.executable, '-c', 'raise SystemExit(7)']}},
                  'profiles': {'existing': ['baseline']}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(checks))
        self.tool('project_checks', 'run', '--profile', 'existing', success=False)
        report = json.loads(next(self.root.glob('logs/project-checks/*/result.json')).read_text())
        self.assertEqual(report['results'][0]['exit_code'], 7)

    def test_subscription_missing_evidence_blocks_and_content_change_invalidates(self):
        self.tool('setup_project')
        self.run_command('git', 'init', '-q')
        self.run_command('git', 'config', 'user.name', 'Scenario Fixture')
        self.run_command('git', 'config', 'user.email', 'fixture@example.invalid')
        self.run_command('git', 'config', 'commit.gpgsign', 'false')
        self.run_command('git', 'add', '.')
        self.run_command('git', 'commit', '-qm', 'fixture baseline')
        app = self.root / 'App'
        app.mkdir()
        product = app / 'subscription.json'
        product.write_text(json.dumps({'product_id': 'example.monthly', 'period': 'month', 'label': '每年续费'}))
        self.run_command('git', 'add', 'App')
        self.run_command(sys.executable, 'scripts/review_gate.py', 'prepare')
        report_path = next(self.root.glob('logs/reviews/*.json'))
        report = json.loads(report_path.read_text())
        report.update(reviewer='测试夹具', completed_at='2026-09-11T00:00:00Z', summary='模拟人工指出月套餐与年文案不一致')
        for item in report['checks'].values():
            item.update(status='不适用', evidence='夹具仅验证门禁记录行为，不是实际业务审查')
        report['checks']['subscription'].update(status='通过', evidence='')
        report_path.write_text(json.dumps(report))
        self.run_command('git', 'add', 'logs/reviews')
        self.run_command(sys.executable, 'scripts/review_gate.py', 'check', success=False)
        report['checks']['subscription'].update(status='未验证', evidence='商品周期与文案不匹配，需要修复')
        report_path.write_text(json.dumps(report))
        self.run_command('git', 'add', 'logs/reviews')
        self.run_command(sys.executable, 'scripts/review_gate.py', 'check', success=False)
        product.write_text(json.dumps({'product_id': 'example.monthly', 'period': 'month', 'label': '每月续费'}))
        self.run_command('git', 'add', 'App')
        self.run_command(sys.executable, 'scripts/review_gate.py', 'prepare')
        self.assertEqual(len(list(self.root.glob('logs/reviews/*.json'))), 2)
        self.run_command(sys.executable, 'scripts/review_gate.py', 'check', success=False)
