"""团队协作能力：纯 Godot 模式、团队规则入口、引擎版本锁定、游戏缓存忽略与本机提交前检查。"""
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / '.agents/teamflow-core/scripts'))
import package_release
import setup_project

spec = importlib.util.spec_from_file_location('verify_godot_team', ROOT / package_release.GODOT_SKILL / 'scripts/verify_godot.py')
verify_godot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_godot)


class TeamTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')

    def git(self, *args, check=True):
        return subprocess.run(['git', '-C', str(self.root), *args], check=check, capture_output=True, text=True)

    def extract(self, archive):
        with zipfile.ZipFile(archive) as stream:
            stream.extractall(self.root)
            return stream.namelist()

    def cli(self, *args):
        return subprocess.run([sys.executable, str(self.root / 'scripts/teamflow.py'), '--project', str(self.root),
                               *args], capture_output=True, text=True)

    def item(self, name):
        return next((i for i in setup_project.diagnose(self.root)['checks'] if i['item'] == name), None)

    def test_godot_only_package_and_mode(self):
        names = self.extract(package_release.package_godot(ROOT))
        self.assertFalse(any(name.startswith('.agents/skills/iOS/') for name in names))
        content = (self.root / 'AGENTS.md').read_text()
        self.assertIn(setup_project.GODOT_ONLY_MARK, content)
        self.assertEqual('godot', setup_project.install_mode(self.root))
        self.assertEqual('就绪', self.item('Skill 与入口')['status'])
        self.assertIn('Godot，', self.item('Skill 与入口')['detail'])
        # 纯 Godot 包内只有指向 iOS Skill 的链接允许悬空，它们只在 Godot + iOS 模式使用。
        for md in (self.root / '.agents').rglob('*.md'):
            if md.name == 'requirement.md':
                continue
            for link in re.findall(r'\]\(([^)]+)\)', md.read_text()):
                if '://' in link or link.startswith('#'):
                    continue
                target = (md.parent / link.split('#')[0]).resolve()
                if not target.exists():
                    self.assertTrue(target.is_relative_to(self.root / '.agents/skills/iOS'), f'{md}: {link}')
        result = self.cli('setup')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('已接入 Godot：', result.stdout)
        self.assertIn('.godot/', (self.root / '.gitignore').read_text().splitlines())
        before = (self.root / 'AGENTS.md').read_bytes()
        failed = self.cli('setup', '--mode', 'godot-ios')
        self.assertNotEqual(0, failed.returncode)
        self.assertIn('iOS 平台依赖不完整', failed.stderr)
        self.assertEqual(before, (self.root / 'AGENTS.md').read_bytes())

    def test_three_modes_switch_with_shared_godot_link_and_team_rules(self):
        self.extract(package_release.package_godot_ios(ROOT))
        core = self.root / package_release.CORE
        setup_project.setup(self.root, core, mode='godot', claude_link=True)
        link = self.root / '.claude/skills/godot'
        self.assertTrue(link.is_symlink())
        for mode in ('godot-ios', 'godot', 'ios', 'godot-ios'):
            setup_project.setup(self.root, core, mode=mode)
            self.assertEqual(mode, setup_project.install_mode(self.root))
            content = (self.root / 'AGENTS.md').read_text()
            self.assertEqual(1, content.count(setup_project.TEAM_RULES))
            self.assertEqual(mode != 'ios', link.is_symlink())
            self.assertEqual(mode == 'ios', (self.root / '.claude/skills/ios').is_symlink())
            snapshot = (self.root / 'AGENTS.md').read_bytes()
            setup_project.setup(self.root, core)
            self.assertEqual(snapshot, (self.root / 'AGENTS.md').read_bytes())

    def test_godot_version_lock_and_cache_ignore(self):
        self.extract(package_release.package_godot(ROOT))
        game = self.root / 'game'
        game.mkdir()
        (game / 'project.godot').write_text('config_version=5\n')
        self.assertEqual('提示', self.item('Godot 版本锁定')['status'])
        self.assertEqual('需处理', self.item('Godot 缓存忽略')['status'])
        self.assertIn('game', self.item('Godot 缓存忽略')['detail'])
        (game / '.gitignore').write_text('.godot/\n')
        self.assertEqual('就绪', self.item('Godot 缓存忽略')['status'])
        toolchain = self.root / setup_project.TOOLCHAIN
        toolchain.parent.mkdir(parents=True)
        toolchain.write_text('{"godot": "latest"}')
        self.assertEqual('需处理', self.item('Godot 版本锁定')['status'])
        toolchain.write_text('{"godot": "4.7.2"}')
        with patch.object(setup_project, 'godot_version', return_value='4.7.2.stable.official.abc'):
            self.assertEqual('就绪', self.item('Godot 版本锁定')['status'])
        with patch.object(setup_project, 'godot_version', return_value='4.7.1.stable.official.abc'):
            item = self.item('Godot 版本锁定')
            self.assertEqual('需处理', item['status'])
            self.assertIn('4.7.1', item['detail'])
        with patch.object(setup_project, 'godot_version', side_effect=ValueError('未找到 Godot')):
            self.assertEqual('需处理', self.item('Godot 版本锁定')['status'])
        # 检查脚本未显式传版本时沿用团队锁定，显式参数优先。
        self.assertEqual('4.7.2', verify_godot.pinned_version(game))
        with self.assertRaisesRegex(ValueError, '不匹配'):
            verify_godot.check_version('4.7.1.stable.official', verify_godot.pinned_version(game))

    def test_native_mode_skips_godot_checks(self):
        self.extract(package_release.package_skill(ROOT))
        self.assertIsNone(self.item('Godot 版本锁定'))
        self.assertIsNone(self.item('Godot 缓存忽略'))

    def test_xcode_lock_is_checked_only_when_pinned(self):
        self.extract(package_release.package_skill(ROOT))
        self.assertIsNone(self.item('Xcode 版本锁定'))
        toolchain = self.root / setup_project.TOOLCHAIN
        toolchain.parent.mkdir(parents=True)
        toolchain.write_text('{"xcode": "16.4"}')
        with patch.object(setup_project, 'xcode_version', return_value='16.4'):
            self.assertEqual('就绪', self.item('Xcode 版本锁定')['status'])
        with patch.object(setup_project, 'xcode_version', return_value='16.3'):
            item = self.item('Xcode 版本锁定')
            self.assertEqual('需处理', item['status'])
            self.assertIn('16.3', item['detail'])
        toolchain.write_text('{"xcode": "latest"}')
        with self.assertRaisesRegex(ValueError, 'xcode 须为'):
            setup_project.toolchain(self.root)

    def configure(self, code):
        (self.root / 'source.txt').write_text('source')
        config = {'schema_version': 2, 'profiles': {'quick': {'inputs': ['source.txt'],
                  'checks': {'unit': {'argv': [sys.executable, '-c', code]}}}}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))

    def test_pre_commit_hook_reuses_evidence_and_is_opt_in(self):
        self.extract(package_release.package_skill(ROOT))
        hook = Path(self.git('rev-parse', '--git-path', 'hooks/pre-commit').stdout.strip())
        hook = hook if hook.is_absolute() else self.root / hook
        self.configure('raise SystemExit(1)')
        self.assertEqual(0, self.cli('setup').returncode)
        self.assertFalse(hook.exists())
        missing = self.cli('setup', '--git-hook', 'absent')
        self.assertIn('未配置所选 profile', missing.stderr)
        self.assertFalse(hook.exists())
        self.assertNotEqual(0, self.cli('setup', '--git-hook', "x';rm").returncode)
        preview = self.cli('setup', '--git-hook', 'quick', '--plan')
        self.assertIn('git hook --profile', preview.stdout)
        self.assertFalse(hook.exists())
        result = self.cli('setup', '--git-hook', 'quick')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(hook.stat().st_mode & 0o100)
        self.git('add', 'source.txt')
        self.assertNotEqual(0, self.git('commit', '-qm', 'blocked', check=False).returncode)
        self.assertFalse(list((self.root / 'logs/project-checks').glob('*/result.json')))
        self.configure('pass')
        req = json.loads(self.cli('req', 'create', '--title', 'hook proof', '--json').stdout)['requirement']
        card = self.root / 'requirements' / (req + '.md')
        card.write_text(card.read_text().replace('〈填写本次要达到的结果〉', '验证提交')
                        .replace('〈填写可观察的输入、操作和预期结果〉', '提交复用证据'))
        done = self.cli('req', 'complete', req, '--profile', 'quick', '--confirm-ac', 'AC-01')
        self.assertEqual(0, done.returncode, done.stderr)
        self.git('add', 'source.txt', '.agents/project-checks.json', str(card.relative_to(self.root)))
        committed = self.git('commit', '-qm', 'allowed', check=False)
        self.assertEqual(1, len(list((self.root / 'logs/project-checks').glob('*/result.json'))))
        self.assertEqual(0, committed.returncode, committed.stdout + committed.stderr)
        self.assertEqual('就绪', self.item('提交前检查')['status'])
        hook.write_text(hook.read_text().replace('git hook', 'verify run'))
        self.assertEqual('需处理', self.item('提交前检查')['status'])
        self.assertEqual(0, self.cli('setup', '--git-hook', 'quick').returncode)
        self.assertIn('git hook', hook.read_text())
        (self.root / '.agents/project-checks.json').write_text('{"schema_version": 2, "profiles": {}}')
        self.assertEqual('需处理', self.item('提交前检查')['status'])
        self.assertEqual(0, self.cli('setup', '--no-git-hook').returncode)
        self.assertFalse(hook.exists())
        self.assertIsNone(self.item('提交前检查'))

    def test_hook_refuses_foreign_hook_and_shared_hooks_path(self):
        self.extract(package_release.package_skill(ROOT))
        self.configure('pass')
        hook = Path(self.git('rev-parse', '--git-path', 'hooks/pre-commit').stdout.strip())
        hook = hook if hook.is_absolute() else self.root / hook
        hook.parent.mkdir(parents=True, exist_ok=True)
        hook.write_text('#!/bin/sh\nexit 0\n')
        for args in (('--git-hook', 'quick'), ('--no-git-hook',)):
            result = self.cli('setup', *args)
            self.assertIn('非 TeamFlow 管理', result.stderr)
        self.assertEqual('#!/bin/sh\nexit 0\n', hook.read_text())
        with tempfile.TemporaryDirectory() as shared:
            self.git('config', 'core.hooksPath', shared)
            self.assertIn('项目外', self.cli('setup', '--git-hook', 'quick').stderr)
            self.assertEqual([], list(Path(shared).iterdir()))
        self.git('config', 'core.hooksPath', '.githooks')
        self.assertEqual(0, self.cli('setup', '--git-hook', 'quick').returncode)
        self.assertIn(setup_project.HOOK_MARK, (self.root / '.githooks/pre-commit').read_text())


if __name__ == '__main__':
    unittest.main()
