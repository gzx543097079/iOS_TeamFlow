#!/usr/bin/env python3
"""TeamFlow 共用命令入口：接入、升级、需求、验证、提交前核对与模块索引。"""
import difflib
import hashlib
import json
import re
import secrets
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from teamflow_common import local_path as safe
from requirement_model import (ID, STATES, BLOCK_KINDS, AC_LINE, state_display, parse_card,
                               parse_requirement, semantic_content, require_ready, dump_card, split_card,
                               acceptance_fingerprints, stale_acceptance)

TEMPLATE = Path(__file__).resolve().parents[1] / 'references/templates/requirement.md'


def now():
    return datetime.now().astimezone().isoformat(timespec='seconds')


def requirement_path(root, requirement):
    if not ID.fullmatch(requirement):
        raise ValueError('需求编号格式应为 REQ-YYYYMMDD-xxxx')
    path = safe(root, 'requirements/' + requirement + '.md')
    if not path.is_file():
        raise ValueError('需求不存在：' + requirement)
    return path


def cards(root):
    directory = safe(root, 'requirements')
    if not directory.exists():
        return [], []
    rows, skipped = [], []
    for path in directory.glob('REQ-*.md'):
        if not ID.fullmatch(path.stem):
            continue
        try:
            card = parse_card(safe(root, str(path.relative_to(root))))
        except (OSError, ValueError) as error:
            skipped.append({'requirement': path.stem, 'error': str(error)})
            continue
        rows.append({'requirement': path.stem, 'title': card['title'], 'state': card['state_display'],
                     'state_key': card['state'], 'progress': card['progress'],
                     'created': str(card['meta'].get('created', ''))})
    return sorted(rows, key=lambda row: (row['created'], row['requirement'])), skipped


def write_card(path, meta, body):
    text = dump_card(meta, body)
    parse_requirement(text, path.stem)
    path.write_text(text)


def append_decision(body, entry):
    """追加到“## 决策与异常”末尾；没有该节时新建。"""
    lines = body.rstrip('\n').split('\n')
    try:
        start = next(i for i, line in enumerate(lines) if re.match(r'^##[ \t]+决策与异常[ \t]*$', line))
    except StopIteration:
        return '\n'.join(lines) + '\n\n## 决策与异常\n\n' + entry + '\n'
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith('## ')), len(lines))
    while end > start + 1 and not lines[end - 1].strip():
        end -= 1
    insert = [entry] if end > start + 1 else ['', entry]
    return '\n'.join(lines[:end] + insert + lines[end:]) + '\n'


def create(root, title, queued=False, bug=False):
    if not title.strip() or '\n' in title or '\r' in title:
        raise ValueError('标题须为单行非空文本')
    directory = safe(root, 'requirements')
    directory.mkdir(parents=True, exist_ok=True)
    scope = '〈填写缺陷现象、触发条件和预期修复结果〉' if bug else '〈填写本次要达到的结果〉'
    conditions = ('- [ ] AC-01：原失败场景已恢复\n- [ ] AC-02：受影响的关联路径没有回归'
                  if bug else '- [ ] AC-01：〈填写可观察的输入、操作和预期结果〉')
    # 日期 + 随机后缀与分支无关，多分支并行创建不会撞号；极少数同名时重新生成。
    for _ in range(100):
        requirement = 'REQ-' + datetime.now().strftime('%Y%m%d') + '-' + secrets.token_hex(2)
        target = directory / (requirement + '.md')
        content = (TEMPLATE.read_text().replace('REQ-00000000-0000', requirement)
                   .replace('〈需求标题〉', title.strip()).replace('〈创建时间〉', now())
                   .replace('〈范围提示〉', scope).replace('〈验收条件〉', conditions))
        meta, body = split_card(content)
        meta['type'] = 'bug' if bug else 'feature'
        if queued:
            meta['queued'] = True
        try:
            with target.open('x') as stream:
                stream.write(dump_card(meta, body))
        except FileExistsError:
            continue
        return {'requirement': requirement, 'card': str(target.relative_to(root)),
                'state': parse_card(target)['state_display']}
    raise ValueError('无法生成不重复的需求编号')


