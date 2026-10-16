import json
import os
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
        # 零命令安装：解压到项目根即可使用，不运行 setup。
        with zipfile.ZipFile(self.archive) as archive:
            archive.extractall(self.root)
        subprocess.run(['git', '-C', str(self.root), 'init', '-q'], check=True)

    def cli(self, *args, ok=True):
        # 必须验证默认缓存行为，不能由宿主禁用或重定向缓存来掩盖安装缺陷。
        env = {key: value for key, value in os.environ.items()
               if key not in ('PYTHONDONTWRITEBYTECODE', 'PYTHONPYCACHEPREFIX')}
        result = subprocess.run([sys.executable, str(self.root / 'scripts/teamflow.py'),
                                 '--project', str(self.root), *args], capture_output=True, text=True, env=env)
        if ok:
            self.assertEqual(0, result.returncode, result.stderr)
        return result

    def test_packaged_requirement_and_removed_release_record(self):
        created = json.loads(self.cli('req', 'create', '--title', '新需求', '--json').stdout)
        self.assertRegex(created['requirement'], r'^REQ-\d{8}-[0-9a-f]{4}$')
        self.assertFalse((self.root / '.gitignore').exists())
        report = json.loads(self.cli('doctor', '--json', ok=False).stdout)
        entry = next(item for item in report['checks'] if item['item'] == 'Skill 与入口')
        self.assertEqual('就绪', entry['status'], entry)
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
        # 未运行 setup 也不会把本地验证日志带进提交。
        untracked = subprocess.run(['git', '-C', str(self.root), 'status', '--porcelain', '--untracked-files=all'],
                                   check=True, capture_output=True, text=True).stdout
        self.assertNotIn('logs/', untracked)
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


    def test_first_commit_does_not_require_profile_to_cover_install_files(self):
        req = json.loads(self.cli('req', 'create', '--title', '首次提交', '--json').stdout)['requirement']
        card = self.root / 'requirements' / (req + '.md')
        card.write_text(card.read_text().replace('〈填写本次要达到的结果〉', '首个页面')
                        .replace('〈填写可观察的输入、操作和预期结果〉', '页面可见'))
        (self.root / 'App').mkdir()
        (self.root / 'App/main.swift').write_text('print(1)\n')
        config = {'schema_version': 2, 'profiles': {'change': {'inputs': ['App'],
                  'checks': {'unit': {'argv': [sys.executable, '-c', 'pass']}}}}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))
        self.cli('req', 'complete', req, '--profile', 'change', '--confirm-ac', 'AC-01')
        self.assertEqual([], list((self.root / '.agents/teamflow-core').rglob('__pycache__')))
        subprocess.run(['git', '-C', str(self.root), 'add', '-A'], check=True)
        report = json.loads(self.cli('git', 'check', req, '--json').stdout)
        self.assertEqual(['App/main.swift'], report['release_sensitive_files'])
        # 直接改过的核心文件不再算安装文件，仍须由验证覆盖。
        workflow = self.root / '.agents/teamflow-core/references/WORKFLOW.md'
        workflow.write_text(workflow.read_text() + '\n团队改动\n')
        subprocess.run(['git', '-C', str(self.root), 'add', '-A'], check=True)
        result = self.cli('git', 'check', req, ok=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('WORKFLOW.md', result.stderr)

    def test_packaged_host_permissions_ask_before_external_actions(self):
        settings = json.loads((self.root / '.claude/settings.json').read_text())
        self.assertIn('Bash(git push:*)', settings['permissions']['ask'])
        self.assertIn('Bash(gh release:*)', settings['permissions']['ask'])
        rules = []
        source = (self.root / '.codex/rules/teamflow.rules').read_text()
        # Starlark 规则语法与 Python 兼容，这里用桩函数核对字段与内联示例。
        exec(compile(source, 'teamflow.rules', 'exec'), {'prefix_rule': lambda **rule: rules.append(rule)})
        self.assertTrue(rules)
        for rule in rules:
            self.assertEqual('prompt', rule['decision'])
            for command in rule.get('match', []):
                self.assertTrue(prefix_matches(rule['pattern'], command.split()), command)
            for command in rule.get('not_match', []):
                self.assertFalse(prefix_matches(rule['pattern'], command.split()), command)
        self.assertIn(['git', 'push'], [rule['pattern'] for rule in rules])


def prefix_matches(pattern, argv):
    return len(argv) >= len(pattern) and all(
        word == part if isinstance(part, str) else word in part for part, word in zip(pattern, argv))

if __name__ == '__main__':
    unittest.main()
