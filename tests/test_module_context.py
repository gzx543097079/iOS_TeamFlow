import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / '.agents/skills/ios-team-flow/scripts/teamflow.py'


class ModuleContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Module Test')
        self.write('App/Account/Login.swift', 'final class Login {}\n')
        self.write('App/Home/Home.swift', 'final class Home {}\n')
        self.write('Project.swift', 'let targets = []\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'initial')

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def write(self, name, body):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)

    def run_tool(self, *args, check=True):
        return subprocess.run([sys.executable, str(TOOL), '--project', str(self.root), 'module', *args],
                              check=check, capture_output=True, text=True)

    def inspect(self, *args):
        return json.loads(self.run_tool('inspect', *args, '--json').stdout)

    def record_account(self, commit=True):
        result = self.run_tool(
            'record', '--name', 'account', '--responsibility', '登录与会话',
            '--trigger', '登录', '--trigger', 'account', '--path', 'App/Account',
            '--entry', 'Login', '--dependency', 'SessionStore', '--caller', 'AppRouter',
            '--verification', 'ios-account', '--cross-cutting', 'Project.swift')
        self.assertEqual('已记录模块：account\n', result.stdout)
        if commit:
            self.git('add', '.agents/project-modules.json')
            self.git('commit', '-qm', 'module index')

    def test_record_has_no_baseline_and_main_is_unchanged(self):
        self.record_account()
        data = json.loads((self.root / '.agents/project-modules.json').read_text())
        self.assertEqual(2, data['schema_version'])
        self.assertNotIn('baseline', data['modules'][0])
        result = self.inspect('--query', '修改登录错误提示')
        self.assertEqual(['account'], result['selected_modules'])
        self.assertEqual('main', result['base'])
        self.assertFalse(result['expand_scope'])
        module = result['modules'][0]
        self.assertEqual('unchanged', module['status'])
        self.assertEqual(['Login'], module['entry_symbols'])
        self.assertEqual([], module['suggested_read_files'])
        brief = self.run_tool('inspect', '--module', 'account').stdout
        self.assertIn('account unchanged', brief)

    def test_branch_reports_committed_staged_unstaged_untracked_and_cross_cutting(self):
        self.record_account()
        self.git('checkout', '-qb', 'feature')
        self.write('App/Account/Login.swift', 'final class Login { let committed = true }\n')
        self.git('add', 'App/Account/Login.swift')
        self.git('commit', '-qm', 'account change')
        self.write('App/Account/Staged.swift', 'let staged = true\n')
        self.git('add', 'App/Account/Staged.swift')
        self.write('App/Account/Login.swift', 'final class Login { let unstaged = true }\n')
        self.write('App/Account/Untracked.swift', 'let untracked = true\n')
        self.write('Project.swift', 'let targets = ["Account"]\n')
        self.git('add', 'Project.swift')
        result = self.inspect('--module', 'account')
        module = result['modules'][0]
        self.assertEqual('changed', module['status'])
        self.assertIn('App/Account/Login.swift', module['changes']['committed'])
        self.assertIn('App/Account/Staged.swift', module['changes']['staged'])
        self.assertIn('App/Account/Login.swift', module['changes']['unstaged'])
        self.assertIn('App/Account/Untracked.swift', module['changes']['untracked'])
        self.assertIn('Project.swift', result['cross_cutting_changes']['staged'])
        self.assertTrue(module['expand_scope'])
        self.assertTrue(result['expand_scope'])
        self.assertIn('先读', self.run_tool('inspect', '--module', 'account').stdout)

    def test_configured_base_branch_and_unmatched_query(self):
        self.record_account()
        self.git('checkout', '-qb', 'develop')
        self.write('App/Home/Home.swift', 'final class Home { let v = 2 }\n')
        self.git('commit', '-qam', 'develop work')
        self.git('checkout', '-qb', 'feature')
        manifest = self.root / '.agents/project-modules.json'
        data = json.loads(manifest.read_text())
        data['base_branch'] = 'develop'
        manifest.write_text(json.dumps(data))
        result = self.inspect('--all')
        self.assertEqual('develop', result['base'])
        self.assertEqual(self.git('rev-parse', 'develop'), result['merge_base'])
        unmatched = self.inspect('--query', '完全未知功能')
        self.assertEqual([], unmatched['selected_modules'])
        self.assertTrue(unmatched['expand_scope'])
        data['base_branch'] = 'missing-branch'
        manifest.write_text(json.dumps(data))
        missing = self.run_tool('inspect', '--all', check=False)
        self.assertNotEqual(0, missing.returncode)
        self.assertIn('base_branch', missing.stderr)

    def test_legacy_baseline_is_rejected(self):
        self.record_account()
        manifest = self.root / '.agents/project-modules.json'
        data = json.loads(manifest.read_text())
        data['modules'][0]['baseline'] = 'f' * 40
        manifest.write_text(json.dumps(data))
        result = self.run_tool('validate', check=False)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('baseline', result.stderr)

    def test_record_rejects_unsafe_or_untracked_paths(self):
        unsafe = self.run_tool('record', '--name', 'bad', '--trigger', 'bad',
                               '--path', '../outside', check=False)
        self.assertNotEqual(0, unsafe.returncode)
        self.assertIn('越出项目目录', unsafe.stderr)
        untracked = self.run_tool('record', '--name', 'new', '--trigger', 'new',
                                  '--path', 'App/New', check=False)
        self.assertNotEqual(0, untracked.returncode)
        self.assertIn('Git 未跟踪', untracked.stderr)

    def test_deleted_module_path_invalidates_index(self):
        self.record_account()
        self.git('checkout', '-qb', 'feature')
        self.git('rm', '-q', 'App/Account/Login.swift')
        self.git('commit', '-qm', 'move account away')
        result = self.inspect('--module', 'account')
        module = result['modules'][0]
        self.assertEqual('invalid', module['status'])
        self.assertTrue(module['expand_scope'])
        self.assertIn('App/Account/Login.swift', module['changes']['committed'])
        validated = self.run_tool('validate', check=False)
        self.assertEqual(1, validated.returncode)


if __name__ == '__main__':
    unittest.main()