def set_state(root, requirement, state, reason=None, blocked=None, reopen_ac=None):
    if state not in STATES:
        raise ValueError('未知状态：' + state)
    if state in ('完成', '待用户验证'):
        raise ValueError('完成或待用户验证必须通过 req complete 绑定证据')
    reason = (reason or '').strip()
    path = requirement_path(root, requirement)
    card = parse_card(path)
    if state == '阻塞' and blocked not in BLOCK_KINDS:
        raise ValueError('阻塞必须用 --blocked 指定原因类型：' + '/'.join(BLOCK_KINDS))
    if state != '阻塞' and blocked is not None:
        raise ValueError('--blocked 只用于阻塞状态')
    reopen = set(reopen_ac or [])
    if reopen and state != '进行中':
        raise ValueError('--reopen-ac 只用于恢复为进行中')
    unknown = reopen - {item['id'] for item in card['ac']}
    if unknown:
        raise ValueError('未知 AC：' + '、'.join(sorted(unknown)))
    reopening = state == '进行中' and card['state'] == '完成'
    if reopening and not reopen:
        # 不取消勾选的重开会被下一次 req complete 复用证据直接判回完成。
        raise ValueError('重开完成的需求必须用 --reopen-ac 指定需重新验收的 AC')
    resuming = state == '进行中' and card['state'] in ('阻塞', '取消', '完成')
    if (state in ('阻塞', '取消') or resuming) and not reason:
        raise ValueError(('重开' if reopening else '恢复' if resuming else state) + '必须填写 --reason')
    meta = dict(card['meta'], state=state)
    for key in ('blocked', 'reason', 'queued'):
        meta.pop(key, None)
    if state == '阻塞':
        meta.update(blocked=blocked, reason=reason)
    elif state == '取消':
        meta['reason'] = reason
    body = card['body']
    if reopen:
        lines = body.split('\n')
        for index, line in enumerate(lines):
            match = AC_LINE.match(line)
            if match and match.group(2) in reopen:
                lines[index] = re.sub(r'\[[xX]\]', '[ ]', line, count=1)
        body = '\n'.join(lines)
        users = [item for item in meta.get('user_confirmed') or [] if item not in reopen]
        meta['user_confirmed'] = users or None
    if reason:
        label = state_display(state) + (f'（{blocked}）' if blocked else '')
        reopened = f"（重开 {'、'.join(sorted(reopen))}）" if reopen else ''
        body = append_decision(body, f'- {now()}：{label}{reopened} — {reason}')
    write_card(path, meta, body)
    return {'requirement': requirement, 'state': parse_card(path)['state_display'], 'state_key': state}


def checks_module():
    import project_checks
    return project_checks


def requirement_fingerprint(card):
    return 'sha256:' + hashlib.sha256(semantic_content(card['text'], card['requirement'])).hexdigest()


def manual_snapshot(root, card, inputs, staged=False):
    """人工证据复用源码快照算法；配置按原始内容绑定，不伪装为自动检查。"""
    config = {'profiles': {'manual': {'inputs': inputs, 'checks': {}}}}
    return checks_module().source_snapshot(root, config, 'manual', staged=staged,
                                           requirement=card['requirement'], raw_config=True)


def verify_saved(root, card, staged=False):
    """复核卡片中已绑定的证据摘要；不读取本地日志。"""
    saved = card['evidence']
    if not isinstance(saved, dict) or saved.get('kind') not in ('result', 'manual'):
        raise ValueError('没有已绑定的证据；请提供 --profile、--result 或 --evidence')
    if saved.get('requirement') != requirement_fingerprint(card):
        raise ValueError('需求范围或 AC 已变化，旧证据不能复用；请重新验证')
    if saved['kind'] == 'result':
        checks_module().verify_summary(root, card['requirement'], saved, staged=staged)
        return saved
    paths = saved.get('paths')
    if not isinstance(paths, list) or not paths:
        raise ValueError('人工证据缺少核对范围；请重新实际核对')
    snapshot = manual_snapshot(root, card, paths)
    if saved.get('fingerprint') != 'sha256:' + snapshot['fingerprint']:
        raise ValueError('人工证据输入已变化；请重新实际核对')
    if staged and manual_snapshot(root, card, paths, staged=True) != snapshot:
        raise ValueError('人工证据暂存内容与已核对工作区不一致')
    return saved


