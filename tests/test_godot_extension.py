"""验证扩展包真实接入及 Godot 检查错误边界；引擎场景由独立 profile 实际运行。"""
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

spec = importlib.util.spec_from_file_location('verify_godot', ROOT / package_release.GODOT_SKILL / 'scripts/verify_godot.py')
verify_godot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verify_godot)


class GodotExtensionTests(unittest.TestCase):
    def test_bundle_is_dependency_complete_and_repeatable(self):
        archive = package_release.package_godot_ios(ROOT)
        with tempfile.TemporaryDirectory(dir=ROOT / 'build' if (ROOT / 'build').is_dir() else ROOT) as directory:
            project = Path(directory)
            with zipfile.ZipFile(archive) as stream:
                names = stream.namelist()
                self.assertTrue(all(n.startswith(('.agents/teamflow-core/', '.agents/skills/iOS/', '.agents/skills/Godot/'))
                                    or n in ('AGENTS.md', 'scripts/teamflow.py', *package_release.PERMISSIONS) for n in names))
                stream.extractall(project)
            skills = project / '.agents/skills'
            for md in (project / '.agents').rglob('*.md'):
                if md.name == 'requirement.md':
                    continue  # 此模板按使用项目 requirements/ 校验。
                for link in re.findall(r'\]\(([^)]+)\)', md.read_text()):
                    if '://' not in link and not link.startswith('#'):
                        self.assertTrue((md.parent / link.split('#')[0]).exists(), str(md) + ': ' + link)
            (project / 'AGENTS.md').write_text('# 项目约定\n保持既有游戏目录。\n')
            subprocess.run(['git', '-C', str(project), 'init', '-q'], check=True)
            setup = [sys.executable, str(project / '.agents/teamflow-core/scripts/teamflow.py'), '--project', str(project), 'setup', '--mode', 'godot-ios']
            for _ in range(2):
                result = subprocess.run(setup, capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual('', subprocess.run(setup + ['--plan'], check=True, capture_output=True, text=True).stdout)
            content = (project / 'AGENTS.md').read_text()
            self.assertIn('保持既有游戏目录。', content)
            self.assertIn('Godot/SKILL.md', content)
            self.assertEqual(1, content.count('<!-- teamflow:start -->'))
            cli = [sys.executable, str(project / 'scripts/teamflow.py'), '--project', str(project)]
            report = subprocess.run(cli + ['doctor', '--json'], capture_output=True, text=True)
            entrance = next(i for i in json.loads(report.stdout)['checks'] if i['item'] == 'Skill 与入口')
            self.assertEqual('就绪', entrance['status'])
            created = subprocess.run(cli + ['req', 'create', '--title', '游戏暂停', '--json'], check=True, capture_output=True, text=True)
            requirement = json.loads(created.stdout)['requirement']
            self.assertRegex(requirement, r'^REQ-\d{8}-[0-9a-f]{4}$')
            self.assertTrue((project / 'requirements' / (requirement + '.md')).is_file())
            helper = skills / 'Godot/scripts/verify_godot.py'
            help_result = subprocess.run([sys.executable, str(helper), '--help'], capture_output=True)
            self.assertEqual(0, help_result.returncode)

    def test_missing_tests_do_not_run_engine(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / 'project.godot').write_text('config_version=5\n')
            with patch.object(verify_godot.subprocess, 'run') as run:
                with self.assertRaisesRegex(ValueError, '必须提供真实'):
                    verify_godot.verify(project)
                with self.assertRaisesRegex(ValueError, '缺少项目文件'):
                    verify_godot.verify(project, test_script='tests/missing.gd')
                with self.assertRaisesRegex(ValueError, '相对游戏根'):
                    verify_godot.verify(project, test_script='../outside.gd')
                run.assert_not_called()

    def test_install_modes_persist_and_switch_without_deleting_user_files(self):
        import setup_project
        archive = package_release.package_godot_ios(ROOT)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            with zipfile.ZipFile(archive) as stream:
                stream.extractall(project)
            skill = project / package_release.CORE
            (project / 'AGENTS.md').unlink()
            # 扩展目录存在不自动激活游戏；首次无参数保持原生入口。
            setup_project.setup(project, skill)
            self.assertEqual('ios', setup_project.install_mode(project))
            self.assertNotIn('Godot/SKILL.md', (project / 'AGENTS.md').read_text())
            setup_project.setup(project, skill, mode='godot-ios', claude_link=True)
            godot_link = project / '.claude/skills/godot'
            native_link = project / '.claude/skills/ios'
            self.assertTrue(godot_link.is_symlink())
            self.assertFalse(native_link.exists())
            snapshot = (project / 'AGENTS.md').read_bytes()
            setup_project.setup(project, skill)
            self.assertEqual(snapshot, (project / 'AGENTS.md').read_bytes())
            report = setup_project.diagnose(project)
            entry = next(i for i in report['checks'] if i['item'] == 'Skill 与入口')
            self.assertEqual('就绪', entry['status'])
            self.assertIn('Godot + iOS', entry['detail'])
            # 预览不写入口也不切换受管理链接。
            setup_project.setup(project, skill, mode='ios', dry_run=True)
            self.assertEqual(snapshot, (project / 'AGENTS.md').read_bytes())
            self.assertTrue(godot_link.is_symlink())
            setup_project.setup(project, skill, mode='ios')
            self.assertTrue(native_link.is_symlink())
            self.assertFalse(godot_link.is_symlink())
            # 与标准链接不同的自有文件保留；目标冲突在写入口前失败。
            godot_link.mkdir()
            (godot_link / 'custom.txt').write_text('user-owned')
            setup_project.setup(project, skill, mode='ios')
            with self.assertRaisesRegex(ValueError, '已存在'):
                setup_project.setup(project, skill, mode='godot-ios', claude_link=True)
            self.assertEqual('ios', setup_project.install_mode(project))
            self.assertEqual('user-owned', (godot_link / 'custom.txt').read_text())

    def test_both_modes_write_reading_rules_and_rerun_is_stable(self):
        import setup_project
        archive = package_release.package_godot_ios(ROOT)
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            with zipfile.ZipFile(archive) as stream:
                stream.extractall(project)
            skill = project / package_release.CORE
            agents = project / 'AGENTS.md'
            # 模拟 5.0.0 托管区块：重新 setup 应补齐读取约束并保留自有说明。
            old_block = '\n'.join(line for line in setup_project.BLOCK.splitlines() if line != setup_project.READING_RULES) + '\n'
            agents.write_text('# 自有说明\n\n' + old_block + '\n自有结尾\n')
            for mode, entry in (('ios', 'skills/iOS/SKILL.md'), ('godot-ios', 'skills/Godot/SKILL.md')):
                setup_project.setup(project, skill, mode=mode)
                content = agents.read_text()
                block = content[content.index(setup_project.START):content.index(setup_project.END)]
                self.assertIn(entry, block)
                self.assertEqual(1, block.count(setup_project.READING_RULES))
                self.assertEqual(1, content.count(setup_project.START))
                self.assertTrue(content.startswith('# 自有说明\n'))
                self.assertIn('自有结尾', content)
                self.assertEqual(mode, setup_project.install_mode(project))
                snapshot = agents.read_bytes()
                setup_project.setup(project, skill)
                self.assertEqual(snapshot, agents.read_bytes())
                self.assertEqual(snapshot, setup_project.plan(project, skill)['AGENTS.md'])

    def test_native_install_ignores_incomplete_extension_and_game_install_fails_before_write(self):
        import setup_project
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            skill = project / package_release.CORE
            skill.mkdir(parents=True)
            (skill / 'scripts').mkdir()
            (skill / 'scripts/teamflow.py').write_text('core')
            native = project / package_release.SKILL
            native.mkdir(parents=True)
            (native / 'SKILL.md').write_text('native')
            (skill / 'references').mkdir()
            (skill / 'references/VERSION').write_text('4.0.1')
            (project / package_release.GODOT_SKILL).mkdir()
            setup_project.setup(project, skill, mode='ios')
            original = (project / 'AGENTS.md').read_bytes()
            with self.assertRaisesRegex(ValueError, '扩展不完整'):
                setup_project.setup(project, skill, mode='godot-ios')
            self.assertEqual(original, (project / 'AGENTS.md').read_bytes())
            self.assertEqual('ios', setup_project.install_mode(project))

    def test_engine_version_follows_project_features(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / 'project.godot').write_text('config_version=5\n')
            self.assertIsNone(verify_godot.project_version(project))
            (project / 'project.godot').write_text(
                '[application]\nconfig/features=PackedStringArray("4.7", "GL Compatibility")\n')
            declared = verify_godot.project_version(project)
            self.assertEqual((4, 7), declared)
        # 升级引擎可通过；低于工程或跨主版本失败；显式版本精确匹配。
        for version in ('4.7.2.stable.official', '4.8.0.stable.official'):
            verify_godot.check_version(version, project=declared)
        for version in ('4.6.1.stable.official', '5.0.0.stable.official'):
            with self.assertRaisesRegex(ValueError, '低于工程'):
                verify_godot.check_version(version, project=declared)
        verify_godot.check_version('4.6.1.stable.official')
        with self.assertRaisesRegex(ValueError, '不匹配'):
            verify_godot.check_version('4.8.0.stable.official', '4.7.2', declared)

    def test_zero_exit_engine_errors_and_timeout_fail(self):
        for output in ('SCRIPT ERROR: Parse Error', 'ERROR: Failed loading resource'):
            result = subprocess.CompletedProcess(['godot'], 0, 'engine output', output)
            with patch.object(verify_godot.subprocess, 'run', return_value=result):
                with self.assertRaisesRegex(ValueError, 'Godot 检查失败'):
                    verify_godot.run_phase(['godot'], ROOT, 1)
        # 只放行明确预期的错误行，其他错误仍失败。
        mixed = subprocess.CompletedProcess(['godot'], 0, '', 'ERROR: ConfigFile parse error at user://save.cfg\nERROR: other')
        with patch.object(verify_godot.subprocess, 'run', return_value=mixed):
            with self.assertRaisesRegex(ValueError, 'Godot 检查失败'):
                verify_godot.run_phase(['godot'], ROOT, 1, ('ConfigFile parse error',))
        expected = subprocess.CompletedProcess(['godot'], 0, 'ok', 'ERROR: ConfigFile parse error at user://save.cfg')
        with patch.object(verify_godot.subprocess, 'run', return_value=expected):
            self.assertEqual('ok', verify_godot.run_phase(['godot'], ROOT, 1, ('ConfigFile parse error',)))
        with patch.object(verify_godot.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['godot'], 1)):
            with self.assertRaises(subprocess.TimeoutExpired):
                verify_godot.run_phase(['godot'], ROOT, 1)

    def test_installed_but_incomplete_or_linked_extension_is_rejected(self):
        import setup_project
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            native = project / package_release.SKILL
            native.mkdir(parents=True)
            (native / 'SKILL.md').write_text('native')
            extension = project / setup_project.GODOT_SKILL
            extension.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, '扩展不完整'):
                setup_project.project_block(project, 'godot-ios')
            extension.rmdir()
            extension.symlink_to(ROOT / package_release.GODOT_SKILL, target_is_directory=True)
            with self.assertRaises(ValueError):
                setup_project.project_block(project, 'godot-ios')


if __name__ == '__main__':
    unittest.main()
