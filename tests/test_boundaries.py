import contextlib
import io
import json
import unittest
from pathlib import Path
import test_teamflow

flow = test_teamflow.flow


class BoundaryTests(unittest.TestCase):
    setUp = test_teamflow.TeamFlowTests.setUp
    git = test_teamflow.TeamFlowTests.git
    configure_checks = test_teamflow.TeamFlowTests.configure_checks
    create = test_teamflow.TeamFlowTests.create
    fill = test_teamflow.TeamFlowTests.fill

    def test_uncovered_staged_code_rejected(self):
        req = self.create(); self.fill(req)
        flow.complete(self.root, req, profile='change')
        (self.root / 'Untested.swift').write_text('let broken = 1')
        self.git('add', '.')
        with self.assertRaisesRegex(ValueError, '未覆盖'):
            flow.git_check(self.root, req)

    def test_uncovered_deleted_code_rejected(self):
        req = self.create(); self.fill(req)
        code = self.root / 'Old.swift'; code.write_text('let a = 1')
        self.git('add', '.'); self.git('commit', '-qm', 'baseline')
        code.unlink(); self.git('add', '-u')
        flow.complete(self.root, req, profile='change')
        self.git('add', 'requirements')
        with self.assertRaisesRegex(ValueError, '未覆盖'):
            flow.git_check(self.root, req)

    def test_manual_cannot_replace_configured_code_checks(self):
        req = self.create(); path = self.fill(req)
        (self.root / 'Business.swift').write_text('let a = 1')
        original = path.read_bytes()
        with self.assertRaisesRegex(ValueError, '自动验证'):
            flow.complete(self.root, req, evidence='看过代码')
        self.assertEqual(original, path.read_bytes())

    def test_manual_directory_addition_and_partial_staging_invalidate(self):
        req = self.create(); self.fill(req)
        directory = self.root / 'docs'; directory.mkdir()
        doc = directory / 'a.md'; doc.write_text('old')
        self.git('add', 'docs', 'requirements')
        flow.complete(self.root, req, evidence='核对文档', evidence_inputs=['docs'])
        (directory / 'b.md').write_text('new')
        with self.assertRaisesRegex(ValueError, '人工证据'):
            flow.complete(self.root, req)
        flow.complete(self.root, req, evidence='重新核对', evidence_inputs=['docs'])
        doc.write_text('changed after stage')
        with self.assertRaisesRegex(ValueError, '暂存'):
            flow.git_check(self.root, req, evidence='已看新内容', evidence_inputs=['docs'])

    def test_manual_source_change_and_staged_code_rejected(self):
        req = self.create(); self.fill(req)
        flow.complete(self.root, req, evidence='实际核对')
        (self.root / 'source.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError, '人工证据'):
            flow.complete(self.root, req)
        (self.root / 'Business.swift').write_text('let a = 1')
        self.git('add', '.')
        with self.assertRaisesRegex(ValueError, '自动验证'):
            flow.git_check(self.root, req, evidence='看过了')

    def test_placeholder_and_stopped_card_rejected(self):
        req = self.create()
        with self.assertRaisesRegex(ValueError, '占位'):
            flow.complete(self.root, req, evidence='实际核对', confirm_ac=['AC-01'])
        path = self.fill(req)
        for state in ('暂停', '取消'):
            flow.set_state(self.root, req, state, '用户要求')
            original = path.read_text()
            with self.assertRaisesRegex(ValueError, '恢复'):
                flow.complete(self.root, req, profile='change')
            self.assertEqual(original, path.read_text())

    def test_list_does_not_follow_symlink(self):
        req = self.create(); card = self.fill(req)
        target = self.root / 'real.md'; card.rename(target); card.symlink_to(target)
        self.assertEqual([], flow.cards(self.root))

    def test_manual_scope_reuse_and_uncovered_document(self):
        req = self.create(); self.fill(req)
        (self.root / 'review.md').write_text('reviewed')
        flow.complete(self.root, req, evidence='已核对文档', evidence_inputs=['review.md'])
        (self.root / 'source.txt').write_text('unrelated')
        flow.complete(self.root, req)
        self.git('add', 'requirements', 'review.md')
        flow.git_check(self.root, req)
        (self.root / 'other.md').write_text('unreviewed')
        self.git('add', 'other.md')
        with self.assertRaisesRegex(ValueError, '未覆盖'):
            flow.git_check(self.root, req)

    def test_release_identity_and_symlink(self):
        options = dict(bundle_id='com.example.one', environment='production',
                       commit='a' * 40, outcome='processing')
        flow.release_record(self.root, 'upload-testflight', '1.0', '1', '平台处理中', **options)
        one = self.root / 'releases/com.example.one-production-1.0-1.md'
        self.assertIn('processing', one.read_text())
        flow.release_record(self.root, 'upload-testflight', '1.0', '1', '完成',
                            **dict(options, bundle_id='com.example.two', outcome='succeeded'))
        self.assertEqual(2, len(list((self.root / 'releases').glob('*.md'))))
        original = one.read_text()
        with self.assertRaisesRegex(ValueError, '身份'):
            flow.release_record(self.root, 'archive', '1.0', '1', '完成',
                                **dict(options, commit='b' * 40))
        target = self.root / 'protected.md'; one.rename(target); one.symlink_to(target)
        with self.assertRaisesRegex(ValueError, '符号链接'):
            flow.release_record(self.root, 'archive', '1.0', '1', '完成', **options)
        self.assertEqual(original, target.read_text())

    def test_release_requires_identity_and_preserves_failed_events(self):
        with self.assertRaisesRegex(ValueError, '发布身份'):
            flow.release_record(self.root, 'archive', '1.0', '1', '完成')
        self.assertFalse((self.root / 'releases').exists())
        options = dict(bundle_id='com.example.app', environment='production', commit='a' * 40)
        for outcome in ('failed', 'processing', 'succeeded'):
            flow.release_record(self.root, 'upload-testflight', '1.0', '1', outcome,
                                outcome=outcome, **options)
        path = self.root / 'releases/com.example.app-production-1.0-1.md'
        events = [json.loads(line[2:]) for line in path.read_text().splitlines() if line.startswith('- ')]
        self.assertEqual(['failed', 'processing', 'succeeded'], [event['outcome'] for event in events])


if __name__ == '__main__':
    unittest.main()