def committed_evidence(root, card, revision):
    """卡片在指定提交中记录的证据指纹与当前一致时返回该指纹。"""
    fingerprint = card['evidence'].get('fingerprint') if isinstance(card['evidence'], dict) else None
    shown = subprocess.run(['git', '-C', str(root), 'show', f"{revision}:requirements/{card['requirement']}.md"],
                           capture_output=True, text=True)
    return fingerprint if fingerprint and shown.returncode == 0 and fingerprint in shown.stdout else None


def delivered_commit(root, card):
    """已完成需求的自动证据与某个提交的输入一致时返回该提交；后续代码演进不影响交付结论。"""
    saved = card['evidence']
    if (card['state'] != '完成' or not isinstance(saved, dict) or saved.get('kind') != 'result'
            or saved.get('requirement') != requirement_fingerprint(card)):
        return None
    history = subprocess.run(['git', '-C', str(root), 'log', '--format=%H', '--',
                              f"requirements/{card['requirement']}.md"], capture_output=True, text=True)
    for commit in history.stdout.split() if history.returncode == 0 else []:
        if not committed_evidence(root, card, commit):
            continue
        try:
            snapshot = checks_module().source_snapshot(root, None, saved.get('profile'),
                                                       requirement=card['requirement'], commit=commit,
                                                       checks=saved.get('checks'), algorithm=saved.get('algorithm', 'sha256-files-v5'))
        except (ValueError, KeyError, TypeError, subprocess.CalledProcessError):
            continue
        if saved.get('fingerprint') == 'sha256:' + snapshot['fingerprint']:
            return commit
    return None


def manual_proof(root, card, evidence, evidence_inputs=None):
    if not isinstance(evidence, str) or not evidence.strip():
        raise ValueError('验证证据不能为空')
    checks = checks_module()
    paths = evidence_inputs or ['.']
    if safe(root, checks.CONFIG).exists():
        # 与 git check 共用文档白名单：脚本、场景、配置等任何非文档改动都不能只靠人工文字。
        changed = checks.input_paths(root, paths, checks.changed_paths(root, card['requirement']))
        code = checks.non_document_paths(root, changed)
        if code:
            raise ValueError('项目已配置自动验证且人工范围内存在非文档改动：' + '、'.join(code[:5]) +
                             '；请使用 --profile 或 --result，人工 AC 通过 --confirm-ac 实际确认')
    snapshot = manual_snapshot(root, card, paths)
    return {'kind': 'manual', 'note': evidence.strip(), 'paths': paths,
            'fingerprint': 'sha256:' + snapshot['fingerprint'],
            'requirement': requirement_fingerprint(card), 'at': now()}


