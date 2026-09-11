import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
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

    def config(self, commands, selected=None):
        data = {'schema_version': 1, 'inputs': ['source'], 'checks': commands,
                'profiles': {'change': list(commands) if selected is None else selected}}
        (self.root / checks.CONFIG).write_text(json.dumps(data))

    def test_success_and_literal_arguments(self):
        self.config({'build': {'argv': [sys.executable, '-c', 'import sys; print(sys.argv[1])', 'a b;$(echo test)']}})
        path, passed = checks.run(self.root, 'change')
        self.assertTrue(passed)
        self.assertEqual('a b;$(echo test)\n', (path.parent / 'build.log').read_text())
        self.assertEqual(0, json.loads(path.read_text())['results'][0]['exit_code'])

    def test_failure_missing_tool_timeout_are_not_passes(self):
        self.config({'fail': {'argv': [sys.executable, '-c', 'raise SystemExit(7)']},
                     'missing': {'argv': ['/no-such-tool']},
                     'slow': {'argv': [sys.executable, '-c', 'import time; time.sleep(30)'], 'timeout_seconds': 1}})
        path, passed = checks.run(self.root, 'change')
        self.assertFalse(passed)
        self.assertEqual(['失败', '无法执行', '超时'], [r['status'] for r in json.loads(path.read_text())['results']])

    def test_empty_unknown_and_escape_rejected_before_execution(self):
        for commands, selected in [({}, []), ({'ok': {'argv': ['echo']}}, ['unknown']),
                                   ({'escape': {'argv': ['echo'], 'cwd': '../'}}, ['escape'])]:
            self.config(commands, selected)
            with self.assertRaises(ValueError):
                checks.run(self.root, 'change')
        self.assertFalse((self.root / 'logs').exists())

    def test_unselected_command_not_executed_and_profiles_required(self):
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']},
                     'bad': {'argv': [sys.executable, '-c', 'raise SystemExit(8)']}}, ['ok'])
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

    def test_git_default_tracks_new_files_but_ignores_generated_evidence(self):
        import subprocess
        def git(*args):
            subprocess.run(['git', '-C', str(self.root), *args], check=True, capture_output=True)
        git('init', '-q')
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        config = self.root / checks.CONFIG
        data = json.loads(config.read_text())
        del data['inputs']
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
        config['inputs'] = ['./source/']
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
        del config['inputs']
        config['profiles']['docs'] = ['ok']
        config['profile_inputs'] = {'docs': ['requirements']}
        config_path.write_text(json.dumps(config))
        (self.root / 'requirements').mkdir()
        card = self.root / 'requirements/REQ-20260911-001.md'
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
        config = json.loads(path.read_text()); del config['inputs']; path.write_text(json.dumps(config))
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
                checks.source_snapshot(self.root, {**config, 'inputs': [name]}, 'change')
        git('add', '.'); git('commit', '-qm', 'initial')
        (self.root / 'source').unlink()
        deleted = checks.source_snapshot(self.root, config, 'change')
        git('add', '-u')
        self.assertEqual(deleted, checks.source_snapshot(self.root, config, 'change', staged=True))
        git('commit', '-qm', 'delete')
        self.assertEqual(deleted, checks.source_snapshot(self.root, config, 'change'))

    def test_cli_summary_verbose_failure_and_complete_logs(self):
        import subprocess
        command = [sys.executable, str(ROOT / '.agents/skills/ios-team-flow/scripts/project_checks.py'),
                   '--project', str(self.root), 'run', '--profile', 'change']
        self.config({'ok': {'argv': [sys.executable, '-c', 'print("raw-output-" * 2000)']}})
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('验证结果：通过；检查数：1', result.stdout)
        self.assertNotIn('ok：通过', result.stdout)
        self.assertNotIn('raw-output-', result.stdout)
        target = Path(result.stdout.split('验证证据：')[1].strip())
        self.assertEqual('raw-output-' * 2000 + '\n', (target.parent / 'ok.log').read_text())
        verbose = subprocess.run(command + ['--verbose'], capture_output=True, text=True)
        self.assertEqual(0, verbose.returncode)
        self.assertIn('ok：通过', verbose.stdout)
        self.config({'fail': {'argv': [sys.executable, '-c', 'print("failure detail"); raise SystemExit(7)']},
                     'missing': {'argv': ['/no-such-tool']},
                     'slow': {'argv': [sys.executable, '-c', 'import time; time.sleep(30)'], 'timeout_seconds': 1}})
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(1, failed.returncode)
        for expected in ('fail：失败；退出码：7', 'missing：无法执行', 'slow：超时', '验证结果：失败'):
            self.assertIn(expected, failed.stdout)
        target = Path(failed.stdout.split('验证证据：')[1].strip())
        self.assertEqual('failure detail\n', (target.parent / 'fail.log').read_text())
        self.config({'mutate': {'argv': [sys.executable, '-c', 'from pathlib import Path; Path("source").write_text("changed")']}})
        changed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(1, changed.returncode)
        self.assertIn('输入已变化，需重测', changed.stdout)
