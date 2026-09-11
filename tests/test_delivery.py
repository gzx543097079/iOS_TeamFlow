import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('delivery', ROOT / '.agents/skills/ios-team-flow/scripts/delivery.py')
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)
REQ = 'REQ-20260911-999'


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        d.git(self.root, 'init', '-q')
        d.git(self.root, 'config', 'user.name', 'Test')
        d.git(self.root, 'config', 'user.email', 'test@example.invalid')
        (self.root / 'requirements').mkdir()
        (self.root / 'requirements' / (REQ + '.md')).write_text('# 需求')
        self.commit('one', 'Requirement: ' + REQ)

    def commit(self, content, message):
        (self.root / 'code.txt').write_text(content)
        d.git(self.root, 'add', '.')
        d.git(self.root, 'commit', '-qm', message)
        return d.resolve(self.root, 'HEAD')

    def test_local_commit_and_tag_not_release_or_merge(self):
        d.git(self.root, 'tag', 'v1')
        path, data = d.load(self.root, REQ)
        d.refresh(self.root, data)
        self.assertTrue(data['snapshot']['committed'])
        self.assertEqual('未核实', data['snapshot']['merged'])
        self.assertEqual([], data['snapshot']['releases'])
        d.save(self.root, path, data, 'refresh')
        self.assertIn(REQ, (self.root / 'requirements/DELIVERY.md').read_text())

    def test_complete_stales_when_implementation_changes(self):
        _, data = d.load(self.root, REQ)
        data['development'] = {'state': '✅ 开发完成', 'commits': d.commits_for(self.root, REQ)}
        self.commit('two', 'Requirement: ' + REQ)
        d.refresh(self.root, data)
        self.assertIn('需复核', data['snapshot']['development'])

    def test_verified_merge_release_and_draft(self):
        sha = d.resolve(self.root, 'HEAD')
        d.git(self.root, 'tag', 'v1')
        _, data = d.load(self.root, REQ)
        data['prs'] = ['https://github.com/example/repo/pull/1']
        pr = {'state': 'MERGED', 'mergedAt': 'date', 'mergeCommit': {'oid': sha}, 'commits': [{'oid': sha}]}
        release = {'isDraft': False, 'isPrerelease': False, 'publishedAt': 'date', 'url': 'https://example.invalid/v1'}
        with patch.object(d, 'gh_json', side_effect=[pr, release]), patch.object(d, 'remote_tag_commit', return_value=sha):
            d.refresh(self.root, data, True)
        self.assertEqual('✅ 已合并', data['snapshot']['merged'])
        self.assertEqual('✅ 已发布', data['snapshot']['release_status'])
        release['isDraft'] = True
        with patch.object(d, 'gh_json', side_effect=[pr, release]), patch.object(d, 'remote_tag_commit', return_value=sha):
            d.refresh(self.root, data, True)
        self.assertEqual([], data['snapshot']['releases'])

    def test_remote_tag_mismatch_not_published(self):
        d.git(self.root, 'tag', 'v1')
        _, data = d.load(self.root, REQ)
        release = {'isDraft': False, 'isPrerelease': False, 'publishedAt': 'date', 'url': 'https://example.invalid/v1'}
        with patch.object(d, 'gh_json', return_value=release), patch.object(d, 'remote_tag_commit', return_value='different'):
            d.refresh(self.root, data, True)
        self.assertEqual([], data['snapshot']['releases'])
        self.assertIn('未核实', data['snapshot']['release_status'])

    def test_old_release_does_not_cover_new_commit(self):
        d.git(self.root, 'tag', 'v1')
        self.commit('two', 'Requirement: ' + REQ)
        _, data = d.load(self.root, REQ)
        with patch.object(d, 'gh_json') as gh:
            d.refresh(self.root, data, True)
            gh.assert_not_called()
        self.assertEqual([], data['snapshot']['releases'])

    def test_remote_failure_not_marked_pass(self):
        _, data = d.load(self.root, REQ)
        data['prs'] = ['https://github.com/example/repo/pull/1']
        with patch.object(d, 'gh_json', side_effect=OSError('offline')):
            d.refresh(self.root, data, True)
        self.assertNotEqual('✅ 已合并', data['snapshot']['merged'])
        self.assertTrue(data['snapshot']['warnings'])

    def test_metadata_only_commit_not_implementation(self):
        expected = d.commits_for(self.root, REQ)
        (self.root / 'requirements/DELIVERY.md').write_text('归档')
        d.git(self.root, 'add', '.')
        d.git(self.root, 'commit', '-qm', 'Requirement: ' + REQ)
        self.assertEqual(expected, d.commits_for(self.root, REQ))

    def test_bad_id_and_unknown_commit_rejected(self):
        with self.assertRaises(ValueError):
            d.load(self.root, '../bad')
        with self.assertRaises(subprocess.CalledProcessError):
            d.resolve(self.root, 'not-found')

    def test_finish_updates_stale_card_and_reports_without_approving(self):
        card = self.root / 'requirements' / (REQ + '.md')
        card.write_text('# 需求\n- Git 状态：未提交\n- 产品验收：待确认\n')
        self.assertFalse(d.finish(self.root, [REQ], check=True))
        self.assertIn('未提交', card.read_text())
        self.assertTrue(d.finish(self.root, [REQ]))
        self.assertIn(d.resolve(self.root, 'HEAD'), card.read_text())
        self.assertIn('产品验收：待确认', card.read_text())
        self.assertTrue(d.finish(self.root, [REQ], check=True))
        (self.root / 'requirements/DELIVERY.md').unlink()
        self.assertFalse(d.finish(self.root, [REQ], check=True))
        self.assertTrue(d.finish(self.root, [REQ]))
        self.assertTrue(d.finish(self.root, [REQ], check=True))
        _, record = d.load(self.root, REQ)
        self.assertEqual('未登记', record['development']['state'])
        self.assertEqual('- Git 状态：未提交', record['card_history'][0]['previous_git_status'])
        self.commit('next', 'Requirement: ' + REQ)
        self.assertFalse(d.finish(self.root, [REQ], check=True))
