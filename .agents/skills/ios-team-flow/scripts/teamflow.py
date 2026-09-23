#!/usr/bin/env python3
"""iOS 工作流：需求、验证、提交前核对与显式 App 外部动作记录。"""
import argparse
import contextlib
import hashlib
import io
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from teamflow_common import local_path as safe
from requirement_model import (ID, STATES, STATE_ICONS, field, field_pattern,
                               state_display, progress_display, parse_card, semantic_content, require_ready)

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


def cards(root):
    directory = safe(root, 'requirements')
    if not directory.exists():
        return []
    rows = []
    for path in directory.glob('REQ-*.md'):
        if not ID.fullmatch(path.stem):
            continue
        try:
            card = parse_card(safe(root, str(path.relative_to(root))))
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
        template = Path(__file__).resolve().parents[1] / 'references/templates/requirement.md'
        content = template.read_text().replace('REQ-0000', requirement).replace('〈需求标题〉', title.strip())
        scope = '待填写缺陷现象、触发条件和预期修复结果' if bug else '待填写本次要达到的结果'
        conditions = ('- ⚪ AC-01：原失败场景已恢复\n- ⚪ AC-02：受影响的关联路径没有回归'
                      if bug else '- ⚪ AC-01：填写可观察的输入、操作和预期结果')
        content = content.replace('〈范围提示〉', scope).replace('〈验收条件〉', conditions)
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
    pattern = field_pattern(name)
    if len(re.findall(pattern, text, re.M)) != 1:
        raise ValueError('需求卡字段缺失或重复：' + name)
    return re.sub(pattern, lambda match: '- ' + name + '：' + value, text, count=1, flags=re.M)


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


def manual_snapshot(root, card, inputs, staged=False):
    """人工证据复用源码快照算法；配置按原始内容绑定，不伪装为自动检查。"""
    checks = checks_module()
    config = {'profiles': {'manual': {'inputs': inputs, 'checks': {}}}}
    return checks.source_snapshot(root, config, 'manual', staged=staged,
                                  requirement=card['requirement'], raw_config=True)


def validation_proof(root, card, result=None, evidence=None, staged=False, evidence_inputs=None):
    if result is not None and evidence is not None:
        raise ValueError('只能提供一种验证证据')
    binding = {'requirement': card['requirement'],
               'requirement_fingerprint': hashlib.sha256(
                   semantic_content(card['text'], card['requirement'])).hexdigest()}
    if evidence_inputs is not None and evidence is None:
        raise ValueError('--evidence-input 只能与新的 --evidence 一起使用')
    snapshot = None
    if result is None and evidence is None:
        try:
            saved = json.loads(field(card['text'], '验证证据'))
            if saved['kind'] == 'result':
                result = saved['path']
            elif saved['kind'] == 'manual':
                if any(saved.get(key) != value for key, value in binding.items()):
                    raise ValueError('人工证据未绑定当前需求内容；请重新核对并提供 --evidence')
                evidence = saved['text']
                evidence_inputs = saved.get('inputs')
                if not evidence_inputs:
                    raise ValueError('人工证据缺少核对范围；请重新实际核对')
                snapshot = manual_snapshot(root, card, evidence_inputs)
                if saved.get('source_fingerprint') != snapshot['fingerprint']:
                    raise ValueError('人工证据输入已变化或缺少源码绑定；请重新实际核对')
            else:
                raise ValueError('未知证据类型')
        except (ValueError, KeyError, TypeError) as error:
            raise ValueError('没有有效的已绑定证据；请提供 --profile、--result 或 --evidence：'
                             + str(error)) from error
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
    inputs = evidence_inputs or ['.']
    if safe(root, checks_module().CONFIG).exists():
        code_suffixes = {'.swift', '.m', '.mm', '.h', '.py', '.sh', '.js', '.ts', '.c', '.cpp',
                         '.plist', '.entitlements', '.pbxproj', '.xcconfig'}
        changed = checks_module().input_paths(root, inputs, checks_module().changed_paths(root))
        if any(Path(name).suffix.lower() in code_suffixes for name in changed):
            raise ValueError('项目已配置自动验证且人工范围内存在代码变更；请使用 --profile 或 --result，'
                             '人工 AC 通过 --confirm-ac 实际确认')
    if snapshot is None:
        snapshot = manual_snapshot(root, card, inputs)
    if staged and manual_snapshot(root, card, inputs, staged=True) != snapshot:
        raise ValueError('人工证据暂存内容与已核对工作区不一致')
    return {'kind': 'manual', 'text': evidence.strip(), 'inputs': inputs,
            'source_fingerprint': snapshot['fingerprint'], **binding}


