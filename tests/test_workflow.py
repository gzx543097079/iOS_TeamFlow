import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import package_release
import validate_workflow


class WorkflowTests(unittest.TestCase):
    def test_release_profile_must_extend_workflow(self):
        config = {'profiles': {'workflow-release': {'inputs': ['docs'], 'checks': {}}}}
        with self.assertRaisesRegex(ValueError, 'extends workflow'):
            validate_workflow.validate_profile_overlap(config)
        config['profiles']['workflow-release'] = {'extends': 'workflow', 'checks': {}}
        validate_workflow.validate_profile_overlap(config)

    def test_repository_documents_and_distribution_manifest(self):
        validate_workflow.validate(ROOT)
        names = set(package_release.FILES)
        self.assertIn('scripts/teamflow.py', names)
        self.assertIn('.agents/project-checks.json', names)
        for test in (ROOT / 'tests').glob('test_*.py'):
            self.assertIn(str(test.relative_to(ROOT)), names)
        self.assertIn(package_release.CORE + '/scripts/teamflow.py', names)

    def test_release_profile_is_explicit_only(self):
        import json
        config = json.loads((ROOT / '.agents/project-checks.json').read_text())
        self.assertIs(True, config['profiles']['workflow-release']['manual'])

    def test_each_test_file_belongs_to_exactly_one_daily_check(self):
        import json
        checks = json.loads((ROOT / '.agents/project-checks.json').read_text())['profiles']['workflow']['checks']
        owners = {}
        for name, check in checks.items():
            argv = check['argv']
            self.assertEqual(['python3', 'scripts/run_workflow_checks.py'], argv[:2], name)
            self.assertTrue(argv[2:], name + ' 不能退化为全量发现')
            for test in argv[2:]:
                owners.setdefault(test, []).append(name)
                self.assertIn('tests/' + test, check['covers'], name)
        files = sorted(p.name for p in (ROOT / 'tests').glob('test_*.py'))
        self.assertEqual(files, sorted(owners))
        self.assertEqual({}, {test: names for test, names in owners.items() if len(names) > 1})

    def test_tests_package_into_temporary_output_not_repository_dist(self):
        snapshot = lambda: {p.name: p.stat().st_mtime_ns for p in (ROOT / 'dist').glob('*')} if (ROOT / 'dist').is_dir() else {}
        before = snapshot()
        with tempfile.TemporaryDirectory() as directory:
            archive = package_release.package_mode(ROOT, 'ios', directory)
            self.assertEqual(Path(directory), archive.parent)
            self.assertTrue(archive.with_suffix('.zip.sha256').is_file())
        self.assertEqual(before, snapshot())
        for test in (ROOT / 'tests').glob('*.py'):
            if test.name != 'release_fixture.py':
                self.assertNotRegex(test.read_text(), r'package_release\.package\w*\(ROOT\)', test.name)

    def test_repository_does_not_activate_extra_host_permissions(self):
        for target, source in package_release.PERMISSIONS.items():
            self.assertTrue((ROOT / source).is_file(), source)
            self.assertFalse((ROOT / target).exists(), target)

    def test_links_are_checked_per_install_mode_and_anchor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in package_release.FILES + ('.agents/project-checks.json',):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes((ROOT / name).read_bytes())
            validate_workflow.validate(root)
            # 纯 Godot 模式下 Godot Skill 的 iOS 路由允许指向未安装的 iOS Skill。
            self.assertIn('../iOS/references/APP-RELEASE.md', (root / package_release.GODOT_SKILL / 'SKILL.md').read_text())
            workflow = root / package_release.CORE / 'references/WORKFLOW.md'
            original = workflow.read_text()
            workflow.write_text(original + '\n[发布](../../skills/iOS/references/APP-RELEASE.md)\n')
            with self.assertRaisesRegex(ValueError, 'godot 安装包中 .*WORKFLOW.md 链接了包外文件'):
                validate_workflow.validate(root)
            workflow.write_text(original + '\n[边界](BOUNDARIES.md#不存在的标题)\n')
            with self.assertRaisesRegex(ValueError, '锚点不存在：BOUNDARIES.md#不存在的标题'):
                validate_workflow.validate(root)
            # 安装包不含源码仓库的示例与文档，包内链接到它们同样是断链。
            workflow.write_text(original + '\n[说明](../../../README.md)\n')
            with self.assertRaisesRegex(ValueError, 'ios 安装包中 .*WORKFLOW.md 链接了包外文件：README.md'):
                validate_workflow.validate(root)
            (root / 'requirements').mkdir()
            workflow.write_text(original)
            (root / 'requirements/PROJECT-CONTEXT.md').write_text('[旧索引](../.agents/skills/ios-team-flow/x.md)\n')
            with self.assertRaisesRegex(ValueError, 'PROJECT-CONTEXT.md 的链接不存在'):
                validate_workflow.validate(root)

    def test_stale_version_examples_in_distribution_docs_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in package_release.FILES + ('.agents/project-checks.json',):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                (root / name).write_bytes((ROOT / name).read_bytes())
            validate_workflow.validate(root)
            install = root / package_release.CORE / 'references/INSTALL.md'
            original = install.read_text()
            install.write_text(original + '\nunzip ~/Downloads/teamflow-ios-v0.0.1.zip\n')
            with self.assertRaisesRegex(ValueError, '版本示例 0.0.1 与 VERSION'):
                validate_workflow.validate(root)
            # CHANGELOG 与内测记录保留历史版本号，不视为示例。
            install.write_text(original)
            (root / 'CHANGELOG.md').write_text('# 版本记录\n\n## 0.0.1\n\n- 旧版本。\n')
            validate_workflow.validate(root)

    def test_documented_command_options_must_exist_in_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            doc = Path(directory) / 'doc.md'
            doc.write_text('```sh\npython3 scripts/teamflow.py req complete REQ-1 \\\n  --profile change --confirm-ac AC-01\n```\n'
                           '用 `req state REQ-1 --state 进行中 --reopen-ac AC-01` 重开；`git commit --no-verify` 不是 TeamFlow 命令。\n')
            self.assertEqual([], validate_workflow.command_errors(ROOT, [str(doc)]))
            for bad in ('`req complete REQ-1 --bogus`', '`git hook --profile <名>`',
                        '```sh\npython3 scripts/teamflow.py setup \\\n  --git-hook --typo\n```'):
                with self.subTest(bad=bad):
                    doc.write_text(bad + '\n')
                    self.assertEqual(1, len(validate_workflow.command_errors(ROOT, [str(doc)])))

    def test_heading_slug_matches_github(self):
        self.assertEqual('显式-git-动作', validate_workflow.slug('显式 Git 动作'))
        self.assertEqual('授权与停止', validate_workflow.slug('授权与停止'))
        self.assertEqual('1-设计基线', validate_workflow.slug('1. 设计基线'))

    def test_clean_dist_keeps_current_version_and_other_files(self):
        version = (ROOT / package_release.CORE / 'references/VERSION').read_text().strip()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / package_release.CORE / 'references').mkdir(parents=True)
            (root / package_release.CORE / 'references/VERSION').write_text(version + '\n')
            dist = root / 'dist'
            dist.mkdir()
            keep = ['teamflow-ios-v' + version + '.zip', 'teamflow-ios-v' + version + '.zip.sha256', 'notes.txt']
            stale = ['teamflow-ios-v0.0.1.zip', 'teamflow-ios-v0.0.1.zip.sha256', 'iOS-TeamFlow-v4.0.0.zip']
            for name in keep + stale:
                (dist / name).write_text(name)
            self.assertEqual(sorted(stale), package_release.clean_dist(root))
            self.assertEqual(sorted(keep), sorted(p.name for p in dist.iterdir()))

    def test_discovery_loads_real_tests(self):
        loader = unittest.TestLoader()
        suite = loader.discover(str(ROOT / 'tests'))
        self.assertFalse(loader.errors, '\n'.join(loader.errors))
        self.assertGreater(suite.countTestCases(), 0)

    def test_setup_preserves_project_instructions_and_is_repeatable(self):
        import json
        import os
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            skill = project / package_release.CORE
            skill.parent.mkdir(parents=True)
            shutil.copytree(ROOT / package_release.CORE, skill)
            native = project / package_release.SKILL
            native.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(ROOT / package_release.SKILL, native)
            (project / 'AGENTS.md').write_text('# 自有约束\n保留项目约定。\n')
            subprocess.run(['git', '-C', str(project), 'init', '-q'], check=True)
            command = [sys.executable, str(skill / 'scripts/teamflow.py'), '--project', str(project), 'setup']
            preview = subprocess.run(command + ['--plan'], capture_output=True, text=True)
            self.assertEqual(0, preview.returncode, preview.stderr)
            self.assertIn('--- AGENTS.md', preview.stdout)
            self.assertIn('+++ scripts/teamflow.py', preview.stdout)
            self.assertIn('+/logs/project-checks/', preview.stdout)
            self.assertEqual('# 自有约束\n保留项目约定。\n', (project / 'AGENTS.md').read_text())
            self.assertFalse((project / 'scripts/teamflow.py').exists())
            self.assertFalse((project / 'requirements').exists())
            for _ in range(2):
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stderr)
            unchanged = subprocess.run(command + ['--plan'], capture_output=True, text=True)
            self.assertEqual(0, unchanged.returncode, unchanged.stderr)
            self.assertEqual('', unchanged.stdout)
            content = (project / 'AGENTS.md').read_text()
            self.assertIn('保留项目约定。', content)
            self.assertEqual(1, content.count('<!-- teamflow:start -->'))
            self.assertIn('SKILL.md', content)
            self.assertEqual(1, (project / '.gitignore').read_text().count('/logs/project-checks/'))
            self.assertTrue((project / 'requirements').is_dir())
            self.assertFalse((project / '.claude').exists())
            entry = [sys.executable, str(project / 'scripts/teamflow.py'), '--project', str(project)]
            self.assertEqual(0, subprocess.run(entry + ['--help'], capture_output=True).returncode)

            def entry_status():
                report = subprocess.run(entry[:2] and [sys.executable, str(skill / 'scripts/teamflow.py'),
                                        '--project', str(project), 'doctor', '--json'], capture_output=True, text=True)
                return next(i for i in json.loads(report.stdout)['checks'] if i['item'] == 'Skill 与入口')['status']
            (project / 'scripts/teamflow.py').write_text('# broken entry\n')
            self.assertEqual('需处理', entry_status())
            subprocess.run(command, check=True, capture_output=True)
            self.assertEqual('就绪', entry_status())

            linked = subprocess.run(command + ['--claude-skill-link'], capture_output=True, text=True)
            self.assertEqual(0, linked.returncode, linked.stderr)
            link = project / '.claude/skills/ios'
            self.assertTrue(link.is_symlink())
            self.assertEqual(native.resolve(), link.resolve())
            self.assertTrue((link / 'SKILL.md').is_file())
            subprocess.run(command + ['--claude-skill-link'], check=True, capture_output=True)
            os.unlink(link); link.mkdir()
            conflict = subprocess.run(command + ['--claude-skill-link'], capture_output=True, text=True)
            self.assertNotEqual(0, conflict.returncode)
            self.assertIn('软链接', conflict.stderr)

if __name__ == '__main__':
    unittest.main()
