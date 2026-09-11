import importlib.util
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.agents/skills/ios-team-flow'
spec = importlib.util.spec_from_file_location('upgrade_skill', SOURCE / 'scripts/upgrade_skill.py')
u = importlib.util.module_from_spec(spec)
spec.loader.exec_module(u)


class SkillUpgradeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve() / 'project'
        self.skill = self.root / u.PREFIX
        shutil.copytree(SOURCE, self.skill, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        u.setup.setup(self.root, self.skill)
        self.original = u.installed_files(self.root)
        self.base = self.archive('old.zip', self.original)
        self.new = dict(self.original)
        current = tuple(map(int, self.original['references/VERSION'].decode().strip().split('.')))
        self.new['references/VERSION'] = f'{current[0]}.{current[1] + 1}.0\n'.encode()
        self.new['references/new.md'] = b'new upstream'

    def archive(self, name, files):
        path = self.root.parent / name
        with zipfile.ZipFile(path, 'w') as output:
            for relative, data in files.items():
                output.writestr('ios-team-flow/' + relative, data)
        return path

    def files(self):
        return {str(p.relative_to(self.root)): p.read_bytes() for p in self.root.rglob('*')
                if p.is_file() and '__pycache__' not in p.parts}

    def test_preview_preserves_customization_apply_and_restore_all(self):
        custom = self.skill / 'references/README.md'
        custom.write_text(custom.read_text() + '\nTeam custom rule\n')
        snapshot = self.files()
        archive = self.archive('new.zip', self.new)
        u.upgrade(self.root, archive, self.base)
        self.assertEqual(snapshot, self.files())
        backup = u.upgrade(self.root, archive, self.base, True)
        self.assertIn('Team custom rule', custom.read_text())
        self.assertEqual(self.new['references/VERSION'], (self.skill / 'references/VERSION').read_bytes())
        self.assertIsNone(u.upgrade(self.root, archive, apply=True))
        u.setup.recover(self.root, backup / 'transaction.json')
        for name, content in snapshot.items():
            self.assertEqual(content, (self.root / name).read_bytes(), name)
        self.assertFalse((self.skill / 'references/new.md').exists())
        self.assertFalse((self.root / u.BASELINE).exists())

    def test_both_sides_edit_conflict_writes_nothing(self):
        (self.skill / 'references/README.md').write_text('team')
        self.new['references/README.md'] = b'upstream'
        snapshot = self.files()
        with self.assertRaisesRegex(ValueError, '同时修改'):
            u.upgrade(self.root, self.archive('new.zip', self.new), self.base, True)
        self.assertEqual(snapshot, self.files())

    def test_missing_baseline_and_traversal_rejected(self):
        with self.assertRaisesRegex(ValueError, 'base-archive'):
            u.upgrade(self.root, self.archive('new.zip', self.new), apply=True)
        with self.assertRaises(ValueError):
            u.archive_files(self.archive('bad.zip', {'../../outside': b'bad'}))

    def test_upstream_removal_and_write_failure_restore_whole_skill(self):
        del self.new['references/README.md']
        archive = self.archive('new.zip', self.new)
        before = u.installed_files(self.root)
        real = u.setup.atomic_write
        def fail(path, content, mode=0o644):
            if path == self.skill / 'references/new.md':
                raise OSError('injected')
            real(path, content, mode)
        with patch.object(u.setup, 'atomic_write', side_effect=fail):
            with self.assertRaisesRegex(OSError, '已恢复'):
                u.upgrade(self.root, archive, self.base, True)
        self.assertEqual(before, u.installed_files(self.root))
        self.assertFalse((self.root / u.BASELINE).exists())

    def test_restore_preserves_changes_made_after_upgrade(self):
        backup = u.upgrade(self.root, self.archive('new.zip', self.new), self.base, True)
        (self.skill / 'references/README.md').write_text('after upgrade edit')
        with self.assertRaisesRegex(ValueError, '冲突'):
            u.setup.recover(self.root, backup / 'transaction.json')
        self.assertEqual('after upgrade edit', (self.skill / 'references/README.md').read_text())

    def test_explicit_merged_file_resolves_both_sides_without_losing_rule(self):
        (self.skill / 'references/README.md').write_text('team')
        self.new['references/README.md'] = b'upstream'
        merged = self.root.parent / 'merged'
        (merged / 'references').mkdir(parents=True)
        (merged / 'references/README.md').write_text('upstream and team')
        u.upgrade(self.root, self.archive('new.zip', self.new), self.base, True, merged)
        self.assertEqual('upstream and team', (self.skill / 'references/README.md').read_text())
        record = json.loads((self.root / u.BASELINE).read_text())
        self.assertEqual(u.digest(b'upstream'), record['files']['references/README.md'])

    def test_removed_upstream_file_restored_after_successful_upgrade(self):
        del self.new['references/README.md']
        backup = u.upgrade(self.root, self.archive('new.zip', self.new), self.base, True)
        self.assertFalse((self.skill / 'references/README.md').exists())
        u.setup.recover(self.root, backup / 'transaction.json')
        self.assertEqual(self.original['references/README.md'], (self.skill / 'references/README.md').read_bytes())
