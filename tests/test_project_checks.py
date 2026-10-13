import importlib.util
import json
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/skills/ios-team-flow/scripts"))
spec = importlib.util.spec_from_file_location('project_checks', ROOT / '.agents/skills/ios-team-flow/scripts/project_checks.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


R1, R2 = 'REQ-20260101-0001', 'REQ-20260101-0002'


def card(scope, acs, excluded='无', state='进行中', title='标题', requirement=R1):
    lines = ''.join(f'- [{"x" if done else " "}] {name}：{text}\n' for name, text, done in acs)
    return (f'---\nid: {requirement}\nstate: {state}\n---\n\n# {title}\n\n## 范围\n\n{scope}\n\n'
            f'## 不包含\n\n{excluded}\n\n## 验收条件\n\n{lines}')


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

    def test_compact_report_rejects_missing_or_mismatched_end_fingerprint(self):
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        path, passed = checks.run(self.root, 'change')
        self.assertTrue(passed)
        original = json.loads(path.read_text())
        self.assertEqual(original['source']['fingerprint'], original['end_fingerprint'])
        self.assertNotIn('source_changes', original)
        self.assertNotIn('source_before', original)
        self.assertNotIn('source_after', original)
        for end in (None, 'incorrect'):
            path.write_text(json.dumps({**original, 'end_fingerprint': end}))
            with self.assertRaises(ValueError):
                checks.verify(self.root, str(path.relative_to(self.root)))

    def test_changed_report_records_added_removed_and_modified_files(self):
        import subprocess
        subprocess.run(['git', '-C', str(self.root), 'init', '-q'], check=True)
        source = self.root / 'source'; source.unlink(); source.mkdir()
        (source / 'removed').write_text('old')
        (source / 'modified').write_text('old')
        self.config({'mutate': {'argv': [sys.executable, '-c',
            "from pathlib import Path; Path('source/removed').unlink(); "
            "Path('source/modified').write_text('new'); Path('source/added').write_text('new')"]}})
        path, passed = checks.run(self.root, 'change')
        self.assertFalse(passed)
        changes = json.loads(path.read_text())['source_changes']
        self.assertEqual(['source/removed'], changes['removed'])
        self.assertEqual(['source/added'], list(changes['added']))
        self.assertEqual(['source/modified'], list(changes['modified']))

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
        path = directory / (R1 + '.md')
        initial = card('修复提示', [('AC-01', '显示结果', False)])
        path.write_text(initial)
        result, passed = checks.run(self.root, 'change', R1)
        self.assertTrue(passed)
        relative = str(result.relative_to(self.root))
        (directory / (R2 + '.md')).write_text('其他需求')
        path.write_text(card('修复提示', [('AC-01', '显示结果', True)], state='待用户验证')
                        .replace('state: 待用户验证', 'state: 待用户验证\nevidence:\n  kind: result'))
        checks.verify(self.root, relative)
        for old, new in [('修复提示', '增加提示'), ('显示结果', '显示新结果')]:
            path.write_text(initial.replace(old, new))
            with self.assertRaises(ValueError):
                checks.verify(self.root, relative)
        path.unlink()
        with self.assertRaises(ValueError):
            checks.verify(self.root, relative)

    def test_requirement_semantics_ignore_display_but_track_scope_exclusions_and_conditions(self):
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        directory = self.root / 'requirements'; directory.mkdir()
        path = directory / (R1 + '.md')
        original = card('显示结果', [('AC-01', '文字正确', False), ('AC-02', '点击有效', False)], excluded='支付')
        path.write_text(original)
        result, _ = checks.run(self.root, 'change', R1)
        relative = str(result.relative_to(self.root))
        display = original.replace('标题', '新标题').replace('\n显示结果\n', '\n  显示结果  \n')
        display = display.replace('- [ ] AC-01：文字正确', '  - [x] AC-01：  文字正确  ')
        path.write_text(display + '\n## 决策与异常\n说明\n')
        checks.verify(self.root, relative)
        for old, new in [('显示结果', '隐藏结果'), ('支付', '登录'), ('点击有效', '点击无效')]:
            path.write_text(original.replace(old, new))
            with self.assertRaisesRegex(ValueError, '源码或配置已变化'):
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
        (directory / (R1 + '.md')).write_text(card('范围', [('AC-01', '结果', False)]))
        context = directory / 'PROJECT-CONTEXT.md'
        context.write_text('工程配置入口')
        result, _ = checks.run(self.root, 'change', R1)
        relative = str(result.relative_to(self.root))
        (directory / (R2 + '.md')).write_text('无关需求')
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
        path = self.root / 'requirements' / (R1 + '.md')
        path.write_text(card('范围', [('AC-01', '结果', False)]))
        git('add', '.')
        result, _ = checks.run(self.root, 'change', R1)
        relative = str(result.relative_to(self.root))
        config_path = self.root / checks.CONFIG
        config = json.loads(config_path.read_text())
        config['profiles']['other'] = {'checks': {'other': {'argv': [sys.executable, '-c', 'pass']}}}
        config_path.write_text(json.dumps(config, indent=2))
        path.write_text(path.read_text().replace('- [ ] AC-01', '- [x] AC-01'))
        checks.verify(self.root, relative, staged=True)
        path.write_text(path.read_text().replace('结果', '新结果'))
        result, _ = checks.run(self.root, 'change', R1)
        relative = str(result.relative_to(self.root))
        with self.assertRaisesRegex(ValueError, '暂存内容'):
            checks.verify(self.root, relative, staged=True)
        git('add', 'requirements')
        checks.verify(self.root, relative, staged=True)
        config['profiles']['change']['checks']['ok']['timeout_seconds'] = 901
        config_path.write_text(json.dumps(config))
        result, _ = checks.run(self.root, 'change', R1)
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
        report = json.loads(path.read_text())
        self.assertNotEqual(report['source']['fingerprint'], report['end_fingerprint'])
        self.assertEqual(['source'], list(report['source_changes']['modified']))
        with self.assertRaises(ValueError):
            checks.verify(self.root, str(path.relative_to(self.root)))

    def test_requirement_snapshot_ignores_status_and_ac_progress(self):
        name = 'requirements/' + R1 + '.md'
        pending = card('显示提示', [('AC-01', '显示结果', False)]).encode()
        completed = card('显示提示', [('AC-01', '显示结果', True)], state='完成').encode()
        self.assertEqual(checks.content_for_snapshot(name, pending), checks.content_for_snapshot(name, completed))
        changed = completed.replace('显示结果'.encode(), '显示新结果'.encode())
        self.assertNotEqual(checks.content_for_snapshot(name, pending), checks.content_for_snapshot(name, changed))

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
        card = self.root / 'requirements/PROJECT-CONTEXT.md'
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

    def test_staged_batch_preserves_binary_contents_and_uses_one_process(self):
        import subprocess
        subprocess.run(['git', '-C', str(self.root), 'init', '-q'], check=True)
        source = self.root / 'source'; source.unlink(); source.mkdir()
        for name, data in [('含空格 file.bin', b'\x00\xff\n12 blob 3\nabc'), ('empty', b''),
                           ('duplicate', b'\x00\xff\n12 blob 3\nabc')]:
            (source / name).write_bytes(data)
        self.config({'ok': {'argv': [sys.executable, '-c', 'pass']}})
        subprocess.run(['git', '-C', str(self.root), 'add', '.'], check=True)
        config = checks.load_config(self.root)
        expected = checks.source_snapshot(self.root, config, 'change')
        with patch.object(checks.subprocess, 'run', wraps=subprocess.run) as runner:
            actual = checks.source_snapshot(self.root, config, 'change', staged=True)
        self.assertEqual(expected, actual)
        batches = [c for c in runner.call_args_list if 'cat-file' in c.args[0]]
        self.assertEqual(1, len(batches))
        self.assertIn('--batch', batches[0].args[0])

    def test_cli_brief_output_failure_and_complete_logs(self):
        import subprocess
        command = [sys.executable, str(ROOT / 'scripts/teamflow.py'),
                   '--project', str(self.root), 'verify', 'run', '--profile', 'change']
        latest = lambda: max((self.root / 'logs/project-checks').glob('*/result.json'), key=lambda p: p.stat().st_mtime_ns)
        self.config({'ok': {'argv': [sys.executable, '-c', 'print("raw-output-" * 2000)']}})
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('验证：通过（change）\n', result.stdout)
        self.assertEqual('raw-output-' * 2000 + '\n', (latest().parent / 'ok.log').read_text())
        self.config({'fail': {'argv': [sys.executable, '-c', 'print("failure detail"); raise SystemExit(7)']},
                     'missing': {'argv': ['/no-such-tool']},
                     'slow': {'argv': [sys.executable, '-c', 'import time; time.sleep(30)'], 'timeout_seconds': 1}})
        failed = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(1, failed.returncode)
        self.assertEqual(1, len(failed.stdout.splitlines()))
        for expected in ('验证：失败（change）', 'fail 失败（logs/project-checks/', 'missing 无法执行', 'slow 超时'):
            self.assertIn(expected, failed.stdout)
        target = latest()
        self.assertEqual(['失败', '无法执行', '超时'], [r['status'] for r in json.loads(target.read_text())['results']])
        self.assertEqual('failure detail\n', (target.parent / 'fail.log').read_text())
        self.config({'mutate': {'argv': [sys.executable, '-c', 'from pathlib import Path; Path("source").write_text("changed")']}})
        changed = subprocess.run(command + ['--json'], capture_output=True, text=True)
        self.assertEqual(1, changed.returncode)
        self.assertEqual('输入已变化，需重测', json.loads(changed.stdout)['status'])