def complete(root, requirement, result=None, evidence=None, wait_user=False, profile=None,
             confirm_ac=None, evidence_inputs=None, user_confirmed=None, rerun=False, announce=None):
    if rerun and profile is None:
        raise ValueError('--rerun 必须与 --profile 一起使用')
    if sum(value is not None for value in (result, evidence, profile)) > 1:
        raise ValueError('只能提供 --profile、--result、--evidence 中的一种')
    if evidence_inputs is not None and evidence is None:
        raise ValueError('--evidence-input 只能与新的 --evidence 一起使用')
    path = requirement_path(root, requirement)
    card = parse_card(path)
    require_ready(card)
    if card['state'] in ('阻塞', '取消'):
        raise ValueError('需求处于' + card['state_display'] + '；请按用户明确决定先执行 '
                         'req state --state 进行中 --reason "恢复依据"，再验收')
    by_user = set(user_confirmed or [])
    confirmed = set(confirm_ac or []) | by_user
    unknown = confirmed - {item['id'] for item in card['ac']}
    if unknown:
        raise ValueError('未知 AC：' + '、'.join(sorted(unknown)))
    checks = checks_module()
    verification = None

    def run_profile(name, auto=False):
        previous = card.get('evidence') or {}
        selected = (previous.get('checks') if previous.get('profile') == name
                    and previous.get('requirement') != requirement_fingerprint(card) else None)
        target, passed = checks.run(root, name, requirement, rerun=rerun, selected=selected,
                                    announce=announce)
        line = checks.describe_run(root, target)
        if auto:
            line = line.replace('（' + name + '）', '（' + name + '，按改动自动选择）', 1)
        if not passed:
            raise ValueError(line + '；需求状态保持不变')
        return line, checks.summarize(root, target)

    if profile is not None:
        try:
            if rerun:
                raise ValueError('显式要求重新执行')
            proof = verify_saved(root, card)
            if proof.get('kind') != 'result' or proof.get('profile') != profile:
                raise ValueError('所选 profile 与已有证据不同')
            verification = '复用验证，未运行测试（' + profile + '）'
        except ValueError as error:
            verification, proof = run_profile(profile)
            verification = verification + '；重新验证：' + str(error)
    elif result is not None:
        report = checks.verify(root, result)
        if report.get('requirement') != requirement:
            raise ValueError('验证结果未绑定当前需求：' + requirement)
        proof = checks.summarize(root, safe(root.resolve(), result))
        verification = '复用验证结果，未运行测试'
    elif evidence is not None:
        proof = manual_proof(root, card, evidence, evidence_inputs)
    else:
        try:
            proof = verify_saved(root, card)
            verification = '复用验证，未运行测试'
        except ValueError as saved_error:
            # 已绑定证据不可复用时，按适用范围与优先级选择 profile 重新验证。
            if not safe(root, checks.CONFIG).exists():
                raise
            previous = card.get('evidence') or {}
            config = checks.load_config(root)
            old_profile = previous.get('profile')
            if (previous.get('checks') and old_profile in config['profiles']
                    and not config['profiles'][old_profile].get('manual')
                    and previous.get('requirement') != requirement_fingerprint(card)):
                selected = old_profile
            else:
                try:
                    selected = checks.select_profile(root, requirement)
                except ValueError as error:
                    raise ValueError(f'{saved_error}；{error}') from error
            verification, proof = run_profile(selected, auto=True)
            verification = verification + '；重新验证：' + str(saved_error)
    card = parse_card(path)
    stale = stale_acceptance(card)
    lines = card['body'].split('\n')
    for index, line in enumerate(lines):
        match = AC_LINE.match(line)
        if match and match.group(2) in stale - confirmed:
            lines[index] = re.sub(r'\[[xX]\]', '[ ]', line, count=1)
        elif match and match.group(2) in confirmed:
            lines[index] = re.sub(r'\[ \]', '[x]', line, count=1)
    body = '\n'.join(lines)
    done = {item['id'] for item in parse_requirement(dump_card(card['meta'], body), requirement)['ac']
            if item['done']}
    pending = [item for item in card['ac'] if item['id'] not in done]
    target_state = ('待用户验证' if wait_user else '进行中') if pending else '完成'
    meta = dict(card['meta'], state=target_state, evidence=proof)
    meta.pop('queued', None)
    # 用户确认单独记录在头部，供评审区分 Agent 自行核对与用户实际确认。
    users = sorted(((set(meta.get('user_confirmed') or []) - stale) | by_user) & done)
    meta['user_confirmed'] = users or None
    meta['confirmed_ac'] = {key: value for key, value in acceptance_fingerprints(card).items() if key in done}
    write_card(path, meta, body)
    card = parse_card(path)
    return {'requirement': requirement, 'state': card['state_display'], 'state_key': target_state,
            'progress': card['progress']['display'], 'verification': verification,
            'pending_ac': [item['id'] for item in pending],
            'pending_conditions': [{'id': item['id'], 'condition': item['condition']} for item in pending],
            'evidence': proof}


