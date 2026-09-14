"""从独立 ZIP 验证日志源码安装，不用文件存在替代实际工程构建。"""
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import package_release


class LoggingInstallTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with contextlib.redirect_stdout(io.StringIO()):
            cls.archive = package_release.package_skill(ROOT)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        with zipfile.ZipFile(self.archive) as archive:
            archive.extractall(self.root / '.agents/skills')
        self.script = self.root / '.agents/skills/ios-team-flow/scripts/install_logging.py'

    def run_install(self, language='mixed', destination='App/Sources/Logging'):
        return subprocess.run([sys.executable, str(self.script), '--project', str(self.root),
                               '--language', language, '--destination', destination],
                              capture_output=True, text=True)

    def test_language_selection_and_idempotence_from_zip(self):
        for language, names in [('swift', {'TFLogger.swift'}), ('objc', {'TFLogger.h', 'TFLogger.m'}),
                                ('mixed', {'TFLogger.h', 'TFLogger.m', 'TFLogger.swift'})]:
            destination = 'App/' + language
            first = self.run_install(language, destination)
            self.assertEqual(0, first.returncode, first.stderr)
            self.assertEqual(names, {Path(p).name for p in json.loads(first.stdout)['files']})
            folder = self.root / destination
            before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()}
            second = self.run_install(language, destination)
            self.assertEqual(0, second.returncode, second.stderr)
            self.assertEqual([], json.loads(second.stdout)['created'])
            self.assertEqual(before, {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in folder.iterdir()})

    def test_conflict_is_preflighted_before_any_copy(self):
        folder = self.root / 'App/Sources/Logging'
        folder.mkdir(parents=True)
        (folder / 'TFLogger.m').write_text('team customization')
        result = self.run_install()
        self.assertEqual(2, result.returncode)
        self.assertEqual(['TFLogger.m'], [p.name for p in folder.iterdir()])
        self.assertEqual('team customization', (folder / 'TFLogger.m').read_text())

    def test_paths_and_external_tool_rejected(self):
        for destination in ('../outside', str(self.root / 'absolute'), '.agents/overwrite'):
            self.assertEqual(2, self.run_install(destination=destination).returncode)
        (self.root / 'App').symlink_to(self.root / '.agents', target_is_directory=True)
        self.assertEqual(2, self.run_install().returncode)
        result = subprocess.run([sys.executable, str(self.script), '--project', str(self.root / 'Other'),
                                 '--language', 'swift', '--destination', 'Sources'], capture_output=True)
        self.assertEqual(2, result.returncode)
