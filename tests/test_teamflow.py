import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".agents/teamflow-core/scripts"))
SOURCE = ROOT / '.agents/teamflow-core/scripts/teamflow.py'
spec = importlib.util.spec_from_file_location('teamflow', SOURCE)
flow = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flow)
import requirement_model as model  # noqa: E402


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
        (self.root / '.gitignore').write_text('/logs/project-checks/\n')
        self.configure_checks()

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.root), *args], check=True,
                              capture_output=True, text=True).stdout.strip()

    def configure_checks(self):
        config = {'schema_version': 2, 'profiles': {'change': {'inputs': ['source.txt', '.gitignore'],
                  'checks': {'ok': {'argv': [sys.executable, '-c', 'pass']}}}}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))

    def create(self, title='需求', **kwargs):
        return flow.create(self.root, title, **kwargs)['requirement']

    def card_path(self, requirement):
        return self.root / 'requirements' / (requirement + '.md')

    def fill(self, requirement, done=True):
        path = self.card_path(requirement)
        text = path.read_text().replace('〈填写本次要达到的结果〉', '实现登录错误提示')
        text = text.replace('- [ ] AC-01：〈填写可观察的输入、操作和预期结果〉',
                            ('- [x]' if done else '- [ ]') + ' AC-01：错误时显示提示')
        path.write_text(text)
        return path

    def saved(self, requirement, staged=False):
        return flow.verify_saved(self.root, flow.parse_card(self.card_path(requirement)), staged=staged)

    def logs(self):
        return list((self.root / 'logs/project-checks').glob('*/result.json'))

    def test_create_uses_branch_independent_ids(self):
        first = self.create('A')
        second = self.create('B', queued=True)
        for requirement in (first, second):
            self.assertRegex(requirement, r'^REQ-\d{8}-[0-9a-f]{4}$')
        self.assertNotEqual(first, second)
        queued = flow.parse_card(self.card_path(second))
        self.assertEqual(('进行中', True), (queued['state'], queued['queued']))
        self.assertEqual('🔵 进行中（排队）', queued['state_display'])
        self.assertEqual('⚪ 0/1', queued['progress']['display'])
        rows, skipped = flow.cards(self.root)
        self.assertEqual({first, second}, {row['requirement'] for row in rows})
        self.assertEqual([], skipped)

    def test_create_retries_on_id_collision(self):
        with patch.object(flow.secrets, 'token_hex', side_effect=['abcd', 'abcd', 'ef01']):
            first = self.create('A')
            second = self.create('B')
        self.assertTrue(first.endswith('-abcd'))
        self.assertTrue(second.endswith('-ef01'))

    def test_bug_uses_shared_card_with_failure_and_regression_conditions(self):
        req = self.create('缺陷', bug=True)
        card = flow.parse_card(self.card_path(req))
        self.assertEqual('bug', card['type'])
        self.assertEqual(['原失败场景已恢复', '受影响的关联路径没有回归'],
                         [item['condition'] for item in card['ac']])
        self.assertIn('触发条件', card['scope'])
        self.assertNotIn('〈验收条件〉', card['text'])

    def test_body_layout_edits_do_not_change_semantics(self):
        req = self.create(); card = self.fill(req)
        before = flow.semantic_content(card.read_text(), req)
        edited = (card.read_text().replace('# 需求', '# 新标题')
                  .replace('\n实现登录错误提示\n', '\n\n   实现登录错误提示   \n\n')
                  .replace('- [x] AC-01：', '* [ ] AC-01:  ')
                  + '\n- 2026-10-13T07:00:00-07:00：补充记录\n\n## 备注\n\n随便写\n')
        card.write_text(edited)
        self.assertEqual(before, flow.semantic_content(edited, req))
        self.assertEqual('新标题', flow.parse_card(card)['title'])

    def test_metadata_errors_are_explicit(self):
        req = self.create(); card = self.card_path(req)
        original = card.read_text()
        for broken, message in [(original.replace('state: 进行中', 'state: 待处理'), '需求状态无效'),
                                ('---\n' + original.split('---\n', 2)[1], '未闭合'),
                                (original.replace('type: feature', 'type feature'), '第 3 行格式无效'),
                                (original.replace('id: ' + req, 'id: REQ-20000101-0000'), 'id 与文件名'),
                                (original.replace('- [ ] AC-01', '- 🔵 AC-01'), '验收条件')]:
            with self.subTest(message=message):
                card.write_text(broken)
                with self.assertRaisesRegex(ValueError, message):
                    flow.parse_card(card)

    def test_block_requires_kind_and_reason_and_is_logged(self):
        req = self.create(); card = self.fill(req)
        with self.assertRaisesRegex(ValueError, '--blocked'):
            flow.set_state(self.root, req, '阻塞', '等待接口定义')
        with self.assertRaisesRegex(ValueError, '--reason'):
            flow.set_state(self.root, req, '阻塞', blocked='外部')
        flow.set_state(self.root, req, '阻塞', '等待接口定义', blocked='外部')
        parsed = flow.parse_card(card)
        self.assertEqual(('阻塞', '外部', '等待接口定义'), (parsed['state'], parsed['blocked'], parsed['reason']))
        self.assertIn('🔴 阻塞（外部） — 等待接口定义', card.read_text())
        with self.assertRaisesRegex(ValueError, '恢复'):
            flow.complete(self.root, req, profile='change')
        with self.assertRaisesRegex(ValueError, '恢复必须'):
            flow.set_state(self.root, req, '进行中')
        flow.set_state(self.root, req, '进行中', '接口已确认')
        parsed = flow.parse_card(card)
        self.assertEqual(('进行中', None, None), (parsed['state'], parsed['blocked'], parsed['reason']))
        self.assertEqual(2, parsed['body'].count('\n- 20'))

    def test_terminal_states_cannot_bypass_evidence(self):
        req = self.create()
        for state in ('完成', '待用户验证'):
            with self.assertRaisesRegex(ValueError, 'req complete'):
                flow.set_state(self.root, req, state)

    def test_complete_with_project_result_writes_summary(self):
        req = self.create(); card = self.fill(req)
        result, passed = flow.checks_module().run(self.root, 'change', req)
        self.assertTrue(passed)
        report = flow.complete(self.root, req, result=str(result.relative_to(self.root)))
        parsed = flow.parse_card(card)
        self.assertEqual('完成', parsed['state'])
        evidence = parsed['evidence']
        self.assertEqual(('result', 'change', '通过'), (evidence['kind'], evidence['profile'], evidence['status']))
        self.assertTrue(evidence['fingerprint'].startswith('sha256:'))
        self.assertEqual(flow.requirement_fingerprint(parsed), evidence['requirement'])
        self.assertIn('at', evidence)
        self.assertEqual(report['evidence'], evidence)

    def test_saved_summary_survives_deleted_logs(self):
        req = self.create(); card = self.fill(req)
        flow.complete(self.root, req, profile='change')
        shutil.rmtree(self.root / 'logs')
        flow.complete(self.root, req)
        self.git('add', 'source.txt', '.gitignore', '.agents/project-checks.json', 'requirements')
        self.assertEqual('Requirement: ' + req, flow.git_check(self.root, req)['commit_trailer'])
        (self.root / 'source.txt').write_text('changed')
        for action in (self.saved, lambda req: flow.git_check(self.root, req)):
            with self.assertRaisesRegex(ValueError, '源码或配置已变化'):
                action(req)
        self.assertEqual('完成', flow.parse_card(card)['state'])

    def test_requirement_change_invalidates_summary(self):
        req = self.create(); card = self.fill(req)
        flow.complete(self.root, req, profile='change')
        card.write_text(card.read_text().replace('错误时显示提示', '离线时显示提示'))
        with self.assertRaisesRegex(ValueError, '需求范围或 AC 已变化'):
            self.saved(req)
        self.assertIn('按改动自动选择', flow.complete(self.root, req)['verification'])
        self.saved(req)

    def test_complete_preserves_pending_ac_and_rejects_stale_result(self):
        req = self.create(); self.fill(req, done=False)
        result, _ = flow.checks_module().run(self.root, 'change', req)
        report = flow.complete(self.root, req, result=str(result.relative_to(self.root)))
        self.assertEqual(['AC-01'], report['pending_ac'])
        self.assertEqual('进行中', flow.parse_card(self.card_path(req))['state'])
        (self.root / 'source.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError, '源码或配置已变化'):
            flow.complete(self.root, req, result=str(result.relative_to(self.root)))

    def test_state_icons_and_list_output(self):
        req = self.create('图标需求')
        self.assertEqual({'进行中': '🔵', '待用户验证': '🟣', '阻塞': '🔴', '完成': '✅', '取消': '⚫'},
                         model.STATE_ICONS)
        self.assertEqual('🔵 1/2', model.progress_display(1, 2))
        self.assertIn('| 🔵 进行中 | ⚪ 0/1 |', flow.render('list', flow.cards(self.root)))
        (self.root / 'requirements/REQ-20000101-dead.md').write_text('# 无元数据\n')
        rows, skipped = flow.cards(self.root)
        self.assertEqual([req], [row['requirement'] for row in rows])
        self.assertIn('已跳过异常需求卡 REQ-20000101-dead', flow.render('list', (rows, skipped)))

    def test_wait_user_completion(self):
        req = self.create(); card = self.fill(req, done=False)
        report = flow.complete(self.root, req, evidence='人工验证入口已准备', wait_user=True)
        self.assertEqual('🟣 待用户验证', report['state'])
        self.assertEqual(['AC-01'], report['pending_ac'])
        self.assertIn('- [ ] AC-01', card.read_text())
        flow.complete(self.root, req, evidence='用户已确认真机结果', confirm_ac=['AC-01'])
        self.assertEqual('完成', flow.parse_card(card)['state'])

    def test_manual_evidence_preserves_literal_text(self):
        req = self.create(); card = self.fill(req)
        evidence = r'核对路径 App\new，命令含 "引号" 与字面量 \1'
        flow.complete(self.root, req, evidence=evidence)
        self.assertEqual(evidence, flow.parse_card(card)['evidence']['note'])
        self.assertEqual('完成', flow.parse_card(card)['state'])

    def test_wait_user_does_not_delay_fully_confirmed_completion(self):
        req = self.create(); card = self.fill(req, done=False)
        flow.complete(self.root, req, profile='change', wait_user=True)
        report = flow.complete(self.root, req, confirm_ac=['AC-01'], wait_user=True)
        self.assertEqual('完成', report['state_key'])
        self.assertEqual([], report['pending_ac'])
        flow.complete(self.root, req, wait_user=True)
        self.assertEqual('完成', flow.parse_card(card)['state'])
        self.assertEqual(1, len(self.logs()))

    def test_user_confirmed_ac_is_recorded_separately(self):
        req = self.create(); card = self.fill(req, done=False)
        flow.complete(self.root, req, profile='change', wait_user=True)
        before = flow.parse_card(card)['evidence']
        report = flow.complete(self.root, req, user_confirmed=['AC-01'])
        self.assertEqual('完成', report['state_key'])
        saved = flow.parse_card(card)
        self.assertEqual(['AC-01'], saved['meta']['user_confirmed'])
        self.assertEqual(before['fingerprint'], saved['evidence']['fingerprint'])
        self.assertEqual(['AC-01'], flow.status(self.root, req)['user_confirmed'])
        from diagnostics import pr_body
        self.assertIn('AC-01：', pr_body(self.root, req)['body'])
        self.assertIn('（用户确认）', pr_body(self.root, req)['body'])

    def test_manual_proof_rejects_semantic_changes_without_writing(self):
        req = self.create(); card = self.fill(req)
        card.write_text(card.read_text().replace('## 不包含\n\n无', '## 不包含\n\n支付'))
        flow.complete(self.root, req, evidence='实际展示核对记录')
        original = card.read_text()
        for before, after in [('实现登录错误提示', '实现离线提示'),
                              ('错误时显示提示', '离线时显示提示'),
                              ('\n支付\n', '\n支付和订单\n')]:
            with self.subTest(field=before):
                changed = original.replace(before, after)
                card.write_text(changed)
                with self.assertRaisesRegex(ValueError, '需求范围或 AC 已变化'):
                    self.saved(req)
                self.assertEqual(changed, card.read_text())
                self.git('add', 'requirements')
                with self.assertRaisesRegex(ValueError, '需求范围或 AC 已变化'):
                    flow.git_check(self.root, req)
        flow.complete(self.root, req, evidence='按新范围重新核对')
        flow.complete(self.root, req)
        self.assertEqual('完成', flow.parse_card(card)['state'])

    def test_evidence_cannot_be_copied_to_another_requirement(self):
        req = self.create(); card = self.fill(req)
        flow.complete(self.root, req, evidence='实际展示核对记录')
        other = self.create(); other_card = self.fill(other)
        other_card.write_text(other_card.read_text().replace('错误时显示提示', '另一个条件'))
        meta, body = flow.split_card(other_card.read_text())
        meta['evidence'] = flow.parse_card(card)['evidence']
        other_card.write_text(flow.dump_card(meta, body))
        with self.assertRaisesRegex(ValueError, '需求范围或 AC 已变化'):
            self.saved(other)

    def test_manual_proof_requires_complete_binding(self):
        req = self.create(); card = self.fill(req)
        flow.complete(self.root, req, evidence='实际展示核对记录')
        meta, body = flow.split_card(card.read_text())
        meta['evidence'].pop('paths')
        card.write_text(flow.dump_card(meta, body))
        with self.assertRaisesRegex(ValueError, '人工证据'):
            self.saved(req)

    def test_result_must_bind_current_requirement(self):
        req = self.create(); self.fill(req)
        other = self.create(); self.fill(other)
        for bound in (None, other):
            result, _ = flow.checks_module().run(self.root, 'change', bound)
            with self.assertRaisesRegex(ValueError, '未绑定当前需求'):
                flow.complete(self.root, req, result=str(result.relative_to(self.root)))

    def test_git_check_uses_staged_object(self):
        req = self.create(); self.fill(req)
        flow.complete(self.root, req, profile='change')
        self.git('add', 'source.txt', '.gitignore', '.agents/project-checks.json', 'requirements')
        report = flow.git_check(self.root, req)
        self.assertEqual('Requirement: ' + req, report['commit_trailer'])
        self.assertIn('提交检查：通过', flow.render('git', report))
        (self.root / 'source.txt').write_text('unstaged change')
        with self.assertRaisesRegex(ValueError, '源码或配置已变化'):
            flow.git_check(self.root, req)
        (self.root / 'source.txt').write_text('other')
        self.git('add', 'source.txt')
        (self.root / 'source.txt').write_text('source')
        with self.assertRaisesRegex(ValueError, '暂存内容与已验证工作区不一致'):
            flow.git_check(self.root, req)

    def test_git_check_rejects_staged_logs_but_allows_deleted_logs(self):
        req = self.create(); self.fill(req)
        old_log = self.root / 'logs/old/run.txt'
        old_log.parent.mkdir(parents=True); old_log.write_text('old')
        self.git('add', '-f', 'logs/old/run.txt'); self.git('commit', '-q', '-m', 'old log')
        flow.complete(self.root, req, profile='change')
        self.git('rm', '-q', '--cached', 'logs/old/run.txt')
        self.git('add', 'source.txt', '.gitignore', '.agents/project-checks.json', 'requirements')
        flow.git_check(self.root, req)
        self.git('add', '-f', str(self.logs()[0].relative_to(self.root)))
        with self.assertRaisesRegex(ValueError, '本地证据'):
            flow.git_check(self.root, req)
        self.git('reset', '-q', '--', 'logs/project-checks')
        (self.root / 'logs/new.txt').write_text('new')
        self.git('add', '-f', 'logs/new.txt')
        with self.assertRaisesRegex(ValueError, 'logs/new.txt'):
            flow.git_check(self.root, req)

    def test_inline_validation_uses_only_before_and_after_snapshots(self):
        req = self.create(); self.fill(req)
        checks = flow.checks_module()
        with patch.object(checks, 'source_snapshot', wraps=checks.source_snapshot) as snapshot:
            flow.complete(self.root, req, profile='change')
            self.assertEqual(2, snapshot.call_count)
            flow.complete(self.root, req)
            self.assertEqual(3, snapshot.call_count)

    def test_confirm_selected_ac_reuses_result_and_preserves_pending(self):
        req = self.create(); card = self.fill(req, done=False)
        card.write_text(card.read_text().replace('错误时显示提示\n', '错误时显示提示\n- [ ] AC-02：用户确认实际展示\n'))
        flow.complete(self.root, req, profile='change')
        with patch.object(flow.checks_module(), 'run', side_effect=AssertionError('不能重跑')):
            flow.complete(self.root, req, confirm_ac=['AC-01'], wait_user=True)
            parsed = flow.parse_card(card)
            self.assertEqual('待用户验证', parsed['state'])
            self.assertEqual([True, False], [item['done'] for item in parsed['ac']])
            result = subprocess.run([sys.executable, str(SOURCE), '--project', str(self.root),
                                     'req', 'complete', req, '--confirm-ac', 'AC-01',
                                     '--confirm-ac', 'AC-02'], capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual(f'{req} ✅ 完成 ✅ 2/2', result.stdout.strip())
            self.assertEqual('完成', flow.parse_card(card)['state'])
        self.assertEqual(1, len(self.logs()))

    def test_confirm_ac_rejects_invalid_requests_without_mutating_card(self):
        req = self.create(); card = self.fill(req, done=False)
        original = card.read_text()
        with self.assertRaisesRegex(ValueError, '未知 AC'):
            flow.complete(self.root, req, confirm_ac=['AC-99'], profile='change')
        self.assertEqual(original, card.read_text())
        self.assertFalse((self.root / 'logs/project-checks').exists())
        flow.complete(self.root, req, profile='change')
        original = card.read_text()
        (self.root / 'source.txt').write_text('changed')
        config = self.root / '.agents/project-checks.json'
        config.write_text(config.read_text().replace('pass', 'raise SystemExit(1)'))
        with self.assertRaisesRegex(ValueError, '验证：失败'):
            flow.complete(self.root, req, profile='change', confirm_ac=['AC-01'])
        self.assertEqual(original, card.read_text())

    def test_confirm_ac_with_profile_preserves_condition(self):
        req = self.create(); card = self.fill(req, done=False)
        card.write_text(card.read_text().replace('- [ ] AC-01', '  - [ ] AC-01'))
        flow.complete(self.root, req, profile='change', confirm_ac=['AC-01'])
        self.assertEqual('完成', flow.parse_card(card)['state'])
        self.assertIn('  - [x] AC-01：错误时显示提示', card.read_text())
        flow.complete(self.root, req)
        self.assertEqual(1, len(self.logs()))

    def test_failed_profile_does_not_complete_or_replace_evidence(self):
        req = self.create(); card = self.fill(req)
        original = card.read_text()
        config = self.root / '.agents/project-checks.json'
        config.write_text(config.read_text().replace('pass', 'raise SystemExit(1)'))
        with self.assertRaisesRegex(ValueError, r'验证：失败（change）：ok 失败（logs/project-checks/'):
            flow.complete(self.root, req, profile='change')
        self.assertEqual(original, card.read_text())
        with self.assertRaisesRegex(ValueError, '验证：失败（change，按改动自动选择）'):
            flow.complete(self.root, req)
        self.assertEqual(original, card.read_text())
        (self.root / '.agents/project-checks.json').unlink()
        with self.assertRaisesRegex(ValueError, '没有已绑定的证据'):
            flow.complete(self.root, req)
        with self.assertRaisesRegex(ValueError, '只能提供'):
            flow.complete(self.root, req, profile='change', evidence='manual')

    def test_cli_defaults_to_brief_output_and_json_on_request(self):
        def cli(*args):
            result = subprocess.run([sys.executable, str(SOURCE), '--project', str(self.root), *args],
                                    capture_output=True, text=True)
            self.assertEqual(0, result.returncode, result.stderr)
            return result.stdout
        created = cli('req', 'create', '--title', '简短输出')
        self.assertRegex(created, r'^已创建 REQ-\d{8}-[0-9a-f]{4}（🔵 进行中）：requirements/')
        req = created.split()[1].split('（')[0]
        self.fill(req, done=False)
        brief = cli('req', 'complete', req, '--profile', 'change')
        self.assertLessEqual(len(brief.strip().splitlines()), 4)
        self.assertIn('验证：通过（change）', brief)
        self.assertEqual('AC-01', json.loads(cli('req', 'status', req, '--json'))['ac'][0]['id'])
        self.assertIn('证据：change 通过', cli('req', 'status', req))
        self.assertEqual('验证：通过（change）', cli('verify', 'run', '--profile', 'change').strip())
        self.assertEqual('通过', json.loads(cli('verify', 'run', '--profile', 'change', '--json'))['status'])
        self.assertIn('仅按路径建议', cli('verify', 'suggest'))
        self.assertIn('profiles', json.loads(cli('verify', 'suggest', '--json')))
        self.assertIn('requirements', json.loads(cli('req', 'list', '--json')))
        cli('req', 'state', req, '--state', '取消', '--reason', '用户取消')
        listing = cli('req', 'list')
        self.assertNotIn(req, listing)
        self.assertIn('另有已完成或取消 1 张（--all 查看）', listing)
        self.assertIn(req, cli('req', 'list', '--all'))
        self.assertEqual([], json.loads(cli('req', 'list', '--json'))['requirements'])

    def test_complete_auto_selects_smallest_covering_profile(self):
        config = {'schema_version': 2, 'profiles': {
            'change': {'inputs': ['source.txt', '.gitignore'],
                       'checks': {'ok': {'argv': [sys.executable, '-c', 'pass']}}},
            'release': {'extends': 'change',
                        'checks': {'package': {'argv': [sys.executable, '-c', 'pass']}}},
            'docs': {'inputs': ['docs'], 'checks': {'links': {'argv': [sys.executable, '-c', 'pass']}}}}}
        (self.root / 'docs').mkdir(); (self.root / 'docs/a.md').write_text('doc')
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))
        loaded = flow.checks_module().load_config(self.root)
        self.assertEqual(['ok', 'package'], list(loaded['profiles']['release']['checks']))
        self.assertEqual(['source.txt', '.gitignore'], loaded['profiles']['release']['inputs'])
        req = self.create(); card = self.fill(req)
        self.git('add', 'docs'); self.git('commit', '-qm', 'docs')
        report = flow.complete(self.root, req)
        self.assertEqual('验证：通过（change，按改动自动选择）', report['verification'])
        self.assertEqual('change', flow.parse_card(card)['evidence']['profile'])
        self.assertEqual('change', flow.checks_module().suggest(self.root)['recommended'])
        self.assertIsNone(flow.complete(self.root, req)['verification'])
        (self.root / 'docs/a.md').write_text('changed doc')
        (self.root / 'source.txt').write_text('changed source')
        original = card.read_text()
        with self.assertRaisesRegex(ValueError, '没有单个 profile 全部覆盖'):
            flow.complete(self.root, req)
        (self.root / 'loose.swift').write_text('let a = 1')
        with self.assertRaisesRegex(ValueError, '不在任何 profile 输入内：loose.swift'):
            flow.complete(self.root, req)
        self.assertEqual(original, card.read_text())

    def test_git_check_accepts_extended_profile(self):
        config = {'schema_version': 2, 'profiles': {
            'change': {'inputs': ['source.txt', '.gitignore'],
                       'checks': {'ok': {'argv': [sys.executable, '-c', 'pass']}}},
            'release': {'extends': 'change', 'checks': {'package': {'argv': [sys.executable, '-c', 'pass']}}}}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))
        req = self.create(); self.fill(req)
        flow.complete(self.root, req, profile='release')
        self.git('add', '.')
        self.assertEqual('release', flow.git_check(self.root, req)['validation']['profile'])

    def test_extends_rejects_cycles_and_missing_parent(self):
        for profiles, message in [({'a': {'extends': 'b', 'checks': {}}, 'b': {'extends': 'a', 'checks': {}}}, '循环'),
                                  ({'a': {'extends': 'none', 'checks': {}}}, '不存在')]:
            (self.root / '.agents/project-checks.json').write_text(
                json.dumps({'schema_version': 2, 'profiles': profiles}))
            with self.assertRaisesRegex(ValueError, message):
                flow.checks_module().load_config(self.root)

if __name__ == '__main__':
    unittest.main()
