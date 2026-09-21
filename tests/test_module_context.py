import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / '.agents/skills/ios-team-flow/scripts/module_context.py'


class ModuleContextTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
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
        return subprocess.run([sys.executable, str(TOOL), '--project', str(self.root), *args],
                              check=check, capture_output=True, text=True)

    def record_account(self):
        result = self.run_tool(
            'record', '--name', 'account', '--responsibility', '登录与会话',
            '--trigger', '登录', '--trigger', 'account', '--path', 'App/Account',
            '--entry', 'Login', '--dependency', 'SessionStore', '--caller', 'AppRouter',
            '--verification', 'ios-account', '--cross-cutting', 'Project.swift')
        return json.loads(result.stdout)

    def test_record_and_query_unchanged_module(self):
        recorded = self.record_account()['recorded']
        self.assertEqual(self.git('rev-parse', 'HEAD'), recorded['baseline'])
        result = json.loads(self.run_tool('inspect', '--query', '修改登录错误提示').stdout)
        self.assertEqual(['account'], result['selected_modules'])
        self.assertFalse(result['expand_scope'])
        module = result['modules'][0]
        self.assertEqual('unchanged', module['status'])
        self.assertEqual(['Login'], module['entry_symbols'])
        self.assertEqual([], module['suggested_read_files'])

    def test_reports_committed_staged_unstaged_untracked_and_cross_cutting(self):
        self.record_account()
        self.git('add', '.agents/project-modules.json')
        self.git('commit', '-qm', 'module index')
        self.write('App/Account/Login.swift', 'final class Login { let committed = true }\n')
        self.git('add', 'App/Account/Login.swift')
        self.git('commit', '-qm', 'account change')
        self.write('App/Account/Staged.swift', 'let staged = true\n')
        self.git('add', 'App/Account/Staged.swift')
        self.write('App/Account/Login.swift', 'final class Login { let unstaged = true }\n')
        self.write('App/Account/Untracked.swift', 'let untracked = true\n')
        self.write('Project.swift', 'let targets = ["Account"]\n')
        self.git('add', 'Project.swift')
        result = json.loads(self.run_tool('inspect', '--module', 'account').stdout)
        module = result['modules'][0]
        self.assertEqual('changed', module['status'])
        self.assertIn('App/Account/Login.swift', module['changes']['committed'])
        self.assertIn('App/Account/Staged.swift', module['changes']['staged'])
        self.assertIn('App/Account/Login.swift', module['changes']['unstaged'])
        self.assertIn('App/Account/Untracked.swift', module['changes']['untracked'])
        self.assertIn('Project.swift', module['cross_cutting_changes']['staged'])
        self.assertTrue(module['expand_scope'])
        self.assertTrue(result['expand_scope'])

    def test_unmatched_query_and_invalid_baseline_expand_scope(self):
        self.record_account()
        unmatched = json.loads(self.run_tool('inspect', '--query', '完全未知功能').stdout)
        self.assertEqual([], unmatched['selected_modules'])
        self.assertTrue(unmatched['expand_scope'])
        manifest = self.root / '.agents/project-modules.json'
        data = json.loads(manifest.read_text())
        data['modules'][0]['baseline'] = 'f' * 40
        manifest.write_text(json.dumps(data))
        invalid = json.loads(self.run_tool('inspect', '--module', 'account').stdout)
        self.assertEqual('invalid', invalid['modules'][0]['status'])
        self.assertTrue(invalid['expand_scope'])
        validated = self.run_tool('validate', check=False)
        self.assertNotEqual(0, validated.returncode)

    def test_record_rejects_unsafe_or_dirty_paths(self):
        unsafe = self.run_tool('record', '--name', 'bad', '--trigger', 'bad',
                               '--path', '../outside', check=False)
        self.assertNotEqual(0, unsafe.returncode)
        self.assertIn('越出项目目录', unsafe.stderr)
        self.write('App/Account/Login.swift', 'dirty\n')
        dirty = self.run_tool('record', '--name', 'account', '--trigger', '登录',
                              '--path', 'App/Account', check=False)
        self.assertNotEqual(0, dirty.returncode)
        self.assertIn('未提交变化', dirty.stderr)

    def test_deleted_module_path_invalidates_index_and_reports_deletion(self):
        self.record_account()
        self.git('add', '.agents/project-modules.json')
        self.git('commit', '-qm', 'module index')
        self.git('rm', 'App/Account/Login.swift')
        self.git('commit', '-qm', 'move account away')
        result = json.loads(self.run_tool('inspect', '--module', 'account').stdout)
        module = result['modules'][0]
        self.assertEqual('invalid', module['status'])
        self.assertTrue(module['expand_scope'])
        self.assertIn('App/Account/Login.swift', module['changes']['committed'])
        self.assertIn('App/Account/Login.swift', module['suggested_read_files'])

    def test_refresh_requires_explicit_confirmation_and_clean_paths(self):
        self.record_account()
        self.git('add', '.agents/project-modules.json')
        self.git('commit', '-qm', 'module index')
        self.write('App/Account/Login.swift', 'changed\n')
        missing = self.run_tool('refresh', '--module', 'account', check=False)
        self.assertNotEqual(0, missing.returncode)
        self.assertIn('--accept-reviewed-changes', missing.stderr)
        dirty = self.run_tool('refresh', '--module', 'account',
                              '--accept-reviewed-changes', check=False)
        self.assertNotEqual(0, dirty.returncode)
        self.assertIn('未提交变化', dirty.stderr)
        self.git('add', 'App/Account/Login.swift')
        self.git('commit', '-qm', 'reviewed account change')
        refreshed = json.loads(self.run_tool('refresh', '--module', 'account',
                                             '--accept-reviewed-changes').stdout)
        self.assertEqual(self.git('rev-parse', 'HEAD'), refreshed['refreshed']['baseline'])
        inspected = json.loads(self.run_tool('inspect', '--module', 'account').stdout)
        self.assertEqual('unchanged', inspected['modules'][0]['status'])


if __name__ == '__main__':
    unittest.main()
