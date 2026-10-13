import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from release_fixture import skill_archive


class ConsumerReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.archive = skill_archive()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        with zipfile.ZipFile(self.archive) as archive:
            archive.extractall(self.root / '.agents/skills')
        subprocess.run(['git', '-C', str(self.root), 'init', '-q'], check=True)
        setup = self.root / '.agents/skills/ios-team-flow/scripts/teamflow.py'
        result = subprocess.run([sys.executable, str(setup), '--project', str(self.root), 'setup'],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)

    def cli(self, *args, ok=True):
        result = subprocess.run([sys.executable, str(self.root / 'scripts/teamflow.py'),
                                 '--project', str(self.root), *args], capture_output=True, text=True)
        if ok:
            self.assertEqual(0, result.returncode, result.stderr)
        return result

    def test_packaged_requirement_and_removed_release_record(self):
        created = json.loads(self.cli('req', 'create', '--title', '新需求', '--json').stdout)
        self.assertRegex(created['requirement'], r'^REQ-\d{8}-[0-9a-f]{4}$')
        self.assertIn('/logs/project-checks/', (self.root / '.gitignore').read_text().splitlines())
        listing = self.cli('req', 'list').stdout
        self.assertIn(created['requirement'], listing)
        self.assertIn('🔵 进行中', listing)
        self.assertIn('⚪ 0/1', listing)
        self.assertNotEqual(0, self.cli('release', 'record', ok=False).returncode)

    def test_packaged_validation_and_manual_confirmation(self):
        req = json.loads(self.cli('req', 'create', '--title', '人工确认', '--json').stdout)['requirement']
        card = self.root / 'requirements' / (req + '.md')
        card.write_text(card.read_text().replace('〈填写本次要达到的结果〉', '显示提示')
                        .replace('〈填写可观察的输入、操作和预期结果〉', '错误时展示提示'))
        (self.root / 'source.txt').write_text('source')
        config = {'schema_version': 2, 'profiles': {'change': {'inputs': ['source.txt'],
                  'checks': {'unit': {'argv': [sys.executable, '-c', 'pass']}}}}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))
        self.cli('req', 'complete', req, '--profile', 'change', '--wait-user')
        status = json.loads(self.cli('req', 'status', req, '--json').stdout)
        self.assertEqual('待用户验证', status['state_key'])
        self.assertEqual(0, status['progress']['done'])
        self.assertNotEqual(0, self.cli('req', 'state', req, '--state', '完成', ok=False).returncode)
        self.cli('req', 'complete', req, '--confirm-ac', 'AC-01', '--wait-user')
        self.assertEqual('完成', json.loads(self.cli('req', 'status', req, '--json').stdout)['state_key'])

    def test_packaged_manual_proof_rejects_changed_conditions(self):
        req = json.loads(self.cli('req', 'create', '--title', '人工证据', '--json').stdout)['requirement']
        card = self.root / 'requirements' / (req + '.md')
        card.write_text(card.read_text().replace('〈填写本次要达到的结果〉', '显示提示')
                        .replace('〈填写可观察的输入、操作和预期结果〉', '错误时展示提示'))
        self.cli('req', 'complete', req, '--evidence', '实际核对记录', '--confirm-ac', 'AC-01')
        card.write_text(card.read_text().replace('错误时展示提示', '新增场景实际展示正确'))
        original = card.read_text()
        result = self.cli('req', 'complete', req, ok=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('需求范围或 AC 已变化', result.stderr)
        self.assertEqual(original, card.read_text())

    def test_packaged_readonly_helpers(self):
        req = json.loads(self.cli('req', 'create', '--title', '恢复', '--json').stdout)['requirement']
        summary = json.loads(self.cli('req', 'status', req, '--json').stdout)
        self.assertTrue(summary['problems'])
        self.assertNotEqual(0, self.cli('req', 'resume', req, ok=False).returncode)
        doctor = self.cli('doctor', '--json', ok=False)
        self.assertEqual(1, doctor.returncode)
        self.assertTrue(json.loads(doctor.stdout)['needs_action'])
        brief = self.cli('doctor', ok=False)
        self.assertEqual(1, brief.returncode)
        self.assertIn('结论：需处理', brief.stdout)
        (self.root / 'sample.txt').write_text('sample')
        config = {'schema_version': 2, 'profiles': {'change': {'inputs': ['sample.txt'],
                  'checks': {'unit': {'argv': [sys.executable, '-c', 'pass']}}}}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))
        suggested = json.loads(self.cli('verify', 'suggest', '--json').stdout)
        self.assertIn('sample.txt', suggested['profiles'][0]['covered_files'])
        self.assertFalse((self.root / 'logs').exists())


if __name__ == '__main__':
    unittest.main()