def git_root(root):
    actual = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--show-toplevel'], text=True).strip()
    if Path(actual).resolve() != root:
        raise ValueError('请从项目 Git 根目录执行')


# 提交时提示需关注发布影响的文件：iOS 工程与签名配置、Godot 工程与导出预设。
RELEASE_SENSITIVE = ('.swift', '.m', '.mm', '.h', '.plist', '.entitlements', '.pbxproj', '.xcconfig',
                     '.gd', '.tscn', '.tres', '.godot', '.cfg')


def git_check(root, requirement, result=None, evidence=None, evidence_inputs=None):
    git_root(root)
    card = parse_card(requirement_path(root, requirement))
    names = [name for name in subprocess.check_output(
        ['git', '-C', str(root), 'diff', '--cached', '--name-only', '-z']).decode().split('\0') if name]
    if not names:
        raise ValueError('暂存区为空')
    checks = checks_module()
    staged_logs = [name for name in names if name.startswith('logs/project-checks/')
                   and safe(root, name).exists()]
    if staged_logs:
        raise ValueError('验证日志是本地证据，不应提交；请移出暂存区并在 .gitignore 加入 /logs/project-checks/')
    # 人工提交检查只用于文档/记录，不能替代业务或工具代码的自动验证。
    manual = evidence is not None or (result is None and (card['evidence'] or {}).get('kind') == 'manual')
    installed = checks.installed_files(root) & set(names)
    code = checks.non_document_paths(root, names)
    if manual and code:
        raise ValueError('非文档暂存变更必须使用自动验证，不能仅提供人工证据：' + '、'.join(code[:5]))
    if result is not None:
        report = checks.verify(root, result, staged=True)
        if report.get('requirement') != requirement:
            raise ValueError('验证结果未绑定当前需求：' + requirement)
        proof = checks.summarize(root, safe(root.resolve(), result))
    elif evidence is not None:
        proof = manual_proof(root, card, evidence, evidence_inputs)
        if manual_snapshot(root, card, proof['paths'], staged=True)['fingerprint'] != proof['fingerprint'][7:]:
            raise ValueError('人工证据暂存内容与已核对工作区不一致')
    else:
        proof = verify_saved(root, card, staged=True)
    inputs = (checks.evidence_inputs(root, proof)
              if proof['kind'] == 'result' else proof['paths'])
    covered = checks.input_paths(root, inputs, set(names)) if inputs != [] else set()
    covered.update({'requirements/' + requirement + '.md', checks.CONFIG})
    covered.update(installed)
    # 移出 Git 的历史日志不改变源码；新增或修改日志仍须由 profile 覆盖。
    deleted = subprocess.check_output(['git', '-C', str(root), 'diff', '--cached', '--name-only',
                                       '--diff-filter=D', '-z']).decode().split('\0')
    covered.update(name for name in deleted if name.startswith('logs/'))
    uncovered = sorted(set(names) - covered)
    if uncovered:
        raise ValueError('验证未覆盖暂存文件：' + '、'.join(uncovered) + '；请配置覆盖本次提交的 profile')
    risky = [name for name in names if name not in installed and Path(name).suffix.lower() in RELEASE_SENSITIVE]
    # 验证配置总视为覆盖（其所选 profile 已进入指纹）；其他 profile 的命令变化未经本次证据执行，须明确提示。
    unverified = (checks.changed_profiles(root, keep={proof['profile']} if proof['kind'] == 'result' else ())
                  if checks.CONFIG in names else [])
    return {'requirement': requirement, 'staged_files': names, 'validation': proof,
            'release_sensitive_files': risky, 'unverified_profiles': unverified,
            'commit_trailer': 'Requirement: ' + requirement}


# 轻量改动只放行纯文档；.txt 可能是依赖清单等工程输入，需求卡须经证据复核。
LIGHTWEIGHT_SUFFIXES = ('.md', '.rst')


def lightweight_documents(root, names):
    checks = checks_module()
    return all(Path(name).suffix.lower() in LIGHTWEIGHT_SUFFIXES and not name.startswith('requirements/')
               and not checks.excluded_input(name) and name != checks.CONFIG for name in names)


