"""从实际分发 ZIP 验证消费项目操作顺序；不模拟真实 App 验收。"""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

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
        self.root = Path(self.temp.name).resolve()
        directory = self.root / '.agents/skills'
        directory.mkdir(parents=True)
        with zipfile.ZipFile(self.archive) as archive:
            archive.extractall(directory)
        self.skill = '.agents/skills/ios-team-flow/scripts/'

    def run_cli(self, *args, ok=True):
        result = subprocess.run(args, cwd=self.root, capture_output=True, text=True)
        if ok:
            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        return result

    def cli(self, script, *args, ok=True):
        return self.run_cli(sys.executable, self.skill + script, *args, ok=ok)

    def git(self, *args, ok=True):
        return self.run_cli('git', *args, ok=ok)

    def initialize(self):
        self.git('init', '-q')
        self.git('config', 'user.name', 'Consumer Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')

    def test_bug_template_in_package_preserves_history_through_finish(self):
        self.initialize()
        created = json.loads(self.cli('delivery.py', 'create', '--template', 'bug-fix', '--title', '切换语言后返回按钮未更新').stdout)
        identifier = created['requirement']
        card = Path(created['card'])
        self.assertEqual(self.root / 'requirements' / (identifier + '.md'), card)
        self.assertIn('- 类型：Bug Fix', card.read_text())
        self.assertNotIn('REQ-YYYYMMDD', card.read_text())
        history = '\n| 2026-09-15T10:00:00+08:00 | Test | 复现 | 首次尝试仍失败，保留证据 | fixture-log |\n'
        content = card.read_text().replace('⬜ 未执行', '🔄 执行中') + history
        card.write_text(content)
        rows = json.loads(self.cli('delivery.py', 'list', '--json').stdout)
        self.assertEqual([identifier], [row['requirement'] for row in rows])
        self.cli('delivery.py', '--requirement', identifier, 'finish')
        self.assertEqual(content, card.read_text())
        record = self.root / 'requirements/delivery' / (identifier + '.json')
        before = record.read_bytes()
        self.cli('delivery.py', '--requirement', identifier, 'finish')
        self.assertEqual(before, record.read_bytes())
        self.assertEqual(content, card.read_text())
        self.assertTrue((self.root / '.agents/skills/ios-team-flow/references/BUGFIX.md').is_file())

    def test_cold_install_diagnoses_without_changing_project(self):
        (self.root / 'AGENTS.md').write_text('团队原规则\n')
        (self.root / 'project.yml').write_text('deploymentTarget: 17.0\nframework: SwiftUI\n')
        ignore = self.root / '.gitignore'; ignore.write_text('existing-cache/\n')
        output = self.cli('setup_project.py', '--project', '.').stdout
        self.assertIn('Git 根目录', output)
        self.assertIn('待配置', output)
        self.assertFalse((self.root / 'App').exists())
        self.assertFalse((self.root / '.git').exists())
        self.assertEqual('existing-cache/\n', ignore.read_text())
        self.assertTrue((self.root / 'AGENTS.md').read_text().startswith('团队原规则'))
        before = {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()}
        self.cli('setup_project.py', '--project', '.', '--doctor')
        self.cli('setup_project.py', '--project', '.')
        self.assertEqual(before, {p: p.read_bytes() for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual('deploymentTarget: 17.0\nframework: SwiftUI\n', (self.root / 'project.yml').read_text())

    def test_first_gate_without_gitignore_and_importing_test_passes(self):
        self.cli('setup_project.py', '--project', '.')
        self.initialize()
        (self.root / 'model.py').write_text('value = 1\n')
        config = {'schema_version': 1, 'checks': {'unit': {'argv': [sys.executable, '-c',
                  'import model; assert model.value == 1']}}, 'profiles': {'change': ['unit']}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))
        self.cli('project_checks.py', 'run', '--profile', 'change')
        result = next((self.root / 'logs/project-checks').glob('*/result.json'))
        self.assertEqual('通过', json.loads(result.read_text())['status'])
        self.git('add', '.')
        self.run_cli(sys.executable, 'scripts/review_gate.py', 'prepare')
        report = next((self.root / 'logs/reviews').glob('*.json'))
        data = json.loads(report.read_text())
        data.update(reviewer='消费项目 CLI 夹具', completed_at='2026-09-11T00:00:00+08:00',
                    summary='测试首次门禁副作用，不代表业务审查', validation_results=[str(result.relative_to(self.root))])
        for item in data['checks'].values():
            item.update(status='不适用', evidence='纯工具 CLI 夹具，不代表 App 验收')
        report.write_text(json.dumps(data))
        self.git('add', 'logs/reviews')
        self.run_cli(sys.executable, 'scripts/review_gate.py', 'check')
        self.assertFalse((self.root / self.skill / '__pycache__').exists())
        self.cli('setup_project.py', '--project', '.', '--doctor')
        self.assertFalse((self.root / self.skill / '__pycache__').exists())

    def test_two_branches_create_distinct_cards_and_merge(self):
        self.cli('setup_project.py', '--project', '.')
        self.initialize()
        self.git('add', '.'); self.git('commit', '-qm', 'base')
        base = self.git('rev-parse', 'HEAD').stdout.strip()
        ids = []
        for branch in ('member-a', 'member-b'):
            self.git('checkout', '-qb', branch, base)
            result = json.loads(self.cli('delivery.py', 'create', '--title', branch).stdout)
            ids.append(result['requirement'])
            self.assertRegex(ids[-1], r'^REQ-\d{8}-\d{9}Z-[0-9a-f]{8}$')
            self.git('add', 'requirements')
            self.git('commit', '-qm', branch + '\n\nRequirement: ' + ids[-1])
        self.assertNotEqual(*ids)
        self.git('checkout', '-q', 'member-a')
        self.git('merge', 'member-b', '--no-edit')
        self.cli('delivery.py', 'finish', '--all')
        for identifier in ids:
            self.assertTrue((self.root / 'requirements' / (identifier + '.md')).exists())
            record = json.loads((self.root / 'requirements/delivery' / (identifier + '.json')).read_text())
            self.assertEqual(1, len(record['snapshot']['commits']))

    def test_existing_v2_cards_are_not_implicitly_migrated(self):
        self.cli('setup_project.py', '--project', '.')
        self.initialize()
        old = self.root / 'requirements/REQ-20260911-001.md'
        old.write_text('# 旧卡\n<!-- teamflow:requirement:v2 -->\n- 状态：✅ 执行完成\n')
        result = json.loads(self.cli('delivery.py', 'create', '--title', '新需求').stdout)
        self.cli('delivery.py', 'finish', '--all')
        self.assertFalse((self.root / 'requirements/delivery/REQ-20260911-001.json').exists())
        self.assertTrue((self.root / 'requirements/delivery' / (result['requirement'] + '.json')).exists())

    def test_shared_commit_collision_can_be_relinked_without_rewriting_history(self):
        self.cli('setup_project.py', '--project', '.')
        self.initialize()
        (self.root / 'code.txt').write_text('second feature')
        old = self.root / 'requirements/REQ-20260911-120000001Z-abcdef01.md'; old.write_text('# old card')
        self.git('add', '.'); self.git('commit', '-qm', 'feature\n\nRequirement: REQ-20260911-120000001Z-abcdef01')
        sha = self.git('rev-parse', 'HEAD').stdout.strip()
        new = json.loads(self.cli('delivery.py', 'create', '--title', '独立需求').stdout)['requirement']
        self.cli('delivery.py', '--requirement', new, 'link-commit', '--commit', sha)
        self.cli('delivery.py', '--requirement', 'REQ-20260911-120000001Z-abcdef01', 'exclude-commit', '--commit', sha, '--reason', '编号冲突，迁入新需求')
        old_data = json.loads((self.root / 'requirements/delivery/REQ-20260911-120000001Z-abcdef01.json').read_text())
        new_data = json.loads((self.root / 'requirements/delivery' / (new + '.json')).read_text())
        self.assertEqual([], old_data['snapshot']['commits'])
        self.assertEqual([sha], new_data['snapshot']['commits'])
        self.assertEqual(sha, self.git('rev-parse', 'HEAD').stdout.strip())

    def test_result_acceptance_and_two_sequential_requirements_from_zip(self):
        self.cli('setup_project.py', '--project', '.')
        self.initialize()
        app = self.root / 'App'; app.mkdir()
        (app / 'A.swift').write_text('A')
        config = {'schema_version': 1, 'inputs': ['App'],
                  'checks': {'unit': {'argv': [sys.executable, '-c', 'pass']}},
                  'profiles': {'change': ['unit']}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))
        req = json.loads(self.cli('delivery.py', 'create', '--title', 'A').stdout)['requirement']
        self.cli('project_checks.py', 'run', '--profile', 'change')
        result = str(next((self.root / 'logs/project-checks').glob('*/result.json')).relative_to(self.root))
        card = self.root / 'requirements' / (req + '.md')
        card.write_text(card.read_text().replace('⬜ 未执行', '✅ 执行完成')
                        .replace('实施并验证 AC-01', '无').replace('| 未验证 | — |', '| 通过 | ' + result + ' |'))
        self.cli('delivery.py', '--requirement', req, 'finish', '--accept', '--result', result)
        self.git('add', '.'); self.git('commit', '-qm', 'A\n\nRequirement: ' + req)
        self.cli('delivery.py', '--requirement', req, 'finish')
        second = json.loads(self.cli('delivery.py', 'create', '--title', 'B').stdout)['requirement']
        (app / 'B.swift').write_text('B')
        self.git('add', '.'); self.git('commit', '-qm', 'B\n\nRequirement: ' + second)
        self.cli('delivery.py', 'finish', '--all')
        record = json.loads((self.root / 'requirements/delivery' / (req + '.json')).read_text())
        self.assertIn('accepted_commit', record['acceptance_baseline'])
        self.assertEqual('✅ 执行完成', record['snapshot']['development'])
        self.cli('delivery.py', 'finish', '--all', '--check')

    def test_document_validation_survives_acceptance_and_rejects_content_changes(self):
        self.cli('setup_project.py', '--project', '.')
        self.initialize()
        req = json.loads(self.cli('delivery.py', 'create', '--title', '文档需求').stdout)['requirement']
        config = {'schema_version': 1, 'inputs': ['requirements'],
                  'checks': {'docs': {'argv': [sys.executable, '-c', 'pass']}},
                  'profiles': {'docs': ['docs']}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))
        self.cli('project_checks.py', 'run', '--profile', 'docs')
        result = str(next((self.root / 'logs/project-checks').glob('*/result.json')).relative_to(self.root))
        card = self.root / 'requirements' / (req + '.md')
        card.write_text(card.read_text().replace('⬜ 未执行', '✅ 执行完成')
                        .replace('实施并验证 AC-01', '无').replace('| 未验证 | — |', '| 通过 | ' + result + ' |'))
        self.cli('delivery.py', '--requirement', req, 'finish', '--accept', '--result', result)
        self.git('add', '.')
        self.cli('project_checks.py', 'verify', '--result', result, '--staged')
        card.write_text(card.read_text().replace('可观察的输入、操作与预期结果', '改变了产品验收条件'))
        self.assertNotEqual(0, self.cli('project_checks.py', 'verify', '--result', result, ok=False).returncode)
        self.assertNotEqual(0, self.cli('delivery.py', '--requirement', req, 'finish', ok=False).returncode)
