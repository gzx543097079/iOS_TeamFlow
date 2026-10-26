"""用真实安装包验证升级：清单识别本地改动、移除旧文件，不触碰团队定制与项目数据。"""
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
from release_fixture import archive as release_archive
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
        cls.ios = read_zip(release_archive('ios'))
        cls.godot = read_zip(release_archive('godot'))
        cls.godot_ios = read_zip(release_archive('godot-ios'))

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

    def test_upgrade_preserves_and_reports_existing_permissions(self):
        self.install(self.ios)
        paths = {'.claude/settings.json': b'{"permissions":{"ask":["custom"]}}',
                 '.codex/rules/teamflow.rules': self.ios[package_release.CORE + '/assets/permissions/codex.rules']}
        for name, content in paths.items():
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        archive = self.newer(self.ios)
        preview = upgrade.upgrade(self.root, archive, dry_run=True)
        self.assertEqual(set(paths), set(preview['host_permissions']))
        self.assertIn('permissions --mode default --plan', upgrade.describe(preview, True))
        upgrade.upgrade(self.root, archive, force=True)
        for name, content in paths.items():
            self.assertEqual(content, (self.root / name).read_bytes())

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

    def test_upgrade_reports_legacy_check_layout(self):
        self.install(self.ios)
        package = self.newer(self.ios)
        self.assertNotIn('config_migration', upgrade.upgrade(self.root, package, force=True))
        (self.root / 'source.txt').write_text('x')
        (self.root / 'scripts/check_app.py').write_text("run(['xcodebuild', '-configuration', 'Release', 'build'])\n")
        (self.root / '.agents/project-checks.json').write_text(json.dumps({'schema_version': 2, 'profiles': {
            'change': {'inputs': ['source.txt', 'scripts/check_app.py'],
                       'checks': {'app': {'argv': ['python3', 'scripts/check_app.py']}}}}}))
        result = upgrade.upgrade(self.root, package, force=True)
        self.assertEqual('需处理', result['config_migration']['status'])
        brief = upgrade.describe(result)
        self.assertIn('验证配置待迁移', brief)
        self.assertIn('change 的检查 app 含 Release 构建', brief)

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

    def test_unsafe_packages_are_rejected(self):
        self.install(self.ios)
        unsafe = write_zip(self.packages / 'unsafe.zip', {**self.ios, '.agents/../outside.txt': b'x'})
        with self.assertRaisesRegex(ValueError, '不安全路径'):
            upgrade.upgrade(self.root, unsafe)
        broken = self.packages / 'broken.zip'
        broken.write_text('not a zip')
        with self.assertRaisesRegex(ValueError, '有效 ZIP'):
            upgrade.upgrade(self.root, broken)

    def test_install_seeds_ios_verification_assets_once(self):
        package = write_zip(self.packages / 'ios.zip', self.ios)
        preview = upgrade.install(self.root, package, mode='ios', dry_run=True)
        self.assertEqual('install', preview['kind'])
        self.assertIn('.agents/project-checks.json', preview['seeded'])
        result = upgrade.install(self.root, package, mode='ios')
        checks = self.root / '.agents/project-checks.json'
        tokens = self.root / '.agents/design-tokens.json'
        debug = self.root / 'scripts/check_debug.py'
        self.assertTrue(checks.is_file())
        self.assertTrue(tokens.is_file())
        self.assertTrue(debug.is_file())
        self.assertIn('design-tokens', checks.read_text())
        self.assertTrue((self.root / 'requirements').is_dir())
        self.assertTrue((self.root / 'scripts/teamflow.py').is_file())
        original = checks.read_text()
        checks.write_text('{"schema_version": 2, "profiles": {"custom": {}}}')
        debug.write_text('# custom\n')
        with self.assertRaisesRegex(ValueError, '已安装'):
            upgrade.install(self.root, package, mode='ios')
        upgrade.install(self.root, package, mode='ios', force=True)
        self.assertEqual('{"schema_version": 2, "profiles": {"custom": {}}}', checks.read_text())
        self.assertEqual('# custom\n', debug.read_text())
        self.assertNotEqual(original, checks.read_text())

    def test_install_teamflow_bootstrap_from_zip_root(self):
        package = release_archive('ios')
        with zipfile.ZipFile(package) as stream:
            self.assertIn('install_teamflow.py', stream.namelist())
            bootstrap = stream.read('install_teamflow.py')
        script = self.packages / 'install_teamflow.py'
        script.write_bytes(bootstrap)
        ran = subprocess.run([sys.executable, str(script), str(package), '--mode', 'ios',
                              '--project', str(self.root)], capture_output=True, text=True)
        self.assertEqual(0, ran.returncode, ran.stderr + ran.stdout)
        self.assertTrue((self.root / '.agents/project-checks.json').is_file())
        self.assertIn('已安装', ran.stdout)

    def test_install_seeds_godot_checks(self):
        package = write_zip(self.packages / 'godot.zip', self.godot)
        upgrade.install(self.root, package, mode='godot')
        config = json.loads((self.root / '.agents/project-checks.json').read_text())
        self.assertIn('godot-check', config['profiles'])
        self.assertFalse((self.root / '.agents/design-tokens.json').exists())


if __name__ == '__main__':
    unittest.main()
