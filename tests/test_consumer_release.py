import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import package_release


class ConsumerReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with contextlib.redirect_stdout(io.StringIO()):
            cls.archive = package_release.package_skill(ROOT)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        with zipfile.ZipFile(self.archive) as archive:
            archive.extractall(self.root / '.agents/skills')
        subprocess.run(['git', '-C', str(self.root), 'init', '-q'], check=True)
        setup = self.root / '.agents/skills/ios-team-flow/scripts/setup_project.py'
        result = subprocess.run([sys.executable, str(setup), '--project', str(self.root)],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(self.root / 'scripts/teamflow.py'),
                                 '--project', str(self.root), *args], capture_output=True, text=True)
        if ok:
            self.assertEqual(0, result.returncode, result.stderr)
        return result

    def test_packaged_requirement_and_explicit_release_boundaries(self):
        created = json.loads(self.cli('req', 'create', '--title', '新需求').stdout)
        self.assertEqual('REQ-0001', created['requirement'])
        listing = self.cli('req', 'list').stdout
        self.assertIn('REQ-0001', listing)
        self.assertIn('🔵 进行中', listing)
        self.assertIn('⚪ 0/1', listing)
        prepared = json.loads(self.cli('release', 'prepare', 'submit-app-review',
                                       '--version', '1.0.0', '--build', '1').stdout)
        self.assertFalse(prepared['external_write'])
        self.assertEqual({}, prepared['export_options_overrides'])
        self.assertFalse((self.root / 'releases').exists())
        self.cli('release', 'record', 'archive', '--version', '1.0.0', '--build', '1',
                 '--evidence', 'archive 校验通过')
        record = self.root / 'releases/App-1.0.0-1.md'
        self.assertIn('归档', record.read_text())
        self.assertNotIn('提交 App Store 审核', record.read_text())

    def test_packaged_testflight_internal_only_is_opt_in(self):
        ordinary = json.loads(self.cli('release', 'prepare', 'upload-testflight',
                                       '--version', '1.0.0', '--build', '2').stdout)
        self.assertEqual({}, ordinary['export_options_overrides'])
        internal = json.loads(self.cli('release', 'prepare', 'upload-testflight',
                                       '--version', '1.0.0', '--build', '2',
                                       '--testflight-internal-only').stdout)
        self.assertEqual({'testFlightInternalTestingOnly': True},
                         internal['export_options_overrides'])
        rejected = self.cli('release', 'prepare', 'archive', '--version', '1.0.0',
                            '--build', '2', '--testflight-internal-only', ok=False)
        self.assertNotEqual(0, rejected.returncode)
        self.assertIn('仅适用于上传 TestFlight', rejected.stderr)

    def test_package_contains_no_legacy_runtime(self):
        legacy = ('delivery.py', 'review_gate.py', 'upgrade_skill.py', 'install_git_checks.py')
        for name in legacy:
            self.assertFalse((self.root / '.agents/skills/ios-team-flow/scripts' / name).exists())


if __name__ == '__main__':
    unittest.main()
