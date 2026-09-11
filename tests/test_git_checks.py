import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.agents/skills/ios-team-flow/scripts'


def module(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


ranges = module('range_review')
hooks = module('install_git_checks')
gate = ranges.gate


class GitChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='teamflow git ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Test')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'commit.gpgsign', 'false')
        self.stage('base.txt', 'base')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD').strip()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True, stderr=subprocess.PIPE)

    def stage(self, name, content):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        self.git('add', '--', name)

    def complete(self, target):
        report = json.loads(target.read_text())
        report.update(reviewer='测试夹具', completed_at='2026-09-11T00:00:00Z', summary='仅用于行为测试')
        for v in report['checks'].values():
            v.update(status='不适用', evidence='临时测试，不是实际代码审查')
        target.write_text(json.dumps(report))

    def reviewed_commit(self, name='code.txt', content='change'):
        self.stage(name, content)
        self.complete(gate.prepare(self.root))
        self.git('add', 'logs/reviews')
        self.git('commit', '-qm', 'reviewed')
        return self.git('rev-parse', 'HEAD').strip()

    def test_empty_index_does_not_pass_unreviewed_range(self):
        self.stage('code.txt', 'unreviewed')
        self.git('commit', '-qm', 'not reviewed')
        self.assertFalse(self.git('diff', '--cached'))
        with self.assertRaises(ValueError):
            ranges.check(self.root, self.base, 'HEAD')

    def test_linear_reports_reused_independent_of_worktree(self):
        head = self.reviewed_commit()
        self.reviewed_commit('other.txt', 'more')
        self.stage('unrelated.txt', 'not part of head')
        ranges.check(self.root, self.base, 'HEAD')
        ranges.check(self.root, self.base, head)

    def test_range_receipt_commit_and_new_code_invalidates(self):
        self.stage('code.txt', 'range')
        self.git('commit', '-qm', 'unreviewed')
        target = ranges.prepare(self.root, self.base, 'HEAD')
        self.complete(target)
        self.git('add', 'logs/reviews')
        self.git('commit', '-qm', 'receipt only')
        ranges.check(self.root, self.base, 'HEAD')
        self.stage('code.txt', 'new content')
        self.git('commit', '-qm', 'new unreviewed')
        with self.assertRaises(ValueError):
            ranges.check(self.root, self.base, 'HEAD')

    def test_target_base_change_invalidates_range_report(self):
        self.stage('feature.txt', 'feature')
        self.git('commit', '-qm', 'feature')
        self.complete(ranges.prepare(self.root, self.base, 'HEAD'))
        self.git('add', 'logs/reviews')
        self.git('commit', '-qm', 'receipt')
        head = self.git('rev-parse', 'HEAD').strip()
        ranges.check(self.root, self.base, head)
        self.git('checkout', '-qb', 'new-target', self.base)
        self.stage('target.txt', 'base advanced')
        self.git('commit', '-qm', 'target changed')
        new_base = self.git('rev-parse', 'HEAD').strip()
        with self.assertRaises(ValueError):
            ranges.check(self.root, new_base, head)

    def test_pending_report_rejected_and_bad_ref_rejected(self):
        self.stage('code.txt', 'pending')
        gate.prepare(self.root)
        self.git('add', 'logs/reviews')
        self.git('commit', '-qm', 'pending')
        with self.assertRaises(ValueError):
            ranges.check(self.root, self.base, 'HEAD')
        with self.assertRaises(subprocess.CalledProcessError):
            ranges.check(self.root, 'nonexistent', 'HEAD')

    def test_binary_mode_and_receipt_boundary(self):
        self.reviewed_commit()
        binary = self.root / 'binary.bin'
        binary.write_bytes(b'\0\xff')
        self.git('add', 'binary.bin')
        self.complete(gate.prepare(self.root))
        self.git('add', 'logs/reviews')
        self.git('commit', '-qm', 'binary reviewed')
        ranges.check(self.root, self.base, 'HEAD')
        self.git('update-index', '--chmod=+x', 'code.txt')
        self.git('commit', '-qm', 'mode changed')
        with self.assertRaises(ValueError):
            ranges.check(self.root, self.base, 'HEAD')
        self.stage('logs/reviews/hidden.py', 'print(1)')
        self.git('commit', '-qm', 'hidden')
        with self.assertRaisesRegex(ValueError, '非回执'):
            ranges.check(self.root, self.base, 'HEAD')

    def test_merge_requires_range_review(self):
        branch = self.git('branch', '--show-current').strip()
        self.git('checkout', '-qb', 'feature')
        self.reviewed_commit('feature.txt', 'feature')
        self.git('checkout', branch)
        self.reviewed_commit('main.txt', 'main')
        self.git('merge', '--no-ff', '-m', 'merge', 'feature')
        with self.assertRaisesRegex(ValueError, '合并提交'):
            ranges.check(self.root, self.base, 'HEAD')
        self.complete(ranges.prepare(self.root, self.base, 'HEAD'))
        self.git('add', 'logs/reviews')
        self.git('commit', '-qm', 'range receipt')
        ranges.check(self.root, self.base, 'HEAD')

    def test_trusted_checker_ignores_head_python(self):
        self.stage('review_gate.py', "print('FORGED PASS')\n")
        self.git('commit', '-qm', 'unreviewed malicious module')
        trusted = self.root / 'trusted'
        trusted.mkdir()
        for name in ('review_gate.py', 'range_review.py'):
            shutil.copyfile(SCRIPTS / name, trusted / name)
        result = subprocess.run([sys.executable, '-I', str(trusted / 'range_review.py'), 'check',
                                 '--base', self.base, '--head', 'HEAD'], cwd=self.root, capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn('FORGED PASS', result.stdout)

    def install_skill_gate(self):
        dest = self.root / '.agents/skills/ios-team-flow/scripts'
        dest.mkdir(parents=True)
        shutil.copyfile(SCRIPTS / 'review_gate.py', dest / 'review_gate.py')

    def test_real_commit_hook_blocks_then_passes(self):
        self.install_skill_gate()
        hooks.install_hook(self.root)
        hooks.install_hook(self.root)
        self.stage('code.txt', 'needs review')
        with self.assertRaises(subprocess.CalledProcessError):
            self.git('commit', '-qm', 'blocked')
        self.complete(gate.prepare(self.root))
        self.git('add', 'logs/reviews')
        self.git('commit', '-qm', 'passed')
        hooks.uninstall_hook(self.root)
        self.assertFalse((self.root / '.git/hooks/pre-commit').exists())

    def test_existing_hook_exit_preserved_and_restored(self):
        self.install_skill_gate()
        target = self.root / '.git/hooks/pre-commit'
        original = '#!/bin/sh\nprintf called > original-ran\nexit 7\n'
        target.write_text(original)
        target.chmod(0o755)
        hooks.install_hook(self.root)
        self.stage('code.txt', 'x')
        with self.assertRaises(subprocess.CalledProcessError):
            self.git('commit', '-qm', 'blocked by original')
        self.assertEqual('called', (self.root / 'original-ran').read_text())
        hooks.uninstall_hook(self.root)
        self.assertEqual(original, target.read_text())
        self.assertTrue(os.access(target, os.X_OK))

    def test_custom_hooks_path_and_conflict_protection(self):
        self.git('config', 'core.hooksPath', '.custom-hooks')
        hooks.install_hook(self.root)
        target = self.root / '.custom-hooks/pre-commit'
        self.assertTrue(target.exists())
        target.write_text(target.read_text() + '# changed\n')
        with self.assertRaises(ValueError):
            hooks.uninstall_hook(self.root)
        with self.assertRaises(ValueError):
            hooks.install_hook(self.root)
        self.git('config', 'core.hooksPath', str(self.root.parent / 'shared-hooks'))
        with self.assertRaises(ValueError):
            hooks.install_hook(self.root)

    def test_ci_install_idempotent_and_no_overwrite(self):
        hooks.install_ci(self.root)
        target = self.root / '.github/workflows/teamflow-pr-review.yml'
        original = target.read_bytes()
        hooks.install_ci(self.root)
        self.assertEqual(original, target.read_bytes())
        target.write_text('team config')
        with self.assertRaises(ValueError):
            hooks.install_ci(self.root)
        self.assertEqual('team config', target.read_text())
