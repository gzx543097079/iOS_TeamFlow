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
        self.root = Path(self.temp.name)
        (self.root / '.agents').mkdir()

    def config(self, commands, selected=None):
        data = {'schema_version': 1, 'checks': commands,
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
