#!/usr/bin/env python3
"""iOS 工作流：需求、验证、提交前核对与显式 App 外部动作记录。"""
import argparse
import contextlib
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from teamflow_common import local_path as safe

MARKER = '<!-- teamflow:requirement:vnext -->'
ID = re.compile(r'REQ-(\d{4})')
STATE_ICONS = {
    '待处理': '⚪',
    '待确认': '🟡',
    '进行中': '🔵',
    '待用户验证': '🟣',
    '完成': '✅',
    '阻塞': '🔴',
    '暂停': '🟠',
    '取消': '⚫',
}
STATES = tuple(STATE_ICONS)
OPERATIONS = (
    'archive', 'upload-testflight', 'distribute-testflight', 'submit-beta-review',
    'submit-app-review', 'publish', 'phased-release', 'pause-phased-release', 'remove-sale',
)
OPERATION_NAMES = {
    'archive': '归档',
    'upload-testflight': '上传 TestFlight',
    'distribute-testflight': '分发 TestFlight',
    'submit-beta-review': '提交 Beta App Review',
    'submit-app-review': '提交 App Store 审核',
    'publish': '发布 App Store 版本',
    'phased-release': '开启分阶段发布',
    'pause-phased-release': '暂停分阶段发布',
    'remove-sale': '下架',
}


def requirement_path(root, requirement):
    if not ID.fullmatch(requirement):
        raise ValueError('需求编号格式应为 REQ-0001')
    path = safe(root, 'requirements/' + requirement + '.md')
    if not path.is_file():
        raise ValueError('需求不存在：' + requirement)
    return path


def field(text, name):
    values = re.findall(r'^- ' + re.escape(name) + r'：(.+)$', text, re.M)
    if len(values) != 1 or not values[0].strip():
        raise ValueError('需求卡必须且只能填写一处：' + name)
    return values[0].strip()


def state_display(state):
    return STATE_ICONS[state] + ' ' + state


def parse_state(value):
    for state in STATES:
        if value == state_display(state):
            return state
    raise ValueError('需求状态无效：' + value)


def progress_display(done, total):
    icon = '✅' if done == total else ('🔵' if done else '⚪')
    return f'{icon} {done}/{total}'


def parse_card(path):
    text = path.read_text()
    if MARKER not in text:
        raise ValueError('只支持 vNext 需求卡：' + path.name)
    requirement = path.stem
    if not ID.fullmatch(requirement):
        raise ValueError('需求文件名格式无效：' + path.name)
    state = parse_state(field(text, '状态'))
    scope = field(text, '范围')
    excluded = field(text, '不包含') if re.search(r'^- 不包含：', text, re.M) else ''
    if scope in ('待填写', '—') or excluded in ('待填写', '—'):
        raise ValueError('范围和不包含必须填写实际内容')
    ac = []
    for line in text.splitlines():
        match = re.match(r'^- (⚪|✅) (AC-\d+)：(.+)$', line)
        if match:
            ac.append({'id': match.group(2), 'done': match.group(1) == '✅',
                       'condition': match.group(3).strip()})
    if not ac or len({item['id'] for item in ac}) != len(ac):
        raise ValueError('需求卡必须包含不重复的 AC 项')
    done = sum(item['done'] for item in ac)
    return {'requirement': requirement, 'state': state, 'state_display': state_display(state),
            'progress': {'done': done, 'total': len(ac),
                         'display': progress_display(done, len(ac))},
            'scope': scope, 'excluded': excluded, 'ac': ac, 'text': text}


def cards(root):
    directory = safe(root, 'requirements')
    if not directory.exists():
        return []
    rows = []
    for path in directory.glob('REQ-*.md'):
        if not ID.fullmatch(path.stem):
            continue
        try:
            card = parse_card(path)
        except (OSError, ValueError) as error:
            print('已跳过异常需求卡 ' + path.name + '：' + str(error), file=sys.stderr)
            continue
        title = next((line[2:].removeprefix(path.stem + '：') for line in card['text'].splitlines()
                      if line.startswith('# ')), path.stem)
        rows.append({'requirement': path.stem, 'title': title,
                     'state': card['state_display'], 'state_key': card['state'],
                     'progress': card['progress']})
    return sorted(rows, key=lambda item: int(ID.fullmatch(item['requirement']).group(1)))


