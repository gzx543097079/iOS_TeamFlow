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
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            skill = project / '.agents/skills/ios-team-flow'
            skill.parent.mkdir(parents=True)
            import shutil
            shutil.copytree(ROOT / package_release.SKILL, skill)
            script = skill / 'scripts/setup_project.py'
            (project / 'AGENTS.md').write_text('# 自有约束\n保留项目约定。\n')
            subprocess.run(['git', '-C', str(project), 'init', '-q'], check=True)
            command = [sys.executable, str(script), '--project', str(project)]
            preview = subprocess.run(command + ['--plan'], capture_output=True, text=True)
            self.assertEqual(0, preview.returncode, preview.stderr)
            self.assertIn('--- AGENTS.md', preview.stdout)
            self.assertIn('+++ scripts/teamflow.py', preview.stdout)
            self.assertIn('SKILL.md', preview.stdout)
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
            self.assertTrue((project / 'requirements').is_dir())
            help_result = subprocess.run(
                [sys.executable, str(project / 'scripts/teamflow.py'), '--help'],
                capture_output=True, text=True)
            self.assertEqual(0, help_result.returncode, help_result.stderr)
            self.assertFalse((project / '.agents/teamflow.json').exists())
            entry = project / 'scripts/teamflow.py'
            entry.write_text('# broken entry\n')
            report = subprocess.run(command + ['--doctor'], capture_output=True, text=True)
            import json
            item = next(i for i in json.loads(report.stdout)['checks'] if i['item'] == 'Skill 与入口')
            self.assertEqual('需处理', item['status'])
            subprocess.run(command, check=True, capture_output=True)
            report = subprocess.run(command + ['--doctor'], capture_output=True, text=True)
            item = next(i for i in json.loads(report.stdout)['checks'] if i['item'] == 'Skill 与入口')
            self.assertEqual('就绪', item['status'])


if __name__ == '__main__':
    unittest.main()
