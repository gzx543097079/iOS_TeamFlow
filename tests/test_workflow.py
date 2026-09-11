import contextlib
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import package_release as release
import review_gate as gate
import validate_workflow as validator


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.git('init', '-q')
        self.git('config', 'user.email', 'test@example.invalid')
        self.git('config', 'user.name', 'Workflow Test')

    def git(self, *args):
        return gate.git(self.root, *args)

    def stage(self, name='App/价格 view.swift', body='let value = 1\n'):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        self.git('add', '--', name)

    def complete(self):
        with contextlib.redirect_stdout(io.StringIO()):
            target = gate.prepare(self.root)
        report = json.loads(target.read_text())
        report.update(reviewer='测试夹具', completed_at='2026-09-11T00:00:00+00:00', summary='测试数据')
        for item in report['checks'].values():
            item.update(status='不适用', evidence='仅用于门禁行为测试的夹具，不是实际审查结论')
        target.write_text(json.dumps(report))
        return target

    def test_initial_commit_pending_then_reuse(self):
        self.stage()
        with self.assertRaises(ValueError):
            gate.check(self.root)
        target = self.complete()
        before = target.read_bytes()
        gate.check(self.root)
        gate.prepare(self.root)
        self.assertEqual(before, target.read_bytes())

    def test_staged_change_and_head_invalidate(self):
        self.stage()
        self.complete()
        self.stage(body='let value = 2\n')
        with self.assertRaises(ValueError):
            gate.check(self.root)
        self.complete()
        self.git('commit', '-qm', 'first')
        self.stage(body='let value = 3\n')
        with self.assertRaises(ValueError):
            gate.check(self.root)

    def test_partial_staging_uses_index(self):
        self.stage()
        target = self.complete()
        (self.root / 'App/价格 view.swift').write_text('let value = 99\n')
        gate.check(self.root)
        self.assertEqual(json.loads(target.read_text())['fingerprint'], gate.snapshot(self.root)[2])

    def test_head_only_change_invalidates_identical_patch(self):
        self.stage('base.txt')
        self.git('commit', '-qm', 'base')
        self.stage()
        self.complete()
        old_base, old_patch, _ = gate.snapshot(self.root)
        self.git('commit', '--allow-empty', '--only', '-qm', 'new context')
        new_base, new_patch, _ = gate.snapshot(self.root)
        self.assertNotEqual(old_base, new_base)
        self.assertEqual(old_patch, new_patch)
        with self.assertRaises(ValueError):
            gate.check(self.root)

    def test_workflow_policy_change_requires_review(self):
        self.stage()
        self.complete()
        self.stage('.agents/skills/ios-team-flow/references/REVIEW.md', 'new policy')
        with self.assertRaises(ValueError):
            gate.check(self.root)

    def test_receipts_do_not_retrigger_but_executables_rejected(self):
        self.stage()
        self.complete()
        before = gate.snapshot(self.root)[2]
        self.git('add', 'logs/reviews')
        self.assertEqual(before, gate.snapshot(self.root)[2])
        gate.check(self.root)
        self.stage('logs/reviews/hidden.py', 'print(1)')
        with self.assertRaises(ValueError):
            gate.snapshot(self.root)

    def test_pending_and_open_findings_rejected(self):
        self.stage()
        target = self.complete()
        report = json.loads(target.read_text())
        report['checks']['memory']['status'] = '未验证'
        target.write_text(json.dumps(report))
        with self.assertRaises(ValueError):
            gate.check(self.root)
        report['checks']['memory']['status'] = '通过'
        report['findings'] = [{'status': 'open'}]
        target.write_text(json.dumps(report))
        with self.assertRaises(ValueError):
            gate.check(self.root)

    def test_delete_rename_binary_and_mode_change_invalidate(self):
        self.stage('App/old.swift')
        self.git('commit', '-qm', 'base')
        self.git('mv', 'App/old.swift', 'App/new.swift')
        self.complete()
        (self.root / 'App/binary').write_bytes(b'\x00\xff\x01')
        self.git('add', 'App/binary')
        with self.assertRaises(ValueError):
            gate.check(self.root)
        self.complete()
        self.git('update-index', '--chmod=+x', 'App/new.swift')
        with self.assertRaises(ValueError):
            gate.check(self.root)
        self.complete()
        self.git('rm', '-f', 'App/new.swift')
        with self.assertRaises(ValueError):
            gate.check(self.root)

    def test_package_is_repeatable_and_excludes_project_data(self):
        for name in release.FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        self.stage('App/Secret.swift', 'private data')
        self.stage('scripts/business-secret.py', 'private data')
        self.stage('requirements/PRIVATE.md', 'private data')
        archive = release.package(self.root)
        before = archive.read_bytes()
        self.assertEqual(before, release.package(self.root).read_bytes())
        import zipfile
        with zipfile.ZipFile(archive) as stream:
            self.assertEqual(set(release.FILES), set(stream.namelist()))
            self.assertIn('.agents/skills/ios-team-flow/SKILL.md', stream.namelist())
        (self.root / '.agents/skills/ios-team-flow/references/VERSION').write_text('../bad')
        with self.assertRaises(ValueError):
            release.package(self.root)

    def test_package_rejects_symlink(self):
        for name in release.FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        target = self.root / 'AGENTS.md'
        target.unlink()
        target.symlink_to(ROOT / 'AGENTS.md')
        with self.assertRaises(ValueError):
            release.package(self.root)

    def test_repository_documents(self):
        validator.validate(ROOT)

    def extract_skill(self):
        import zipfile
        for name in release.FILES:
            target = self.root / 'source' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        archive = release.package_skill(self.root / 'source')
        before = archive.read_bytes()
        self.assertEqual(before, release.package_skill(self.root / 'source').read_bytes())
        with zipfile.ZipFile(archive) as stream:
            self.assertTrue(all(name.startswith('ios-team-flow/') for name in stream.namelist()))
            stream.extractall(self.root / 'installed')
        # 删除模拟源仓库，确保接入完全依赖安装包。
        shutil.rmtree(self.root / 'source')
        return self.root / 'installed/ios-team-flow'

    def run_setup(self, skill, project):
        local_skill = project / '.agents/skills/ios-team-flow'
        if not local_skill.exists():
            shutil.copytree(skill, local_skill)
        return subprocess.run([sys.executable, str(local_skill / 'scripts/setup_project.py'),
                               '--project', str(project)], cwd=self.root,
                              capture_output=True, text=True)

    def test_standalone_skill_two_projects_and_idempotence(self):
        skill = self.extract_skill()
        original = {str(p.relative_to(skill)): p.read_bytes() for p in skill.rglob('*') if p.is_file()}
        for name in ('项目 A', '项目 B'):
            project = self.root / name
            project.mkdir()
            (project / 'AGENTS.md').write_text('原有团队规则\n')
            result = self.run_setup(skill, project)
            self.assertEqual(0, result.returncode, result.stderr)
            before = (project / 'AGENTS.md').read_bytes()
            self.assertTrue(before.decode().startswith('原有团队规则\n'))
            self.assertEqual(0, self.run_setup(skill, project).returncode)
            self.assertEqual(before, (project / 'AGENTS.md').read_bytes())
            self.assertTrue((project / 'requirements').is_dir())
            self.assertTrue((project / 'logs/reviews').is_dir())
            self.assertFalse((project / 'workflow').exists())
            self.assertTrue((project / '.agents/teamflow.json').is_file())
            gate_result = subprocess.run([sys.executable, str(project / 'scripts/review_gate.py'), '--help'], capture_output=True, text=True)
            self.assertEqual(0, gate_result.returncode, gate_result.stderr)
        self.assertEqual(original, {str(p.relative_to(skill)): p.read_bytes()
                                   for p in skill.rglob('*') if p.is_file()})

    def test_direct_skill_edits_used_by_package_without_sync(self):
        import zipfile
        for name in release.FILES:
            target = self.root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        policy = '.agents/skills/ios-team-flow/references/standards/ui.md'
        changed = (self.root / policy).read_text() + '\n项目直接维护的规则。\n'
        (self.root / policy).write_text(changed)
        validator.validate(self.root)
        for archive, member in (
            (release.package(self.root), policy),
            (release.package_skill(self.root), 'ios-team-flow/references/standards/ui.md'),
        ):
            with zipfile.ZipFile(archive) as stream:
                self.assertEqual(changed, stream.read(member).decode())
                self.assertFalse(any(n.startswith('workflow/') for n in stream.namelist()))
        self.assertFalse((self.root / 'workflow').exists())

    def test_project_gate_uses_current_skill_implementation(self):
        skill = self.extract_skill()
        project = self.root / 'live-gate'
        self.assertEqual(0, self.run_setup(skill, project).returncode)
        implementation = project / '.agents/skills/ios-team-flow/scripts/review_gate.py'
        implementation.write_text("print('project-local-gate')\n")
        result = subprocess.run([sys.executable, str(project / 'scripts/review_gate.py')],
                                capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('project-local-gate', result.stdout.strip())

    def test_setup_conflict_does_not_modify_project(self):
        skill = self.extract_skill()
        project = self.root / 'conflict'
        (project / 'scripts').mkdir(parents=True)
        target = project / 'scripts/review_gate.py'
        target.write_text('用户定制代码')
        self.assertNotEqual(0, self.run_setup(skill, project).returncode)
        self.assertEqual('用户定制代码', target.read_text())
        self.assertFalse((project / 'AGENTS.md').exists())
        self.assertFalse((project / 'workflow').exists())

    def test_external_skill_cannot_bind_project(self):
        skill = self.extract_skill()
        project = self.root / 'not-installed'
        result = subprocess.run([sys.executable, str(skill / 'scripts/setup_project.py'),
                                 '--project', str(project)], capture_output=True, text=True)
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(project.exists())

    def test_project_copy_keeps_local_workflow(self):
        skill = self.extract_skill()
        project = self.root / 'project-original'
        self.assertEqual(0, self.run_setup(skill, project).returncode)
        copied = self.root / 'project-copy'
        shutil.copytree(project, copied)
        shutil.rmtree(project)
        shutil.rmtree(skill)
        local = copied / '.agents/skills/ios-team-flow'
        result = subprocess.run([sys.executable, str(local / 'scripts/setup_project.py'),
                                 '--project', str(copied)], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('.agents/skills/ios-team-flow/SKILL.md', (copied / 'AGENTS.md').read_text())

    def test_setup_version_conflict_and_symlink(self):
        skill = self.extract_skill()
        project = self.root / 'version'
        self.assertEqual(0, self.run_setup(skill, project).returncode)
        manifest = project / '.agents/teamflow.json'
        manifest.write_text('{"version": "0.0.1"}')
        self.assertNotEqual(0, self.run_setup(skill, project).returncode)
        self.assertEqual('{"version": "0.0.1"}', manifest.read_text())
        other = self.root / 'symlink'
        other.mkdir()
        (other / 'scripts').symlink_to(skill / 'scripts', target_is_directory=True)
        self.assertNotEqual(0, self.run_setup(skill, other).returncode)
        self.assertFalse((other / 'AGENTS.md').exists())

    def test_setup_detects_overriding_instructions(self):
        skill = self.extract_skill()
        project = self.root / 'override'
        project.mkdir()
        (project / 'AGENTS.override.md').write_text('项目优先规则')
        result = self.run_setup(skill, project)
        self.assertNotEqual(0, result.returncode)
        self.assertIn('AGENTS.override.md', result.stderr)
        self.assertFalse((project / 'AGENTS.md').exists())


if __name__ == '__main__':
    unittest.main()
