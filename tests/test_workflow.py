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
        self.assertIn(package_release.SKILL + '/scripts/teamflow.py', names)

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
            skill = project / '.agents/skills/ios-team-flow'
            skill.parent.mkdir(parents=True)
            shutil.copytree(ROOT / package_release.SKILL, skill)
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
            self.assertEqual(1, content.count('<!-- ios-team-flow:start -->'))
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
            link = project / '.claude/skills/ios-team-flow'
            self.assertTrue(link.is_symlink())
            self.assertEqual(skill.resolve(), link.resolve())
            self.assertTrue((link / 'SKILL.md').is_file())
            subprocess.run(command + ['--claude-skill-link'], check=True, capture_output=True)
            os.unlink(link); link.mkdir()
            conflict = subprocess.run(command + ['--claude-skill-link'], capture_output=True, text=True)
            self.assertNotEqual(0, conflict.returncode)
            self.assertIn('软链接', conflict.stderr)

if __name__ == '__main__':
    unittest.main()
