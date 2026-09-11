import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / '.agents/skills/ios-team-flow/scripts/setup_project.py'
spec = importlib.util.spec_from_file_location('setup_recovery', SOURCE)
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class RecoveryTests(unittest.TestCase):
    def test_failure_restores_existing_and_removes_new_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'AGENTS.md').write_bytes(b'original')
            (root / 'AGENTS.md').chmod(0o640)
            real = setup.atomic_write
            def fail(path, content, mode=0o644):
                if path == root / 'scripts/review_gate.py' and content == b'new':
                    raise OSError('injected write failure')
                real(path, content, mode)
            with patch.object(setup, 'atomic_write', side_effect=fail):
                with self.assertRaisesRegex(OSError, '已恢复'):
                    setup.apply_transaction(root, {'AGENTS.md': b'changed', '.agents/teamflow.json': b'new',
                                                   'scripts/review_gate.py': b'new'},
                                            {'AGENTS.md': b'original', '.agents/teamflow.json': None,
                                             'scripts/review_gate.py': None})
            self.assertEqual((root / 'AGENTS.md').read_bytes(), b'original')
            self.assertEqual((root / 'AGENTS.md').stat().st_mode & 0o777, 0o640)
            self.assertFalse((root / '.agents/teamflow.json').exists())

    def test_manual_recovery_preflights_changes_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'AGENTS.md').write_bytes(b'old')
            backup = setup.apply_transaction(root, {'AGENTS.md': b'new'}, {'AGENTS.md': b'old'})
            journal = backup / 'transaction.json'
            (root / 'AGENTS.md').write_bytes(b'user changes')
            with self.assertRaisesRegex(ValueError, '冲突'):
                setup.recover(root, journal)
            self.assertEqual((root / 'AGENTS.md').read_bytes(), b'user changes')
            (root / 'AGENTS.md').write_bytes(b'new')
            setup.recover(root, journal)
            setup.recover(root, journal)
            self.assertEqual((root / 'AGENTS.md').read_bytes(), b'old')
            (root / 'AGENTS.md').unlink()
            (root / 'AGENTS.md').symlink_to(journal)
            with self.assertRaisesRegex(ValueError, '符号链接'):
                setup.recover(root, journal)

    def test_interrupted_install_requires_recovery(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            skill = root / '.agents/skills/ios-team-flow'
            shutil.copytree(SOURCE.parents[1], skill)
            real = setup.atomic_write
            def interrupt(path, content, mode=0o644):
                if path == root / 'scripts/review_gate.py':
                    raise KeyboardInterrupt()
                real(path, content, mode)
            with patch.object(setup, 'atomic_write', side_effect=interrupt):
                with self.assertRaises(KeyboardInterrupt):
                    setup.setup(root, skill)
            with self.assertRaisesRegex(ValueError, '中断'):
                setup.setup(root, skill)
            journal = next((root / '.agents/teamflow-backups').glob('*/transaction.json'))
            setup.recover(root, journal)
            setup.setup(root, skill)
            self.assertTrue((root / 'AGENTS.md').exists())