def create(root, title, queued=False, bug=False):
    if not title.strip() or '\n' in title or '\r' in title:
        raise ValueError('标题须为单行非空文本')
    directory = safe(root, 'requirements')
    directory.mkdir(parents=True, exist_ok=True)
    numbers = [int(ID.fullmatch(path.stem).group(1)) for path in directory.glob('REQ-*.md')
               if ID.fullmatch(path.stem)]
    for number in range(max(numbers, default=0) + 1, 10000):
        requirement = f'REQ-{number:04d}'
        target = directory / (requirement + '.md')
        template_name = 'bug-fix.md' if bug else 'requirement.md'
        template = Path(__file__).resolve().parents[1] / 'references/templates' / template_name
        content = template.read_text().replace('REQ-0000', requirement).replace('〈需求标题〉', title.strip())
        if queued:
            content = content.replace('- 状态：' + state_display('进行中'),
                                      '- 状态：' + state_display('待处理'), 1)
        try:
            with target.open('x') as stream:
                stream.write(content)
        except FileExistsError:
            continue
        result = {'requirement': requirement, 'card': str(target)}
        print(json.dumps(result, ensure_ascii=False))
        return result
    raise ValueError('需求编号已用尽')


def replace_field(text, name, value):
    pattern = r'^- ' + re.escape(name) + r'：.*$'
    if len(re.findall(pattern, text, re.M)) != 1:
        raise ValueError('需求卡字段缺失或重复：' + name)
    return re.sub(pattern, '- ' + name + '：' + value, text, count=1, flags=re.M)


def set_state(root, requirement, state, reason=None):
    if state not in STATES:
        raise ValueError('未知状态：' + state)
    if state in ('完成', '待用户验证'):
        raise ValueError('完成或待用户验证必须通过 req complete 绑定证据')
    if state in ('待确认', '阻塞', '暂停', '取消') and not (reason and reason.strip()):
        raise ValueError(state + ' 必须填写原因或恢复条件')
    path = requirement_path(root, requirement)
    card = parse_card(path)
    text = replace_field(card['text'], '状态', state_display(state))
    if reason and reason.strip():
        heading = '## 决策与异常'
        entry = f'- {datetime.now(timezone.utc).isoformat()}：{state_display(state)} — {reason.strip()}'
        if heading not in text:
            text = text.rstrip() + '\n\n' + heading + '\n\n' + entry + '\n'
        else:
            text = text.rstrip() + '\n' + entry + '\n'
    path.write_text(text)
    print(json.dumps({'requirement': requirement, 'state': state_display(state),
                      'state_key': state}, ensure_ascii=False))


def checks_module():
    import project_checks
    return project_checks


def validation_proof(root, card, result=None, evidence=None, staged=False):
    if result is not None and evidence is not None:
        raise ValueError('只能提供一种验证证据')
    if result is None and evidence is None:
        try:
            saved = json.loads(field(card['text'], '验证证据'))
            if saved['kind'] == 'result':
                result = saved['path']
            elif saved['kind'] == 'manual':
                evidence = saved['text']
            else:
                raise ValueError('未知证据类型')
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError('没有有效的已绑定证据；请提供 --profile、--result 或 --evidence') from error
    if result is not None:
        if not isinstance(result, str) or not result.strip():
            raise ValueError('验证结果路径不能为空')
        with contextlib.redirect_stdout(io.StringIO()):
            report = checks_module().verify(root, result, staged=staged)
        if report.get('requirement') != card['requirement']:
            raise ValueError('验证结果未绑定当前需求：' + card['requirement'])
        return {'kind': 'result', 'path': result}
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError('验证证据不能为空')
    return {'kind': 'manual', 'text': evidence.strip()}


