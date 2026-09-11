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
CURRENT_VERSION = tuple(map(int, (ROOT / '.agents/skills/ios-team-flow/references/VERSION').read_text().strip().split('.')))
NEXT_VERSION = f'{CURRENT_VERSION[0]}.{CURRENT_VERSION[1] + 1}.0'
LATER_VERSION = f'{CURRENT_VERSION[0]}.{CURRENT_VERSION[1] + 2}.0'
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
        self.git('add', str(target.relative_to(self.root)))
        return target

    def test_unstaged_report_cannot_replace_pending_index_report(self):
        self.stage()
        target = gate.prepare(self.root)
        self.git('add', 'logs/reviews')
        pending = target.read_bytes()
        self.complete()
        complete = target.read_bytes()
        target.write_bytes(pending)
        self.git('add', 'logs/reviews')
        target.write_bytes(complete)
        with self.assertRaises(ValueError):
            gate.check(self.root)
        self.git('add', 'logs/reviews')
        gate.check(self.root)
        target.write_bytes(pending)  # 工作区变化不改变即将提交的有效报告。
        gate.check(self.root)
        self.git('rm', '-f', '--cached', str(target.relative_to(self.root)))
        with self.assertRaises(ValueError):
            gate.check(self.root)

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
        self.git('add', str(target.relative_to(self.root)))
        with self.assertRaises(ValueError):
            gate.check(self.root)
        report['checks']['memory']['status'] = '通过'
        report['findings'] = [{'status': 'open'}]
        target.write_text(json.dumps(report))
        self.git('add', str(target.relative_to(self.root)))
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

    def project_files(self, project):
        return {str(p.relative_to(project)): p.read_bytes()
                for p in project.rglob('*') if p.is_file()}

    def bump_skill(self, project, version=NEXT_VERSION):
        local = project / '.agents/skills/ios-team-flow'
        (local / 'references/VERSION').write_text(version + '\n')
        script = local / 'scripts/setup_project.py'
        script.write_text(script.read_text().replace('版本见 .agents/teamflow.json',
                                                    '工作流版本见 .agents/teamflow.json')
                          .replace('唯一实现维护在 Skill 内', '实现由本项目 Skill 提供'))

    def test_upgrade_121_without_baseline(self):
        skill = self.extract_skill()
        project = self.root / 'from-121'
        local = project / '.agents/skills/ios-team-flow'
        shutil.copytree(skill, local)
        (project / 'scripts').mkdir()
        old_block = '<!-- ios-team-flow:start -->\n## iOS 团队工作流\n\n本项目采用仓库内的 `.agents/skills/ios-team-flow/SKILL.md`。实施 iOS 需求和提交前必须读取该文件，无需用户再次点名 Skill；按 OC / Swift / SwiftUI / UI 类型加载规范，维护 requirements/ 需求过程与 logs/ 审查记录。\n新产品先整理 PRD 交团队确认。提交前只 review 本次改动，相同有效指纹复用；运行 `python3 scripts/review_gate.py check`。未经授权不提交或发布。\n版本见 .agents/teamflow.json，Skill 与项目一起提交和克隆，不依赖用户级安装。找不到本地 Skill 时明确报告缺失，不自动改用其他项目或用户级同名版本。遵守项目现有具体约定，有冲突先说明。\n<!-- ios-team-flow:end -->\n'
        old_gate = '#!/usr/bin/env python3\n"""从项目内 Skill 加载审查门禁，唯一实现维护在 Skill 内。"""\nimport runpy\nfrom pathlib import Path\n\n_source = Path(__file__).resolve().parents[1] / \'.agents/skills/ios-team-flow/scripts/review_gate.py\'\nglobals().update(runpy.run_path(str(_source), run_name=__name__))\n'
        agents = '团队前置规则\n' + old_block + '\n团队后置规则\n'
        (project / 'AGENTS.md').write_text(agents)
        (project / 'scripts/review_gate.py').write_text(old_gate)
        manifest = project / '.agents/teamflow.json'
        manifest.write_text(json.dumps({'skill': 'ios-team-flow', 'version': '1.2.1',
                                        'team': '保留团队字段'}))
        self.bump_skill(project)
        result = self.run_setup(skill, project)
        self.assertEqual(0, result.returncode, result.stderr)
        data = json.loads(manifest.read_text())
        self.assertEqual(NEXT_VERSION, data['version'])
        self.assertEqual('保留团队字段', data['team'])
        self.assertEqual({'agents_block', 'gate_entry'}, set(data['managed']))
        updated = (project / 'AGENTS.md').read_text()
        self.assertTrue(updated.startswith('团队前置规则\n'))
        self.assertTrue(updated.endswith('\n团队后置规则\n'))
        self.assertIn('工作流版本见 .agents/teamflow.json', updated)
        backups = list((project / '.agents/teamflow-backups').glob('upgrade-*'))
        self.assertEqual(1, len(backups))
        self.assertEqual(agents, (backups[0] / 'AGENTS.md').read_text())
        self.assertEqual(old_gate, (backups[0] / 'scripts/review_gate.py').read_text())
        before = self.project_files(project)
        self.assertEqual(0, self.run_setup(skill, project).returncode)
        self.assertEqual(before, self.project_files(project))

    def test_future_upgrade_with_baseline(self):
        skill = self.extract_skill()
        project = self.root / 'future'
        self.assertEqual(0, self.run_setup(skill, project).returncode)
        self.bump_skill(project)
        result = self.run_setup(skill, project)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(NEXT_VERSION, json.loads((project / '.agents/teamflow.json').read_text())['version'])
        self.bump_skill(project, LATER_VERSION)
        self.assertEqual(0, self.run_setup(skill, project).returncode)
        self.assertEqual(LATER_VERSION, json.loads((project / '.agents/teamflow.json').read_text())['version'])

    def test_upgrade_customization_conflicts_write_nothing(self):
        skill = self.extract_skill()
        for name in ('AGENTS.md', 'scripts/review_gate.py'):
            with self.subTest(name=name):
                project = self.root / ('custom-' + Path(name).stem)
                self.assertEqual(0, self.run_setup(skill, project).returncode)
                target = project / name
                if name == 'AGENTS.md':
                    target.write_text(target.read_text().replace('新产品先整理 PRD', '定制：新产品先整理 PRD'))
                else:
                    target.write_text(target.read_text() + '\n# 团队定制\n')
                self.bump_skill(project)
                before = self.project_files(project)
                result = self.run_setup(skill, project)
                self.assertNotEqual(0, result.returncode)
                self.assertIn('团队修改', result.stderr)
                self.assertEqual(before, self.project_files(project))

    def test_version_only_upgrade_preserves_team_customization(self):
        skill = self.extract_skill()
        project = self.root / 'custom-version-only'
        self.assertEqual(0, self.run_setup(skill, project).returncode)
        agents = project / 'AGENTS.md'
        agents.write_text(agents.read_text().replace('新产品先整理 PRD', '团队定制：新产品先整理 PRD'))
        entry = project / 'scripts/review_gate.py'
        entry.write_text(entry.read_text() + '\n# 团队定制\n')
        expected = (agents.read_bytes(), entry.read_bytes())
        (project / '.agents/skills/ios-team-flow/references/VERSION').write_text(NEXT_VERSION + '\n')
        result = self.run_setup(skill, project)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(expected, (agents.read_bytes(), entry.read_bytes()))
        self.assertEqual(NEXT_VERSION, json.loads((project / '.agents/teamflow.json').read_text())['version'])

    def test_upgrade_rejects_downgrade_bad_manifest_and_markers(self):
        skill = self.extract_skill()
        for case in ('downgrade', 'bad-json', 'bad-baseline', 'reversed-markers'):
            with self.subTest(case=case):
                project = self.root / case
                self.assertEqual(0, self.run_setup(skill, project).returncode)
                manifest = project / '.agents/teamflow.json'
                if case == 'downgrade':
                    self.bump_skill(project, '1.0.0')
                elif case == 'bad-json':
                    manifest.write_text('{broken')
                elif case == 'bad-baseline':
                    data = json.loads(manifest.read_text())
                    data['managed'] = []
                    manifest.write_text(json.dumps(data))
                else:
                    (project / 'AGENTS.md').write_text('<!-- ios-team-flow:end -->\n<!-- ios-team-flow:start -->')
                before = self.project_files(project)
                self.assertNotEqual(0, self.run_setup(skill, project).returncode)
                self.assertEqual(before, self.project_files(project))

    def test_setup_uses_overriding_instructions_and_upgrades(self):
        skill = self.extract_skill()
        project = self.root / 'override'
        project.mkdir()
        override = project / 'AGENTS.override.md'
        override.write_text('项目优先规则')
        result = self.run_setup(skill, project)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(override.read_text().startswith('项目优先规则'))
        self.assertEqual(1, override.read_text().count('<!-- ios-team-flow:start -->'))
        self.assertFalse((project / 'AGENTS.md').exists())
        self.assertEqual('AGENTS.override.md', json.loads((project / '.agents/teamflow.json').read_text())['instruction_file'])
        self.assertEqual(0, self.run_setup(skill, project).returncode)
        self.bump_skill(project)
        self.assertEqual(0, self.run_setup(skill, project).returncode)
        self.assertIn('工作流版本见', override.read_text())

    def test_switch_from_agents_to_override_keeps_old_rules(self):
        skill = self.extract_skill()
        project = self.root / 'switch-override'
        self.assertEqual(0, self.run_setup(skill, project).returncode)
        original = (project / 'AGENTS.md').read_bytes()
        (project / 'AGENTS.override.md').write_text('override rule')
        result = self.run_setup(skill, project)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(original, (project / 'AGENTS.md').read_bytes())
        self.assertIn('<!-- ios-team-flow:start -->', (project / 'AGENTS.override.md').read_text())


    def test_gate_rechecks_linked_test_report_against_index(self):
        self.stage('App/code.swift', 'old')
        (self.root / 'App/code.swift').write_text('fixed')
        (self.root / '.agents').mkdir()
        (self.root / '.agents/project-checks.json').write_text(json.dumps({
            'schema_version': 1, 'inputs': ['App'],
            'checks': {'ok': {'argv': [sys.executable, '-c', 'pass']}}, 'profiles': {'change': ['ok']}}))
        self.git('add', '.agents/project-checks.json')
        subprocess.run([sys.executable, str(ROOT / release.SKILL / 'scripts/project_checks.py'),
                        '--project', str(self.root), 'run', '--profile', 'change'],
                       check=True, capture_output=True)
        result = next((self.root / 'logs/project-checks').glob('*/result.json'))
        self.git('add', str(result.relative_to(self.root)))
        report_path = self.complete()
        report = json.loads(report_path.read_text())
        report['validation_results'] = [str(result.relative_to(self.root))]
        report_path.write_text(json.dumps(report))
        self.git('add', str(report_path.relative_to(self.root)))
        with self.assertRaisesRegex(ValueError, '暂存内容'):
            gate.check(self.root)
        self.git('add', 'App/code.swift')
        report_path = self.complete()
        report = json.loads(report_path.read_text())
        report['validation_results'] = [str(result.relative_to(self.root))]
        report_path.write_text(json.dumps(report))
        self.git('add', str(report_path.relative_to(self.root)))
        gate.check(self.root)

    def test_requirement_template_links_at_destination(self):
        import re
        template = (ROOT / release.SKILL / 'references/templates/requirement.md').read_text()
        self.assertNotIn('审查指纹/报告：提交前填写', template)
        shutil.copytree(ROOT / release.SKILL, self.root / release.SKILL)
        destination = self.root / 'requirements/REQ-20260911-001.md'
        destination.parent.mkdir()
        destination.write_text(template)
        for target in re.findall(r'\]\(([^)]+)\)', template):
            self.assertTrue((destination.parent / target).exists(), target)


if __name__ == '__main__':
    unittest.main()