def complete(root, requirement, result=None, evidence=None, wait_user=False, profile=None,
             confirm_ac=None, evidence_inputs=None):
    if sum(value is not None for value in (result, evidence, profile)) > 1:
        raise ValueError('只能提供 --profile、--result、--evidence 中的一种')
    path = requirement_path(root, requirement)
    card = parse_card(path)
    require_ready(card)
    if card['state'] in ('暂停', '取消'):
        raise ValueError('请按用户明确决定先恢复需求为进行中，再验收')
    if evidence_inputs is not None and evidence is None:
        raise ValueError('--evidence-input 只能与新的 --evidence 一起使用')
    confirmed = set(confirm_ac or [])
    unknown = confirmed - {item['id'] for item in card['ac']}
    if unknown:
        raise ValueError('未知 AC：' + '、'.join(sorted(unknown)))
    if profile is not None:
        target, passed = checks_module().run(root, profile, requirement)
        if not passed:
            raise ValueError('验证未通过，需求状态保持不变')
        proof = {'kind': 'result', 'path': str(target.relative_to(root.resolve()))}
    else:
        proof = validation_proof(root, card, result, evidence, evidence_inputs=evidence_inputs)
    card = parse_card(path)
    text = card['text']
    for item in card['ac']:
        if item['id'] in confirmed:
            text = re.sub(r'^([ \t]*-[ \t]+)⚪([ \t]+' + re.escape(item['id']) + r'：)',
                          r'\g<1>✅\g<2>', text, flags=re.M)
            item['done'] = True
    pending = [item['id'] for item in card['ac'] if not item['done']]
    target_state = ('待用户验证' if wait_user else '进行中') if pending else '完成'
    text = replace_field(text, '状态', state_display(target_state))
    text = replace_field(text, '验证证据', json.dumps(proof, ensure_ascii=False))
    path.write_text(text)
    if target_state == '完成':
        message, next_step = '需求已完成，全部 AC 已确认且证据有效。', None
    else:
        message = ('验证证据已绑定，需求尚未完成；等待用户实际确认。' if wait_user
                   else '验证证据已绑定，需求尚未完成；请核对剩余 AC。')
        next_step = (f'核对实际证据后，在项目根执行 python3 scripts/teamflow.py req complete {requirement}'
                     ' --confirm-ac AC-编号（可重复传入，仅指定已实际确认的条件）；'
                     '输入未变化时复用证据，无需重跑测试。')
    print(json.dumps({'requirement': requirement, 'state': state_display(target_state),
                      'state_key': target_state, 'pending_ac': pending,
                      'pending_conditions': [{'id': item['id'], 'condition': item['condition']}
                                             for item in card['ac'] if not item['done']],
                      'message': message, 'next_step': next_step, 'evidence': proof}, ensure_ascii=False))


def git_root(root):
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], text=True).strip()
    if Path(actual).resolve() != root:
        raise ValueError('请从项目 Git 根目录执行')


def git_check(root, requirement, result=None, evidence=None, evidence_inputs=None):
    git_root(root)
    card = parse_card(requirement_path(root, requirement))
    names = [name for name in subprocess.check_output(
        ['git', '-C', str(root), 'diff', '--cached', '--name-only', '-z']).decode().split('\0') if name]
    if not names:
        raise ValueError('暂存区为空')
    # 人工提交检查只用于文档/记录，不能替代业务或工具代码的自动验证。
    saved_kind = None
    if result is None and evidence is None:
        try:
            saved_kind = json.loads(field(card['text'], '验证证据')).get('kind')
        except (ValueError, TypeError, AttributeError):
            pass
    if evidence is not None or saved_kind == 'manual':
        if any(Path(name).suffix.lower() not in ('.md', '.rst', '.txt') for name in names):
            raise ValueError('非文档暂存变更必须使用自动验证，不能仅提供人工证据')
    proof = validation_proof(root, card, result, evidence, staged=True, evidence_inputs=evidence_inputs)
    checks = checks_module()
    if proof['kind'] == 'result':
        report = json.loads(safe(root, proof['path']).read_text())
        inputs = checks.load_config(root)['profiles'][report['profile']].get('inputs')
        # 当前报告及其声明的原始日志是交付证据，不是待测源码。
        evidence_dir = Path(proof['path']).parent
        generated = {str(evidence_dir / 'result.json')}
        generated.update(str(evidence_dir / item['log']) for item in report['results'])
    else:
        inputs, generated = proof['inputs'], set()
    covered = checks.input_paths(root, inputs, set(names))
    covered.update({'requirements/' + requirement + '.md', checks.CONFIG} | generated)
    uncovered = sorted(set(names) - covered)
    if uncovered:
        raise ValueError('验证未覆盖暂存文件：' + '、'.join(uncovered) + '；请配置覆盖本次提交的 profile')
    risky = [name for name in names if Path(name).suffix.lower() in
             ('.swift', '.m', '.mm', '.h', '.plist', '.entitlements', '.pbxproj', '.xcconfig')]
    print(json.dumps({'requirement': requirement, 'staged_files': names, 'validation': proof,
                      'covered_files': names, 'uncovered_files': [], 'release_sensitive_files': risky,
                      'commit_trailer': 'Requirement: ' + requirement}, ensure_ascii=False, indent=2))