def complete(root, requirement, result=None, evidence=None, wait_user=False, profile=None):
    if sum(value is not None for value in (result, evidence, profile)) > 1:
        raise ValueError('只能提供 --profile、--result、--evidence 中的一种')
    path = requirement_path(root, requirement)
    card = parse_card(path)
    pending = [item['id'] for item in card['ac'] if not item['done']]
    if pending and not wait_user:
        raise ValueError('仍有未完成 AC：' + ', '.join(pending))
    if profile is not None:
        target, passed = checks_module().run(root, profile, requirement)
        if not passed:
            raise ValueError('验证未通过，需求状态保持不变')
        result = str(target.relative_to(root.resolve()))
    proof = validation_proof(root, card, result, evidence)
    target_state = '待用户验证' if wait_user else '完成'
    text = replace_field(card['text'], '状态', state_display(target_state))
    text = replace_field(text, '验证证据', json.dumps(proof, ensure_ascii=False))
    path.write_text(text)
    print(json.dumps({'requirement': requirement, 'state': state_display(target_state),
                      'state_key': target_state, 'evidence': proof}, ensure_ascii=False))


def git_root(root):
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], text=True).strip()
    if Path(actual).resolve() != root:
        raise ValueError('请从项目 Git 根目录执行')


def git_check(root, requirement, result=None, evidence=None):
    git_root(root)
    card = parse_card(requirement_path(root, requirement))
    if card['state'] not in ('完成', '待用户验证'):
        raise ValueError('只有完成或待用户验证的需求可以进入提交检查')
    names = [name for name in subprocess.check_output(
        ['git', '-C', str(root), 'diff', '--cached', '--name-only', '-z']).decode().split('\0') if name]
    if not names:
        raise ValueError('暂存区为空')
    proof = validation_proof(root, card, result, evidence, staged=True)
    risky = [name for name in names if Path(name).suffix.lower() in
             ('.swift', '.m', '.mm', '.h', '.plist', '.entitlements', '.pbxproj', '.xcconfig')]
    print(json.dumps({'requirement': requirement, 'staged_files': names, 'validation': proof,
                      'semantic_review_required': True, 'release_sensitive_files': risky,
                      'commit_trailer': 'Requirement: ' + requirement}, ensure_ascii=False, indent=2))


def release_export_options(operation, testflight_internal_only=False):
    if testflight_internal_only and operation != 'upload-testflight':
        raise ValueError('TestFlight Internal Only 仅适用于上传 TestFlight')
    # 默认完全省略该键，而不是主动写入 false。
    return {'testFlightInternalTestingOnly': True} if testflight_internal_only else {}


def release_record(root, operation, version, build, evidence, testflight_internal_only=False):
    if not evidence.strip():
        raise ValueError('外部动作记录必须包含真实证据')
    release_export_options(operation, testflight_internal_only)
    directory = safe(root, 'releases')
    directory.mkdir(parents=True, exist_ok=True)
    name = re.sub(r'[^A-Za-z0-9._-]', '-', version)
    build_name = re.sub(r'[^A-Za-z0-9._-]', '-', build)
    if not name or not build_name:
        raise ValueError('版本和 build 不能为空')
    path = directory / f'App-{name}-{build_name}.md'
    if path.exists():
        text = path.read_text()
    else:
        text = f'# App 发布动作：{version} / {build}\n\n'
    display_name = OPERATION_NAMES[operation]
    if testflight_internal_only:
        display_name += '（TestFlight Internal Only）'
    entry = (f'- {datetime.now(timezone.utc).isoformat()} | {display_name} | '
             f'{evidence.strip()}\n')
    path.write_text(text.rstrip() + '\n\n' + entry)
    print(json.dumps({'record': str(path), 'operation': operation}, ensure_ascii=False))


