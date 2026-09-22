import contextlib
import importlib.util
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / '.agents/skills/ios-team-flow/scripts/teamflow.py'
spec = importlib.util.spec_from_file_location('teamflow', SOURCE)
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)


class TeamFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.root / '.agents').mkdir()
        (self.root / 'source.txt').write_text('source')
        self.configure_checks()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def configure_checks(self):
        config = {'schema_version': 1, 'inputs': ['source.txt'],
                  'checks': {'ok': {'argv': [sys.executable, '-c', 'pass']}},
                  'profiles': {'change': ['ok']}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))

    def create(self, title='需求', **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            return flow.create(self.root, title, **kwargs)['requirement']

    def fill(self, requirement):
        path = self.root / 'requirements' / (requirement + '.md')
        text = path.read_text().replace('待填写本次要达到的结果', '实现登录错误提示')
        text = text.replace('待填写本次明确不处理的内容；没有时写“无额外排除”', '无额外排除')
        text = text.replace('- [ ] ⚪ AC-01：填写可观察的输入、操作和预期结果',
                            '- [x] ✅ AC-01：错误时显示提示')
        path.write_text(text)
        return path

    def test_create_uses_readable_sequence_and_ignores_old_cards(self):
        directory = self.root / 'requirements'; directory.mkdir()
        (directory / 'REQ-20260911-old.md').write_text('legacy')
        first = self.create('A')
        second = self.create('B', queued=True)
        self.assertEqual(('REQ-0001', 'REQ-0002'), (first, second))
        self.assertEqual('待处理', flow.parse_card(directory / 'REQ-0002.md')['state'])
        self.assertIn('- 状态：⚪ 待处理', (directory / 'REQ-0002.md').read_text())
        self.assertEqual('⚪ 0/1', flow.parse_card(directory / 'REQ-0002.md')['progress']['display'])
        self.assertEqual([first, second], [item['requirement'] for item in flow.cards(self.root)])

    def test_new_format_only_and_sparse_state_reason(self):
        req = self.create()
        card = self.fill(req)
        old = self.root / 'requirements/REQ-0002.md'
        old.write_text('# old\n<!-- teamflow:requirement:v3 -->\n')
        with self.assertRaisesRegex(ValueError, 'vNext'):
            flow.parse_card(old)
        with self.assertRaises(ValueError):
            flow.set_state(self.root, req, '阻塞')
        with contextlib.redirect_stdout(io.StringIO()):
            flow.set_state(self.root, req, '阻塞', '等待接口定义')
        text = card.read_text()
        self.assertIn('- 状态：🔴 阻塞', text)
        self.assertIn('等待接口定义', text)
        self.assertNotIn('下一步：无', text)
        self.assertNotIn('阻塞项：无', text)

    def test_complete_with_project_result_and_no_delivery_record(self):
        req = self.create(); card = self.fill(req)
        result, passed = flow.checks_module().run(self.root, 'change')
        self.assertTrue(passed)
        relative = str(result.relative_to(self.root))
        with contextlib.redirect_stdout(io.StringIO()):
            flow.complete(self.root, req, result=relative)
        self.assertEqual('完成', flow.parse_card(card)['state'])
        self.assertIn('- 状态：✅ 完成', card.read_text())
        self.assertIn('- 验证状态：✅ 通过', card.read_text())
        self.assertIn(relative, card.read_text())
        self.assertFalse((self.root / 'requirements/delivery').exists())
        self.assertFalse((self.root / 'logs/reviews').exists())

    def test_complete_rejects_unfinished_ac_and_stale_result(self):
        req = self.create()
        path = self.root / 'requirements' / (req + '.md')
        path.write_text(path.read_text().replace('待填写本次要达到的结果', '范围')
                        .replace('待填写本次明确不处理的内容；没有时写“无额外排除”', '无'))
        with self.assertRaisesRegex(ValueError, '未完成 AC'):
            flow.complete(self.root, req, evidence='人工核对')
        self.fill(req)
        result, _ = flow.checks_module().run(self.root, 'change')
        (self.root / 'source.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError, '源码或配置已变化'):
            flow.complete(self.root, req, result=str(result.relative_to(self.root)))

    def test_colored_state_and_progress_are_required_and_listed(self):
        req = self.create('图标需求')
        card = self.root / 'requirements' / (req + '.md')
        self.assertEqual({'待处理': '⚪', '待确认': '🟡', '进行中': '🔵',
                          '待用户验证': '🟣', '完成': '✅', '阻塞': '🔴',
                          '暂停': '🟠', '取消': '⚫'}, flow.STATE_ICONS)
        self.assertEqual('🔵 1/2', flow.progress_display(1, 2))
        listing = io.StringIO()
        with contextlib.redirect_stdout(listing):
            flow.list_output(self.root)
        self.assertIn('| 🔵 进行中 | ⚪ 0/1 |', listing.getvalue())
        listing_json = io.StringIO()
        with contextlib.redirect_stdout(listing_json):
            flow.list_output(self.root, as_json=True)
        self.assertEqual('🔵 进行中', json.loads(listing_json.getvalue())[0]['state'])
        card.write_text(card.read_text().replace('- 状态：🔵 进行中', '- 状态：进行中'))
        with self.assertRaisesRegex(ValueError, '需求状态无效'):
            flow.parse_card(card)

    def test_ac_checkbox_and_progress_icon_must_agree(self):
        req = self.create()
        card = self.root / 'requirements' / (req + '.md')
        card.write_text(card.read_text().replace('- [ ] ⚪ AC-01', '- [x] ⚪ AC-01'))
        with self.assertRaisesRegex(ValueError, '复选框与进度图标不一致'):
            flow.parse_card(card)

    def test_wait_user_completion_uses_colored_state(self):
        req = self.create(); card = self.fill(req)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            flow.complete(self.root, req, evidence='人工验证入口已准备', wait_user=True)
        self.assertEqual('🟣 待用户验证', json.loads(output.getvalue())['state'])
        self.assertIn('- 状态：🟣 待用户验证', card.read_text())
        self.assertIn('- 验证状态：🟣 待用户验证', card.read_text())

    def test_git_check_is_explicit_and_uses_staged_object(self):
        req = self.create(); self.fill(req)
        result, _ = flow.checks_module().run(self.root, 'change')
        with contextlib.redirect_stdout(io.StringIO()):
            flow.complete(self.root, req, result=str(result.relative_to(self.root)))
        self.git('add', 'source.txt', '.agents/project-checks.json')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            flow.git_check(self.root, req, result=str(result.relative_to(self.root)))
        report = json.loads(output.getvalue())
        self.assertEqual('Requirement: ' + req, report['commit_trailer'])
        (self.root / 'source.txt').write_text('unstaged change')
        with self.assertRaisesRegex(ValueError, '源码或配置已变化'):
            flow.git_check(self.root, req, result=str(result.relative_to(self.root)))

    def test_release_prepare_is_read_only_and_record_is_one_action(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            flow.release_prepare('upload-testflight', '1.2.0', '123')
        self.assertFalse((self.root / 'releases').exists())
        prepared = json.loads(output.getvalue())
        self.assertFalse(prepared['external_write'])
        self.assertEqual({}, prepared['export_options_overrides'])
        with contextlib.redirect_stdout(io.StringIO()):
            flow.release_record(self.root, 'upload-testflight', '1.2.0', '123', '处理完成')
        record = self.root / 'releases/App-1.2.0-123.md'
        self.assertIn('上传 TestFlight', record.read_text())
        self.assertNotIn('Internal Only', record.read_text())
        self.assertNotIn('提交 App Store 审核', record.read_text())

    def test_testflight_internal_only_requires_explicit_option(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            flow.release_prepare('upload-testflight', '1.2.0', '124', True)
        prepared = json.loads(output.getvalue())
        self.assertEqual({'testFlightInternalTestingOnly': True},
                         prepared['export_options_overrides'])
        with self.assertRaisesRegex(ValueError, '仅适用于上传 TestFlight'):
            flow.release_prepare('archive', '1.2.0', '124', True)
        with contextlib.redirect_stdout(io.StringIO()):
            flow.release_record(self.root, 'upload-testflight', '1.2.0', '124',
                                '处理完成', True)
        record = self.root / 'releases/App-1.2.0-124.md'
        self.assertIn('上传 TestFlight（TestFlight Internal Only）', record.read_text())


if __name__ == '__main__':
    unittest.main()