def release_record(root, operation, version, build, evidence, testflight_internal_only=False,
                   *, bundle_id=None, environment=None, commit=None, outcome=None):
    if not evidence.strip():
        raise ValueError('外部动作记录必须包含真实证据')
    if testflight_internal_only and operation != 'upload-testflight':
        raise ValueError('TestFlight Internal Only 仅适用于上传 TestFlight')
    identity = {'bundle_id': bundle_id, 'environment': environment,
                'version': version, 'build': build, 'commit': commit}
    if any(not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', value)
           for value in identity.values()):
        raise ValueError('发布身份必须明确填写 Bundle ID、环境、版本、build 和 commit；仅使用字母数字及 ._-')
    if not re.fullmatch(r'[0-9a-fA-F]{40}|[0-9a-fA-F]{64}', commit):
        raise ValueError('commit 必须为完整提交哈希')
    if outcome not in ('failed', 'processing', 'succeeded'):
        raise ValueError('结果必须为 failed、processing 或 succeeded')
    path = safe(root, f'releases/{bundle_id}-{environment}-{version}-{build}.md')
    header = '# App 发布动作\n\n' + json.dumps(identity, ensure_ascii=False, sort_keys=True) + '\n'
    if path.exists():
        text = path.read_text()
        if not text.startswith(header):
            raise ValueError('发布记录身份冲突：同一 App、环境和 build 不得替换 commit')
    else:
        text = header
    display_name = OPERATION_NAMES[operation]
    if testflight_internal_only:
        display_name += '（TestFlight Internal Only）'
    entry = '- ' + json.dumps({'time': datetime.now(timezone.utc).isoformat(),
                              'operation': operation, 'name': display_name,
                              'outcome': outcome, 'evidence': evidence.strip()}, ensure_ascii=False) + '\n'
    path.parent.mkdir(parents=True, exist_ok=True)
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
    top.add_parser('doctor', help='只读核对接入、配置、需求证据和可选模块索引')

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
    resume = req_sub.add_parser('resume', help='只读恢复摘要，不改变状态')
    resume.add_argument('requirement')
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
    done.add_argument('--evidence-input', action='append', help='人工核对的项目相对文件/目录，可重复；默认整个项目')
    done.add_argument('--confirm-ac', action='append', metavar='AC-编号',
                      help='显式确认已实际核对的条件，可重复传入；验证证据有效后才写入')

    verify = top.add_parser('verify')
    verify_sub = verify.add_subparsers(dest='command', required=True)
    verify_sub.add_parser('init')
    verify_sub.add_parser('list')
    verify_sub.add_parser('suggest', help='按改动路径建议验证范围，不运行检查')
    run = verify_sub.add_parser('run')
    run.add_argument('--profile', required=True)
    run.add_argument('--requirement', help='绑定本次需求的范围和 AC，忽略其他需求')

    git_area = top.add_parser('git')
    git_sub = git_area.add_subparsers(dest='command', required=True)
    check = git_sub.add_parser('check')
    check.add_argument('requirement')
    check.add_argument('--result')
    check.add_argument('--evidence')
    check.add_argument('--evidence-input', action='append')

    release = top.add_parser('release')
    release_sub = release.add_subparsers(dest='command', required=True)
    record = release_sub.add_parser('record')
    record.add_argument('operation', choices=OPERATIONS)
    record.add_argument('--version', required=True)
    record.add_argument('--build', required=True)
    record.add_argument('--evidence', required=True)
    record.add_argument('--testflight-internal-only', action='store_true')
    record.add_argument('--bundle-id', required=True)
    record.add_argument('--environment', required=True)
    record.add_argument('--commit', required=True)
    record.add_argument('--outcome', required=True, choices=('failed', 'processing', 'succeeded'))

    args = parser.parse_args()
    root = args.project.resolve()
    try:
        if args.area == 'doctor':
            from diagnostics import doctor
            report = doctor(root)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 1 if report['needs_action'] else 0
        elif args.area == 'req':
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
            elif args.command == 'resume':
                from diagnostics import resume
                print(json.dumps(resume(root, args.requirement), ensure_ascii=False, indent=2))
            elif args.command == 'state':
                set_state(root, args.requirement, args.state, args.reason)
            else:
                complete(root, args.requirement, args.result, args.evidence, args.wait_user,
                         args.profile, args.confirm_ac, args.evidence_input)
        elif args.area == 'verify':
            checks = checks_module()
            if args.command == 'init':
                path = checks.local_path(root, checks.CONFIG)
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open('x') as stream:
                    json.dump({'schema_version': 2, 'profiles': {}}, stream, indent=2)
                    stream.write('\n')
                print('已创建空验证配置：' + str(path))
            elif args.command == 'suggest':
                print(json.dumps(checks.suggest(root), ensure_ascii=False, indent=2))
            elif args.command == 'list':
                print(json.dumps(checks.load_config(root), ensure_ascii=False, indent=2))
            else:
                _, passed = checks.run(root, args.profile, args.requirement)
                return 0 if passed else 1
        elif args.area == 'git':
            git_check(root, args.requirement, args.result, args.evidence, args.evidence_input)
        else:
            release_record(root, args.operation, args.version, args.build, args.evidence,
                           args.testflight_internal_only, bundle_id=args.bundle_id,
                           environment=args.environment, commit=args.commit, outcome=args.outcome)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(2, str(error) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