def hook_check(root):
    """只读提交门禁：复用能够覆盖整个暂存区的需求证据（自动或文档人工证据），不执行项目命令。"""
    checks = checks_module()
    if not checks.load_config(root)['profiles']:
        raise ValueError('未配置任何验证 profile')
    staged = set(name for name in subprocess.check_output(
        ['git', '-C', str(root), 'diff', '--cached', '--name-only', '-z']).decode().split('\0') if name)
    if staged and lightweight_documents(root, staged):
        return {'requirement': None, 'staged_files': sorted(staged), 'validation': {'kind': 'document'},
                'release_sensitive_files': [], 'unverified_profiles': [], 'commit_trailer': None}
    rows, _ = cards(root)
    candidates = []
    for row in rows:
        if row['state_key'] == '取消':
            continue
        card = parse_card(requirement_path(root, row['requirement']))
        if (card['evidence'] or {}).get('kind') in ('result', 'manual'):
            candidates.append(row)
    # 本次暂存的卡最可能对应提交，其次是进行中的卡与新卡；历史卡放最后，避免逐张哈希全部旧证据。
    candidates.sort(key=lambda row: row['created'], reverse=True)
    candidates.sort(key=lambda row: ('requirements/' + row['requirement'] + '.md' not in staged,
                                     row['state_key'] == '完成'))
    problems = []
    for row in candidates:
        try:
            return git_check(root, row['requirement'])
        except ValueError as error:
            problems.append(row['requirement'] + '：' + str(error))
    reason = '；'.join(problems[:3]) or '没有覆盖暂存内容的已绑定证据'
    hint = '；请先 req complete <需求编号> --profile <覆盖本次提交的 profile>，再暂存验收后的内容'
    raise ValueError('提交证据检查失败，未运行测试：' + reason + hint)


def status(root, requirement):
    """只读：卡片内容 + 证据是否仍可复用 + 下一步；不修改状态。"""
    from diagnostics import requirement_summary
    card = parse_card(requirement_path(root, requirement))
    summary, _ = requirement_summary(root, requirement)
    return {'requirement': requirement, 'title': card['title'], 'type': card['type'],
            'state': card['state_display'], 'state_key': card['state'], 'blocked': card['blocked'],
            'reason': card['reason'], 'progress': card['progress'], 'scope': card['scope'],
            'excluded': card['excluded'], 'ac': card['ac'], 'evidence': card['evidence'],
            'user_confirmed': card['meta'].get('user_confirmed') or [],
            'evidence_status': summary['evidence_status'], 'problems': summary['problems'],
            'decisions': summary['decisions'], 'next_step': summary['next_step']}


