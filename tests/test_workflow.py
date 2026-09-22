import importlib.util
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
    VALIDATION_SEQUENCE = '完成全部改动 → 环境预检 → 针对性测试 → 文件冻结 → 一次完整验证 → 目标交付'

    def test_repository_documents_and_distribution_manifest(self):
        validate_workflow.validate(ROOT)
        names = set(package_release.FILES)
        self.assertIn('scripts/teamflow.py', names)
        self.assertIn(package_release.SKILL + '/scripts/teamflow.py', names)
        for removed in ('scripts/review_gate.py', package_release.SKILL + '/scripts/delivery.py',
                        package_release.SKILL + '/scripts/review_gate.py',
                        package_release.SKILL + '/scripts/upgrade_skill.py'):
            self.assertNotIn(removed, names)

    def test_new_project_is_stage_scoped(self):
        template = ROOT / package_release.SKILL / 'references/templates/new-project.md'
        self.assertLess(len(template.read_text().splitlines()), 80)
        self.assertIn('templates/feature.md', (ROOT / package_release.SKILL / 'SKILL.md').read_text())
        self.assertNotIn('App Store Connect App ID / SKU', template.read_text())

    def test_required_prerequisites_are_distributed_without_optional_expansion(self):
        skill = (ROOT / package_release.SKILL / 'SKILL.md').read_text()
        workflow = (ROOT / package_release.SKILL / 'references/WORKFLOW.md').read_text()
        git_actions = (ROOT / package_release.SKILL / 'references/GIT-ACTIONS.md').read_text()
        app_release = (ROOT / package_release.SKILL / 'references/APP-RELEASE.md').read_text()
        readme = (ROOT / 'README.md').read_text()
        setup = (ROOT / package_release.SKILL / 'scripts/setup_project.py').read_text()
        for text in (skill, workflow, git_actions, app_release, readme, setup):
            self.assertIn('必要前置', text)
        self.assertIn('GitHub Release', git_actions)
        self.assertIn('testFlightInternalTestingOnly', app_release)
        self.assertIn('可选上传参数', app_release)

    def test_frozen_input_validation_sequence_is_distributed(self):
        paths = (
            ROOT / package_release.SKILL / 'SKILL.md',
            ROOT / package_release.SKILL / 'references/WORKFLOW.md',
            ROOT / package_release.SKILL / 'references/PROJECT-CHECKS.md',
            ROOT / package_release.SKILL / 'scripts/setup_project.py',
            ROOT / 'README.md',
        )
        for path in paths:
            self.assertIn(self.VALIDATION_SEQUENCE, path.read_text(), path)

    def test_setup_fresh_project_and_rejects_old_schema(self):
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            skill = project / '.agents/skills/ios-team-flow'
            skill.parent.mkdir(parents=True)
            import shutil
            shutil.copytree(ROOT / package_release.SKILL, skill)
            script = skill / 'scripts/setup_project.py'
            subprocess.run(['git', '-C', str(project), 'init', '-q'], check=True)
            result = subprocess.run([sys.executable, str(script), '--project', str(project)],
                                    capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertTrue((project / 'scripts/teamflow.py').is_file())
            self.assertTrue((project / 'requirements').is_dir())
            self.assertFalse((project / 'logs/reviews').exists())
            self.assertIn(self.VALIDATION_SEQUENCE, (project / 'AGENTS.md').read_text())
            help_result = subprocess.run([sys.executable, str(project / 'scripts/teamflow.py'), '--help'],
                                         capture_output=True, text=True)
            self.assertEqual(0, help_result.returncode, help_result.stderr)
            (project / '.agents/teamflow.json').write_text('{"schema_version": 1}')
            rejected = subprocess.run([sys.executable, str(script), '--project', str(project)],
                                      capture_output=True, text=True)
            self.assertNotEqual(0, rejected.returncode)
            self.assertIn('不提供兼容升级', rejected.stderr)


if __name__ == '__main__':
    unittest.main()
