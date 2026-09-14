import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('check_selection', ROOT / 'scripts/run_workflow_checks.py')
selection = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selection)


class CheckSelectionTests(unittest.TestCase):
    def test_docs_templates_and_mixed_changes(self):
        self.assertEqual([selection.DOCUMENTS], selection.select_checks([
            'README.md', 'requirements/REQ-20260911-120000001Z-abcdef01.md',
            'requirements/delivery/REQ-20260911-120000001Z-abcdef01.json', 'requirements/DELIVERY.md',
            'logs/reviews/fixture.json', 'logs/reviews/fixture.patch']))
        template = selection.SKILL + 'references/templates/new-project.md'
        selected = selection.select_checks([template])
        self.assertIn(selection.TEMPLATE, selected)
        self.assertIn('test_consumer_release', selected)
        mixed = selection.select_checks([template, selection.SKILL + 'scripts/project_checks.py'])
        for name in ('test_project_checks', 'test_delivery', 'test_workflow', 'test_consumer_release', 'test_scenarios'):
            self.assertIn(name, mixed)
        self.assertNotIn(selection.DOCUMENTS, mixed)  # 整模块已含文档检查。
        self.assertNotIn(selection.TEMPLATE, mixed)

    def test_unknown_public_and_test_changes_fall_back_to_full(self):
        for name in ('scripts/run_workflow_checks.py', 'scripts/package_release.py',
                     'scripts/validate_workflow.py', 'tests/test_delivery.py', 'delivery.py',
                     'requirements/source.py', 'logs/reviews/hidden.py',
                     '.github/workflows/teamflow-check.yml', selection.SKILL + 'references/VERSION',
                     selection.SKILL + 'scripts/future_tool.py'):
            self.assertIsNone(selection.select_checks(['README.md', name]), name)

    def test_tool_dependencies_include_consumers_and_gates(self):
        for tool in selection.TOOLS:
            selected = selection.select_checks([selection.SKILL + 'scripts/' + tool])
            self.assertIn('test_consumer_release', selected, tool)
            self.assertIn('test_workflow', selected, tool)
        self.assertIn('test_git_checks', selection.select_checks(['scripts/review_gate.py']))

    def test_git_range_preserves_deletions_renames_and_missing_base(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()
            git('init', '-q'); git('config', 'user.email', 'fixture@example.test'); git('config', 'user.name', 'Fixture')
            (root / 'README.md').write_text('old')
            (root / 'tool.py').write_text('code')
            git('add', '.'); git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            (root / 'README.md').unlink()
            (root / 'tool.py').rename(root / 'new.py')
            git('add', '-A'); git('commit', '-qm', 'change')
            paths = selection.changed_paths(root, base, 'HEAD')
            self.assertEqual({'README.md', 'tool.py', 'new.py'}, set(paths))
            self.assertIsNone(selection.select_checks(paths))
            for missing in (None, '', '0' * 40, 'f' * 40, '--bad-ref'):
                self.assertIsNone(selection.changed_paths(root, missing, 'HEAD'))
            self.assertIsNone(selection.changed_paths(root, base, 'missing-head'))

    def test_cli_list_and_failed_test_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'scripts').mkdir(); (root / 'tests').mkdir()
            script = root / 'scripts/run_workflow_checks.py'
            shutil.copyfile(ROOT / 'scripts/run_workflow_checks.py', script)
            (root / 'tests/test_fixture.py').write_text('import unittest\nclass Failure(unittest.TestCase):\n    def test_failure(self):\n        self.fail("intentional failure")\n')
            command = [sys.executable, str(script), '--full']
            listing = subprocess.run(command + ['--list'], capture_output=True, text=True)
            self.assertEqual(0, listing.returncode)
            self.assertEqual('full', json.loads(listing.stdout)['scope'])
            failed = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(1, failed.returncode)
            self.assertIn('intentional failure', failed.stderr)
            (root / 'tests/test_fixture.py').unlink()
            empty = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(0, empty.returncode)
            self.assertIn('未发现测试', empty.stderr)
