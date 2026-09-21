import importlib.util
import json
import os
import shutil
import subprocess
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


hooks = module('install_git_checks')
gate = module('review_gate')


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
        for value in report['checks'].values():
            value.update(status='不适用', evidence='临时测试，不是实际代码审查')
        target.write_text(json.dumps(report))

    def install_skill_gate(self):
        destination = self.root / '.agents/skills/ios-team-flow/scripts'
        destination.mkdir(parents=True)
        shutil.copyfile(SCRIPTS / 'review_gate.py', destination / 'review_gate.py')

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
