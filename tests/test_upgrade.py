"""用真实安装包验证升级：清单识别本地改动、移除旧文件、兼容 5.x 布局，不触碰团队定制与项目数据。"""
import json
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
sys.path.insert(0, str(ROOT / '.agents/teamflow-core/scripts'))
import package_release
import upgrade

WORKFLOW = '.agents/teamflow-core/references/WORKFLOW.md'
OBSOLETE = '.agents/teamflow-core/references/LOCALIZATION.md'
ADDED = '.agents/teamflow-core/references/ADDED.md'
VERSION = '.agents/teamflow-core/references/VERSION'


def read_zip(path):
    with zipfile.ZipFile(path) as stream:
        return {name: stream.read(name) for name in stream.namelist()}


def write_zip(path, files):
    with zipfile.ZipFile(path, 'w') as stream:
        for name, data in files.items():
            stream.writestr(name, data)
    return path


class UpgradeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ios = read_zip(package_release.package_skill(ROOT))
        cls.godot = read_zip(package_release.package_godot(ROOT))
        cls.godot_ios = read_zip(package_release.package_godot_ios(ROOT))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name).resolve()
        self.root = base / 'project'
        self.root.mkdir()
        self.packages = base / 'packages'
        self.packages.mkdir()
        subprocess.run(['git', '-C', str(self.root), 'init', '-q'], check=True)

    def install(self, files):
        for name, data in files.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

    def newer(self, files, version='9.0.0', name='new.zip'):
        files = dict(files)
        files[VERSION] = (version + '\n').encode()
        files[WORKFLOW] = files[WORKFLOW] + '\n新版规则。\n'.encode()
        files.pop(OBSOLETE)
        files[ADDED] = '# 新增\n'.encode()
        return write_zip(self.packages / name, files)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(self.root / 'scripts/teamflow.py'), '--project', str(self.root),
                               *args], capture_output=True, text=True)

    def test_upgrade_replaces_managed_files_and_keeps_team_data(self):
        self.install(self.ios)
        team = self.root / '.agents/team/RULES.md'
        team.parent.mkdir(parents=True)
        team.write_text('团队规则\n')
        (self.root / 'AGENTS.md').write_text('# 项目约定\n\n' + (self.root / 'AGENTS.md').read_text())
        card = self.root / 'requirements/REQ-20260101-a3f9.md'
        card.parent.mkdir()
        card.write_text('卡片\n')
        package = self.newer(self.ios)
        preview = self.cli('upgrade', str(package), '--plan')
        self.assertEqual(0, preview.returncode, preview.stderr)
        self.assertIn('+ ' + ADDED, preview.stdout)
        self.assertIn('- ' + OBSOLETE, preview.stdout)
        self.assertNotEqual('9.0.0', (self.root / VERSION).read_text().strip())
        result = self.cli('upgrade', str(package), '--json')
        self.assertEqual(0, result.returncode, result.stderr)
        actions = json.loads(result.stdout)['actions']
        self.assertEqual([OBSOLETE], actions['remove'])
        self.assertIn(WORKFLOW, actions['update'])
        self.assertEqual('9.0.0', (self.root / VERSION).read_text().strip())
        self.assertFalse((self.root / OBSOLETE).exists())
        self.assertTrue((self.root / ADDED).is_file())
        self.assertEqual('团队规则\n', team.read_text())
        self.assertEqual('卡片\n', card.read_text())
        self.assertTrue((self.root / 'AGENTS.md').read_text().startswith('# 项目约定\n'))
        manifest = json.loads((self.root / upgrade.MANIFEST).read_text())
        self.assertEqual('9.0.0', manifest['version'])
        self.assertIn(ADDED, manifest['files'])
        doctor = json.loads(self.cli('doctor', '--json').stdout)
        entry = next(item for item in doctor['checks'] if item['item'] == 'Skill 与入口')
        self.assertEqual('就绪', entry['status'])
        self.assertIn('9.0.0', entry['detail'])

    def test_local_changes_block_upgrade_until_forced(self):
        self.install(self.ios)
        (self.root / WORKFLOW).write_text('团队直接改过的规则\n')
        package = self.newer(self.ios)
        preview = upgrade.upgrade(self.root, package, dry_run=True)
        self.assertTrue(preview['blocked'])
        self.assertEqual([WORKFLOW], preview['actions']['conflict'])
        with self.assertRaisesRegex(ValueError, 'WORKFLOW.md'):
            upgrade.upgrade(self.root, package)
        self.assertEqual('团队直接改过的规则\n', (self.root / WORKFLOW).read_text())
        self.assertTrue((self.root / OBSOLETE).exists())
        result = upgrade.upgrade(self.root, package, force=True)
        self.assertIn(WORKFLOW, result['actions']['conflict'])
        self.assertIn('新版规则', (self.root / WORKFLOW).read_text())

    def test_legacy_layout_without_manifest_uses_baseline_package(self):
        # 5.x 安装包解压到 .agents/，没有安装清单。
        legacy = {name[len('.agents/'):]: data for name, data in self.ios.items()
                  if name.startswith('.agents/') and name != upgrade.MANIFEST}
        legacy['teamflow-core/references/VERSION'] = b'5.0.3\n'
        old = write_zip(self.packages / 'old.zip', legacy)
        with zipfile.ZipFile(old) as stream:
            stream.extractall(self.root / '.agents')
        (self.root / 'AGENTS.md').write_bytes(self.ios['AGENTS.md'])
        package = write_zip(self.packages / 'new.zip', self.ios)
        with self.assertRaisesRegex(ValueError, '--baseline'):
            upgrade.upgrade(self.root, package)
        result = upgrade.upgrade(self.root, package, baseline_zip=old)
        self.assertEqual('5.0.3', result['from'])
        self.assertFalse(result['actions']['conflict'])
        self.assertTrue((self.root / upgrade.MANIFEST).is_file())

    def test_package_must_cover_installed_mode_and_only_mode_files_install(self):
        self.install(self.ios)
        with self.assertRaisesRegex(ValueError, '不含当前模式'):
            upgrade.upgrade(self.root, self.newer(self.godot, name='godot.zip'))
        upgrade.upgrade(self.root, self.newer(self.godot_ios, name='godot-ios.zip'))
        self.assertFalse((self.root / package_release.GODOT_SKILL).exists())
        self.assertEqual('ios', json.loads((self.root / upgrade.MANIFEST).read_text())['package'])

    def test_mode_switch_adds_and_removes_platform_skill(self):
        self.install(self.godot)
        package = write_zip(self.packages / 'godot-ios.zip', self.godot_ios)
        result = self.cli('upgrade', str(package), '--mode', 'godot-ios')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue((self.root / package_release.SKILL / 'SKILL.md').is_file())
        self.assertEqual('godot-ios', upgrade.setup_project.install_mode(self.root))
        upgrade.upgrade(self.root, package, mode='godot')
        self.assertFalse((self.root / package_release.SKILL).exists())
        self.assertEqual('godot', upgrade.setup_project.install_mode(self.root))

    def test_downgrade_and_unsafe_packages_are_rejected(self):
        self.install(self.ios)
        older = write_zip(self.packages / 'older.zip', {**self.ios, VERSION: b'1.0.0\n'})
        with self.assertRaisesRegex(ValueError, '降级'):
            upgrade.upgrade(self.root, older)
        unsafe = write_zip(self.packages / 'unsafe.zip', {**self.ios, '.agents/../outside.txt': b'x'})
        with self.assertRaisesRegex(ValueError, '不安全路径'):
            upgrade.upgrade(self.root, unsafe)
        broken = self.packages / 'broken.zip'
        broken.write_text('not a zip')
        with self.assertRaisesRegex(ValueError, '有效 ZIP'):
            upgrade.upgrade(self.root, broken)


if __name__ == '__main__':
    unittest.main()