# 保留入口导出，调用方继续使用相同命令接口。
from cli_output import render
from cli_parser import build_parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    root = args.project.resolve()

    def progress(line):
        # 开始提示走 stderr，不影响 --json 输出；长验证可据此后台运行并等待完成。
        print(line, file=sys.stderr, flush=True)

    def emit(kind, data, as_json=None):
        if getattr(args, 'json', False):
            print(json.dumps(data if as_json is None else as_json, ensure_ascii=False, indent=2))
        else:
            print(render(kind, data))

    try:
        if args.area == 'doctor':
            from diagnostics import doctor, format_report
            report = doctor(root)
            print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report))
            return 1 if report['needs_action'] else 0
        elif args.area == 'permissions':
            import setup_project
            report = setup_project.permissions(root, args.mode, args.plan)
            print(json.dumps(report, ensure_ascii=False, indent=2))
        elif args.area == 'req':
            if args.command == 'create':
                emit('create', create(root, args.title, args.queued, args.bug))
            elif args.command == 'list':
                rows, skipped = cards(root)
                # 默认只列未完成需求，避免历史卡片让输出随项目时间线性增长。
                shown = rows if args.all else [row for row in rows if row['state_key'] not in ('完成', '取消')]
                emit('list', (shown, skipped, len(rows) - len(shown)), {'requirements': shown, 'skipped': skipped})
            elif args.command == 'status':
                emit('status', status(root, args.requirement))
            elif args.command == 'pr':
                from diagnostics import pr_body
                body = pr_body(root, args.requirement)
                print(json.dumps(body, ensure_ascii=False, indent=2) if args.json else body['title'] + '\n\n' + body['body'])
            elif args.command == 'state':
                emit('state', set_state(root, args.requirement, args.state, args.reason, args.blocked,
                                        args.reopen_ac))
            else:
                emit('complete', complete(root, args.requirement, args.result, args.evidence, args.wait_user,
                                          args.profile, args.confirm_ac, args.evidence_input,
                                          args.user_confirmed, args.rerun, announce=progress))
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
                emit('suggest', checks.suggest(root, args.requirement))
            elif args.command == 'list':
                print(json.dumps(checks.load_config(root), ensure_ascii=False, indent=2))
            else:
                target, passed = checks.run(root, args.profile, args.requirement, rerun=args.rerun,
                                            announce=progress)
                if args.json:
                    print(target.read_text().rstrip())
                else:
                    print(checks.describe_run(root, target))
                return 0 if passed else 1
        elif args.area == 'git' and args.command == 'ci':
            from diagnostics import ci_check, format_report
            report = ci_check(root, args.base)
            print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else format_report(report))
            return 1 if report['needs_action'] else 0
        elif args.area == 'git' and args.command == 'hook':
            emit('git', hook_check(root))
        elif args.area == 'git':
            emit('git', git_check(root, args.requirement, args.result, args.evidence, args.evidence_input))
        elif args.area == 'setup':
            import setup_project
            skill = Path(__file__).resolve().parents[1]
            planned = setup_project.setup(root, skill, args.plan, args.claude_skill_link, args.mode,
                                          args.git_hook, args.no_git_hook)
            if args.plan:
                for name, data in planned.items():
                    current = Path(name) if Path(name).is_absolute() else safe(root, name)
                    before = current.read_text() if current.exists() else ''
                    print(''.join(difflib.unified_diff(before.splitlines(keepends=True),
                                                       data.decode().splitlines(keepends=True),
                                                       fromfile=name, tofile=name)), end='')
            else:
                if not setup_project.source_repository(root):
                    mode = setup_project.install_mode(root)
                    print('已接入 ' + setup_project.MODE_LABELS[mode] + '：' + str(root))
                if args.git_hook:
                    print('提交前检查：pre-commit 只复核暂存内容的已绑定证据')
                elif args.no_git_hook:
                    print('已移除 TeamFlow 管理的 pre-commit')
        elif args.area == 'upgrade':
            import upgrade
            result = upgrade.upgrade(root, args.package, args.force, args.plan, args.mode)
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else
                  upgrade.describe(result, args.plan))
        elif args.area == 'module':
            import module_context
            module_root = module_context.project_root(root)
            if args.command == 'record':
                recorded = module_context.record(module_root, args.name, args.path, args.trigger, args.responsibility,
                                                 args.entry, args.dependency, args.caller, args.verification,
                                                 args.cross_cutting)
                print('已记录模块：' + recorded['name'])
            else:
                report = module_context.inspect(module_root, module_context.load_manifest(module_root),
                                                modules=getattr(args, 'module', None),
                                                query=getattr(args, 'query', None),
                                                all_modules=args.command == 'validate' or args.all)
                emit('module', report)
                if args.command == 'validate' and any(m['status'] == 'invalid' for m in report['modules']):
                    return 1
        else:
            platform_scripts = safe(root, '.agents/skills/iOS/scripts')
            if not (platform_scripts / 'install_logging.py').is_file():
                raise ValueError('缺少 iOS 日志组件安装工具')
            sys.path.insert(0, str(platform_scripts))
            import install_logging
            result = install_logging.install(root, args.destination, args.language)
            print(json.dumps(result, ensure_ascii=False, indent=2) if args.json else
                  '日志组件：' + '、'.join(result['files']) + '\n下一步：' + result['next'])
    except (ValueError, OSError, KeyError, TypeError, UnicodeError, subprocess.CalledProcessError) as error:
        parser.exit(2, str(error) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