def list_output(root, as_json=False):
    rows = cards(root)
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return
    lines = ['| 需求 | 标题 | 状态 | 进度 |', '| --- | --- | --- | --- |']
    lines.extend(f"| [{row['requirement']}](requirements/{row['requirement']}.md) | {row['title']} | {row['state']} | {row['progress']['display']} |"
                 for row in rows)
    print('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('.'))
    top = parser.add_subparsers(dest='area', required=True)

    req = top.add_parser('req')
    req_sub = req.add_subparsers(dest='command', required=True)
    creator = req_sub.add_parser('create')
    creator.add_argument('--title', required=True)
    creator.add_argument('--queued', action='store_true')
    creator.add_argument('--bug', action='store_true')
    listing = req_sub.add_parser('list')
    listing.add_argument('--json', action='store_true')
    status = req_sub.add_parser('status')
    status.add_argument('requirement')
    state = req_sub.add_parser('state')
    state.add_argument('requirement')
    state.add_argument('--state', choices=STATES, required=True)
    state.add_argument('--reason')
    done = req_sub.add_parser('complete')
    done.add_argument('requirement')
    proof = done.add_mutually_exclusive_group()
    proof.add_argument('--profile')
    proof.add_argument('--result')
    proof.add_argument('--evidence')
    done.add_argument('--wait-user', action='store_true')

    verify = top.add_parser('verify')
    verify_sub = verify.add_subparsers(dest='command', required=True)
    verify_sub.add_parser('init')
    verify_sub.add_parser('list')
    run = verify_sub.add_parser('run')
    run.add_argument('--profile', required=True)
    run.add_argument('--requirement', help='绑定本次需求的范围和 AC，忽略其他需求')

    git_area = top.add_parser('git')
    git_sub = git_area.add_subparsers(dest='command', required=True)
    check = git_sub.add_parser('check')
    check.add_argument('requirement')
    check.add_argument('--result')
    check.add_argument('--evidence')

    release = top.add_parser('release')
    release_sub = release.add_subparsers(dest='command', required=True)
    record = release_sub.add_parser('record')
    record.add_argument('operation', choices=OPERATIONS)
    record.add_argument('--version', required=True)
    record.add_argument('--build', required=True)
    record.add_argument('--evidence', required=True)
    record.add_argument('--testflight-internal-only', action='store_true')

    args = parser.parse_args()
    root = args.project.resolve()
    try:
        if args.area == 'req':
            if args.command == 'create':
                create(root, args.title, args.queued, args.bug)
            elif args.command == 'list':
                list_output(root, args.json)
            elif args.command == 'status':
                card = parse_card(requirement_path(root, args.requirement))
                payload = {k: v for k, v in card.items() if k not in ('text', 'state_display')}
                payload['state_key'] = payload['state']
                payload['state'] = card['state_display']
                print(json.dumps(payload, ensure_ascii=False, indent=2))
            elif args.command == 'state':
                set_state(root, args.requirement, args.state, args.reason)
            else:
                complete(root, args.requirement, args.result, args.evidence, args.wait_user, args.profile)
        elif args.area == 'verify':
            checks = checks_module()
            if args.command == 'init':
                path = checks.local_path(root, checks.CONFIG)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('x') as stream:
                    json.dump({'schema_version': 1, 'checks': {}, 'profiles': {}}, stream, indent=2)
                    stream.write('\n')
                print('已创建空验证配置：' + str(path))
            elif args.command == 'list':
                print(json.dumps(checks.load_config(root), ensure_ascii=False, indent=2))
            else:
                _, passed = checks.run(root, args.profile, args.requirement)
                return 0 if passed else 1
        elif args.area == 'git':
            git_check(root, args.requirement, args.result, args.evidence)
        else:
            release_record(root, args.operation, args.version, args.build, args.evidence,
                           args.testflight_internal_only)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(2, str(error) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
