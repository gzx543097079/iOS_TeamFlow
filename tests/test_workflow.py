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
            for _ in range(2):
                result = subprocess.run(command, capture_output=True, text=True)
                self.assertEqual(0, result.returncode, result.stderr)
            content = (project / 'AGENTS.md').read_text()
            self.assertIn('保留项目约定。', content)
            self.assertEqual(1, content.count('<!-- ios-team-flow:start -->'))
            self.assertIn('SKILL.md', content)
            self.assertTrue((project / 'requirements').is_dir())
            help_result = subprocess.run(
                [sys.executable, str(project / 'scripts/teamflow.py'), '--help'],
                capture_output=True, text=True)
            self.assertEqual(0, help_result.returncode, help_result.stderr)
            (project / '.agents/teamflow.json').write_text('{"schema_version": 1}')
            rejected = subprocess.run(command, capture_output=True, text=True)
            self.assertNotEqual(0, rejected.returncode)


if __name__ == '__main__':
    unittest.main()
