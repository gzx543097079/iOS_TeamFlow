import unittest
import test_teamflow

flow = test_teamflow.flow


class BoundaryTests(unittest.TestCase):
    setUp = test_teamflow.TeamFlowTests.setUp
    git = test_teamflow.TeamFlowTests.git
    configure_checks = test_teamflow.TeamFlowTests.configure_checks
    create = test_teamflow.TeamFlowTests.create
    fill = test_teamflow.TeamFlowTests.fill
    card_path = test_teamflow.TeamFlowTests.card_path

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
            flow.verify_saved(self.root, flow.parse_card(self.card_path(req)))
        (self.root / 'Business.swift').write_text('let a = 1')
        self.git('add', '.')
        with self.assertRaisesRegex(ValueError, '自动验证'):
            flow.git_check(self.root, req, evidence='看过了')

    def test_placeholder_and_stopped_card_rejected(self):
        req = self.create()
        with self.assertRaisesRegex(ValueError, '占位'):
            flow.complete(self.root, req, evidence='实际核对', confirm_ac=['AC-01'])
        path = self.fill(req)
        for state, blocked in (('阻塞', '暂停'), ('取消', None)):
            flow.set_state(self.root, req, state, '用户要求', blocked)
            original = path.read_text()
            with self.assertRaisesRegex(ValueError, '恢复'):
                flow.complete(self.root, req, profile='change')
            self.assertEqual(original, path.read_text())

    def test_list_does_not_follow_symlink(self):
        req = self.create(); card = self.fill(req)
        target = self.root / 'real.md'; card.rename(target); card.symlink_to(target)
        rows, skipped = flow.cards(self.root)
        self.assertEqual([], rows)
        self.assertIn('符号链接', skipped[0]['error'])

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

if __name__ == '__main__':
    unittest.main()
