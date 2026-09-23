import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/ios-team-flow/scripts"))
spec = importlib.util.spec_from_file_location('project_checks', ROOT / '.agents/skills/ios-team-flow/scripts/project_checks.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class ProjectChecksTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / '.agents').mkdir()
        (self.root / 'source').write_text('fixture source')

    def config(self, commands):
        data = {'schema_version': 2, 'profiles': {'change': {
            'inputs': ['source'], 'checks': commands}}}
        (self.root / checks.CONFIG).write_text(json.dumps(data))

    def test_success_and_literal_arguments(self):
        self.config({'build': {'argv': [sys.executable, '-c', 'import sys; print(sys.argv[1])', 'a b;$(echo test)']}})
        path, passed = checks.run(self.root, 'change')
        self.assertTrue(passed)
        self.assertEqual('a b;$(echo test)\n', (path.parent / 'build.log').read_text())
        self.assertEqual(0, json.loads(path.read_text())['results'][0]['exit_code'])

    def test_only_selected_effective_configuration_invalidates_result(self):
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        config_path = self.root / checks.CONFIG
        original = json.loads(config_path.read_text())
        original['profiles']['other'] = {'checks': {'other': {'argv': [sys.executable, '-c', 'print(1)']}}}
        config_path.write_text(json.dumps(original))
        result, passed = checks.run(self.root, 'change')
        self.assertTrue(passed)
        relative = str(result.relative_to(self.root))
        unrelated = json.loads(json.dumps(original))
        unrelated['profiles']['other']['checks']['other']['argv'][-1] = 'print(2)'
        unrelated['profiles']['other']['inputs'] = ['unrelated']
        unrelated['profiles']['change']['checks']['ok'].update(cwd='.', timeout_seconds=900)
        config_path.write_text(json.dumps(unrelated, indent=4))
        checks.verify(self.root, relative)
        variants = []
        for field, value in [('argv', [sys.executable, '-c', 'print(3)']),
                             ('timeout_seconds', 901), ('cwd', '.agents')]:
            changed = json.loads(json.dumps(original))
            changed['profiles']['change']['checks']['ok'][field] = value
            variants.append(changed)
        for field, value in [('inputs', ['.agents']), ('checks', original['profiles']['other']['checks'])]:
            changed = json.loads(json.dumps(original))
            changed['profiles']['change'][field] = value
            variants.append(changed)
        for changed in variants:
            config_path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                checks.verify(self.root, relative)

    def test_requirement_binding_ignores_other_cards_but_tracks_scope_and_ac(self):
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        directory = self.root / 'requirements'
        directory.mkdir()
        card = directory / 'REQ-0001.md'
        initial = ('# REQ-0001\n<!-- teamflow:requirement:vnext -->\n'
                   '- 状态：🔵 进行中\n- 范围：修复提示\n'
                   '- ⚪ AC-01：显示结果\n\n## 验证\n- 验证证据：—\n')
        card.write_text(initial)
        result, passed = checks.run(self.root, 'change', 'REQ-0001')
        self.assertTrue(passed)
        relative = str(result.relative_to(self.root))
        (directory / 'REQ-0002.md').write_text('其他需求')
        card.write_text(initial.replace('🔵 进行中', '🟣 待用户验证')
                       .replace('⚪ AC-01', '✅ AC-01').replace('证据：—', '证据：验证通过'))
        checks.verify(self.root, relative)
        for old, new in [('修复提示', '增加提示'), ('显示结果', '显示新结果')]:
            card.write_text(initial.replace(old, new))
            with self.assertRaises(ValueError):
                checks.verify(self.root, relative)
        card.unlink()
        with self.assertRaises(ValueError):
            checks.verify(self.root, relative)

    def test_bound_requirement_preserves_explicit_project_context_input(self):
        import subprocess
        subprocess.run(['git', '-C', str(self.root), 'init', '-q'], check=True)
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        config_path = self.root / checks.CONFIG
        config = json.loads(config_path.read_text())
        config['profiles']['change']['inputs'] = ['source', 'requirements']
        config_path.write_text(json.dumps(config))
        directory = self.root / 'requirements'
        directory.mkdir()
        (directory / 'REQ-0001.md').write_text('<!-- teamflow:requirement:vnext -->\n- 范围：范围\n')
        context = directory / 'PROJECT-CONTEXT.md'
        context.write_text('工程配置入口')
        result, _ = checks.run(self.root, 'change', 'REQ-0001')
        relative = str(result.relative_to(self.root))
        (directory / 'REQ-0002.md').write_text('无关需求')
        checks.verify(self.root, relative)
        context.write_text('新的工程入口')
        with self.assertRaises(ValueError):
            checks.verify(self.root, relative)

    def test_staged_effective_config_and_bound_requirement(self):
        import subprocess
        def git(*args):
            subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
        git('init', '-q')
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        (self.root / 'requirements').mkdir()
        card = self.root / 'requirements/REQ-0001.md'
        card.write_text('<!-- teamflow:requirement:vnext -->\n- 范围：范围\n- ⚪ AC-01：结果\n')
        git('add', '.')
        result, _ = checks.run(self.root, 'change', 'REQ-0001')
        relative = str(result.relative_to(self.root))
        config_path = self.root / checks.CONFIG
        config = json.loads(config_path.read_text())
        config['profiles']['other'] = {'checks': {'other': {'argv': [sys.executable, '-c', 'pass']}}}
        config_path.write_text(json.dumps(config, indent=2))
        card.write_text(card.read_text().replace('⚪ AC-01', '✅ AC-01'))
        checks.verify(self.root, relative, staged=True)
        card.write_text(card.read_text().replace('结果', '新结果'))
        result, _ = checks.run(self.root, 'change', 'REQ-0001')
        relative = str(result.relative_to(self.root))
        with self.assertRaisesRegex(ValueError, '暂存内容'):
            checks.verify(self.root, relative, staged=True)
        git('add', 'requirements')
        checks.verify(self.root, relative, staged=True)
        config['profiles']['change']['checks']['ok']['timeout_seconds'] = 901
        config_path.write_text(json.dumps(config))
        result, _ = checks.run(self.root, 'change', 'REQ-0001')
        relative = str(result.relative_to(self.root))
        with self.assertRaisesRegex(ValueError, '暂存内容'):
            checks.verify(self.root, relative, staged=True)
        git('add', '.agents')
        checks.verify(self.root, relative, staged=True)

    def test_failure_returns_false(self):
        self.config({'fail': {'argv': [sys.executable, '-c', 'raise SystemExit(7)']}})
        path, passed = checks.run(self.root, 'change')
        self.assertFalse(passed)
        self.assertEqual('失败', json.loads(path.read_text())['status'])

    def test_empty_unknown_and_escape_rejected_before_execution(self):
        for commands in ({}, {'escape': {'argv': ['echo'], 'cwd': '../'}}, {'invalid': {}}):
            self.config(commands)
            with self.assertRaises(ValueError):
                checks.run(self.root, 'change')
        self.assertFalse((self.root / 'logs').exists())

    def test_other_profile_not_executed_and_profiles_required(self):
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        target = self.root / checks.CONFIG
        config = json.loads(target.read_text())
        config['profiles']['other'] = {'checks': {'bad': {'argv': [sys.executable, '-c', 'raise SystemExit(8)']}}}
        target.write_text(json.dumps(config))
        with self.assertRaises(ValueError):
            checks.run(self.root, 'absent')
        path, passed = checks.run(self.root, 'change')
        self.assertTrue(passed)
        self.assertEqual(['ok'], [r['name'] for r in json.loads(path.read_text())['results']])

    def test_symlink_log_directory_rejected(self):
        self.config({'ok': {'argv': ['echo', 'ok']}})
        (self.root / 'logs').symlink_to(self.root / '.agents', target_is_directory=True)
        with self.assertRaises(ValueError):
            checks.run(self.root, 'change')

    def test_source_edit_add_delete_and_config_change_invalidate(self):
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        source = self.root / 'source'
        source.unlink()
        source.mkdir()
        code = source / 'code.swift'
        code.write_text('one')
        path, passed = checks.run(self.root, 'change')
        self.assertTrue(passed)
        relative = str(path.relative_to(self.root))
        checks.verify(self.root, relative)
        code.write_text('two')
        with self.assertRaises(ValueError):
            checks.verify(self.root, relative)
        code.write_text('one')
        added = source / 'added.swift'
        added.write_text('new')
        with self.assertRaises(ValueError):
            checks.verify(self.root, relative)
        added.unlink()
        code.unlink()
        with self.assertRaises(ValueError):
            checks.verify(self.root, relative)
        code.write_text('one')
        self.config({'ok': {'argv': [sys.executable, '-c', 'print(1)']}})
        with self.assertRaises(ValueError):
            checks.verify(self.root, relative)

    def test_input_change_during_successful_command_is_not_pass(self):
        self.config({'mutate': {'argv': [sys.executable, '-c',
                    "from pathlib import Path; Path('source').write_text('changed')"]}})
        (self.root / 'source').write_text('before')
        path, passed = checks.run(self.root, 'change')
        self.assertFalse(passed)
        self.assertEqual(0, json.loads(path.read_text())['results'][0]['exit_code'])
        self.assertFalse(json.loads(path.read_text())['source_unchanged'])

    def test_requirement_snapshot_ignores_colored_status_and_ac_progress(self):
        pending = '''# REQ-0001
<!-- teamflow:requirement:vnext -->

- 状态：🔵 进行中
- ⚪ AC-01：显示结果

## 验证

- 验证状态：⚪ 未验证
'''.encode()
        completed = pending.replace('🔵 进行中'.encode(), '✅ 完成'.encode())
        completed = completed.replace('- ⚪ AC-01'.encode(), '- ✅ AC-01'.encode())
        self.assertEqual(checks.content_for_snapshot('requirements/REQ-0001.md', pending),
                         checks.content_for_snapshot('requirements/REQ-0001.md', completed))
        changed = completed.replace('显示结果'.encode(), '显示新结果'.encode())
        self.assertNotEqual(checks.content_for_snapshot('requirements/REQ-0001.md', pending),
                            checks.content_for_snapshot('requirements/REQ-0001.md', changed))

    def test_git_default_tracks_new_files_but_ignores_generated_evidence(self):
        import subprocess
        def git(*args):
            subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
        git('init', '-q')
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        config = self.root / checks.CONFIG
        data = json.loads(config.read_text())
        del data['profiles']['change']['inputs']
        config.write_text(json.dumps(data))
        (self.root / 'source.swift').write_text('source')
        (self.root / '.gitignore').write_text('build/\n')
        git('add', '.')
        path, passed = checks.run(self.root, 'change')
        self.assertTrue(passed)
        relative = str(path.relative_to(self.root))
        checks.verify(self.root, relative)
        (self.root / 'build').mkdir()
        (self.root / 'build/output').write_text('generated')
        checks.verify(self.root, relative)
        (self.root / 'new.swift').write_text('new')
        with self.assertRaises(ValueError):
            checks.verify(self.root, relative)
        (self.root / 'new.swift').unlink()
        (self.root / 'source.swift').chmod(0o755)
        with self.assertRaises(ValueError):
            checks.verify(self.root, relative)

    def test_staged_verification_rejects_old_missing_deleted_and_mode_inputs(self):
        import subprocess
        def git(*args):
            subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
        git('init', '-q')
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        config_path = self.root / checks.CONFIG
        config = json.loads(config_path.read_text())
        config['profiles']['change']['inputs'] = ['./source/']
        config_path.write_text(json.dumps(config))
        source = self.root / 'source'
        source.unlink()
        source.mkdir()
        code = source / 'code.swift'
        code.write_text('old')
        git('add', '.')
        code.write_text('fixed')
        path, passed = checks.run(self.root, 'change')
        relative = str(path.relative_to(self.root))
        checks.verify(self.root, relative)
        with self.assertRaisesRegex(ValueError, '暂存内容'):
            checks.verify(self.root, relative, staged=True)
        git('add', 'source')
        checks.verify(self.root, relative, staged=True)
        new = source / 'new.swift'
        new.write_text('new')
        path, _ = checks.run(self.root, 'change')
        with self.assertRaisesRegex(ValueError, '暂存内容'):
            checks.verify(self.root, str(path.relative_to(self.root)), staged=True)
        git('add', 'source')
        new.unlink()
        path, _ = checks.run(self.root, 'change')
        with self.assertRaisesRegex(ValueError, '暂存内容'):
            checks.verify(self.root, str(path.relative_to(self.root)), staged=True)
        git('add', '-u')
        code.chmod(0o755)
        path, _ = checks.run(self.root, 'change')
        with self.assertRaisesRegex(ValueError, '暂存内容'):
            checks.verify(self.root, str(path.relative_to(self.root)), staged=True)
        git('add', 'source')
        checks.verify(self.root, str(path.relative_to(self.root)), staged=True)

    def test_requirement_updates_skip_default_but_invalidate_document_profile(self):
        import subprocess
        subprocess.run(['git', '-C', str(self.root), 'init', '-q'], check=True)
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        config_path = self.root / checks.CONFIG
        config = json.loads(config_path.read_text())
        del config['profiles']['change']['inputs']
        config['profiles']['docs'] = {'inputs': ['requirements'],
                                      'checks': config['profiles']['change']['checks']}
        config_path.write_text(json.dumps(config))
        (self.root / 'requirements').mkdir()
        card = self.root / 'requirements/REQ-20260911-120000001Z-abcdef01.md'
        card.write_text('执行中')
        result, _ = checks.run(self.root, 'change')
        docs, _ = checks.run(self.root, 'docs')
        card.write_text('执行完成')
        checks.verify(self.root, str(result.relative_to(self.root)))
        with self.assertRaisesRegex(ValueError, '源码或配置已变化'):
            checks.verify(self.root, str(docs.relative_to(self.root)))


    def test_default_deletion_then_staging_preserves_verified_snapshot(self):
        import subprocess
        def git(*args):
            subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
        git('init', '-q')
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        path = self.root / checks.CONFIG
        config = json.loads(path.read_text()); del config['profiles']['change']['inputs']; path.write_text(json.dumps(config))
        source = self.root / 'removed.swift'; source.write_text('old')
        git('add', '.')
        source.unlink()
        result, passed = checks.run(self.root, 'change')
        self.assertTrue(passed)
        relative = str(result.relative_to(self.root))
        with self.assertRaisesRegex(ValueError, '暂存内容'):
            checks.verify(self.root, relative, staged=True)
        git('add', '-u')
        checks.verify(self.root, relative, staged=True)
        source.write_text('restored')
        with self.assertRaisesRegex(ValueError, '源码或配置'):
            checks.verify(self.root, relative, staged=True)

    def test_invalid_input_rejected_and_tracked_deletion_allowed(self):
        import subprocess
        def git(*args):
            return subprocess.check_output(['git', '-C', str(self.root), *args])
        git('init', '-q'); git('config', 'user.name', 'Fixture'); git('config', 'user.email', 'fixture@example.invalid')
        self.config({'unit': {'argv': [sys.executable, '-c', 'pass']}})
        config = checks.load_config(self.root)
        for name in ('missing-source', 'empty'):
            if name == 'empty':
                (self.root / name).mkdir()
            with self.assertRaisesRegex(ValueError, '无有效文件'):
                checks.source_snapshot(self.root, {'profiles': {'change': {
                    **config['profiles']['change'], 'inputs': [name]}}}, 'change')
        git('add', '.'); git('commit', '-qm', 'initial')
        (self.root / 'source').unlink()
        deleted = checks.source_snapshot(self.root, config, 'change')
        git('add', '-u')
        self.assertEqual(deleted, checks.source_snapshot(self.root, config, 'change', staged=True))
        git('commit', '-qm', 'delete')
        self.assertEqual(deleted, checks.source_snapshot(self.root, config, 'change'))

    def test_cli_original_output_failure_and_complete_logs(self):
        import subprocess
        command = [sys.executable, str(ROOT / 'scripts/teamflow.py'),
                   '--project', str(self.root), 'verify', 'run', '--profile', 'change']
        self.config({'ok': {'argv': [sys.executable, '-c', 'print("raw-output-" * 2000)']}})
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(2, len(result.stdout.splitlines()))
        self.assertEqual('ok：通过', result.stdout.splitlines()[0])
        self.assertNotIn('raw-output-', result.stdout)
        target = Path(result.stdout.split('验证证据：')[1].strip())
        self.assertEqual('raw-output-' * 2000 + '\n', (target.parent / 'ok.log').read_text())
        self.config({'fail': {'argv': [sys.executable, '-c', 'print("failure detail"); raise SystemExit(7)']},
                     'missing': {'argv': ['/no-such-tool']},
                     'slow': {'argv': [sys.executable, '-c', 'import time; time.sleep(30)'], 'timeout_seconds': 1}})
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(1, failed.returncode)
        for expected in ('fail：失败', 'missing：无法执行', 'slow：超时'):
            self.assertIn(expected, failed.stdout)
        target = Path(failed.stdout.split('验证证据：')[1].strip())
        self.assertEqual(['失败', '无法执行', '超时'], [r['status'] for r in json.loads(target.read_text())['results']])
        self.assertEqual('failure detail\n', (target.parent / 'fail.log').read_text())
        self.config({'mutate': {'argv': [sys.executable, '-c', 'from pathlib import Path; Path("source").write_text("changed")']}})
        changed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(1, changed.returncode)
        target = Path(changed.stdout.split('验证证据：')[1].strip())
        self.assertEqual('输入已变化，需重测', json.loads(target.read_text())['status'])
