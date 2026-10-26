"""只读诊断和需求状态摘要，不写第二套状态或执行项目检查。"""
import json
import subprocess
from teamflow_common import local_path
from requirement_model import require_ready, parse_card, stale_acceptance

LARGE_PROJECT_FILES = 1000


def requirement_summary(root, requirement):
    """返回证据有效性、问题与下一步，以及是否为已交付但证据无法对应交付提交的历史需求。"""
    import teamflow as flow
    card = parse_card(flow.requirement_path(root, requirement))
    problems = []
    try:
        require_ready(card)
    except ValueError as error:
        problems.append(str(error))
    if stale_acceptance(card):
        problems.append('AC 内容已变化，旧确认失效；请重新核对并执行 req complete')
    content_ready = not problems
    pending = [item for item in card['ac'] if not item['done']]
    finished = card['state'] == '完成' and content_ready and not pending
    history = False
    try:
        flow.verify_saved(root, card)
        evidence = '有效'
    except (ValueError, OSError, KeyError, TypeError) as error:
        commit = flow.delivered_commit(root, card) if finished else None
        if commit:
            # 交付提交与验证输入一致，之后的代码演进不影响已完成结论。
            evidence = '交付时有效（提交 ' + commit[:7] + '）'
        elif card['state'] == '进行中' and not card['evidence'] and content_ready:
            # 实施中尚未验收是正常状态，不计为问题。
            evidence = '未验证'
        else:
            evidence = '缺失或失效'
            problems.append(str(error))
            # 已提交的完成卡对不上交付提交只作历史提示；尚未提交即失效说明交付前内容已变化。
            history = finished and bool(flow.committed_evidence(root, card, 'HEAD'))
    if card['state'] == '取消' or card['blocked'] == '暂停':
        next_step = '等待用户明确恢复；不得自动继续'
    elif card['state'] == '阻塞':
        next_step = '核对阻塞原因，解除条件后恢复'
    elif history:
        next_step = '历史需求已交付；旧证据无法对应交付提交，无需重开'
    elif problems:
        next_step = '补齐实际需求内容或重新核对失效证据'
    elif evidence == '未验证':
        next_step = '实施定稿后统一验收：req complete ' + requirement + ' --profile <名>'
    elif pending and card['state'] == '待用户验证':
        next_step = '等待用户确认剩余 AC；用户明确确认后用 --user-confirmed 记录'
    elif pending:
        next_step = '实际核对剩余 AC，使用 --confirm-ac 确认；证据有效时无需重跑'
    elif card['state'] == '完成':
        next_step = '需求已完成；证据有效时不重跑测试，仅执行用户明确授权的交付目标'
    else:
        next_step = '复用有效证据执行 req complete'
    decisions = card['body'].split('## 决策与异常', 1)
    summary = {'requirement': requirement, 'state': card['state_display'],
               'pending_ac': pending, 'evidence_status': evidence, 'problems': problems,
               'decisions': decisions[1].strip() if len(decisions) == 2 else '', 'next_step': next_step}
    return summary, history


def doctor(root):
    import setup_project
    import project_checks
    import module_context
    checks = []
    setup = setup_project.diagnose(root)
    # 工作流工具和组件仓库不一定需要 Xcode；只有 App 检查实际运行时才要求它。
    checks.extend(item for item in setup['checks'] if item['item'] != 'Xcode')
    # 配置文件缺失已由“项目验证”报告，不再重复一项原始错误。
    try:
        if not local_path(root, project_checks.CONFIG).exists():
            raise FileNotFoundError
        config = project_checks.load_config(root)
        if not config['profiles']:
            raise ValueError('未配置任何验证 profile')
        for profile in config['profiles']:
            project_checks.source_snapshot(root, config, profile)
        checks.append({'item': '验证配置及输入', 'status': '就绪', 'detail': list(config['profiles'])})
        # 升级不改项目脚本；旧形态在此提示，按 INSTALL「升级」在升级任务中迁移。
        issues = project_checks.legacy_layout(root, config)
        if issues:
            checks.append({'item': '验证配置形态',
                           'status': '需处理' if any(i['status'] == '需处理' for i in issues) else '提示',
                           'detail': [i['detail'] for i in issues]
                                      + ['按仓库 README「验证配置迁移」执行；细则见 CHECKS-CONFIG「从全量脚本迁移」与「小任务耗时」'
                                         '（日常=编译+模块测，全量/Release=manual）']})
    except FileNotFoundError:
        pass
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        checks.append({'item': '验证配置及输入', 'status': '需处理', 'detail': str(error)})
    directory = local_path(root, 'requirements')
    if directory.exists():
        for path in sorted(directory.glob('REQ-*.md')):
            try:
                local_path(root, str(path.relative_to(root)))
                summary, finished = requirement_summary(root, path.stem)
                card_state = summary['state'].split(' ', 1)[-1]
                status = ('需处理' if summary['problems'] and not finished else '历史' if summary['problems']
                          else '进行中' if card_state.startswith(('进行中', '待用户验证')) else '就绪')
                checks.append({'item': path.stem, 'status': status, 'detail': summary})
            except (ValueError, OSError, KeyError, TypeError) as error:
                checks.append({'item': path.name, 'status': '需处理', 'detail': str(error)})
    try:
        manifest = local_path(root, str(module_context.MANIFEST))
        if manifest.exists():
            data = module_context.load_manifest(root)
            summary = module_context.inspect(root, data, all_modules=True)
            # 改动只是增量读取线索；只有索引失效才需要处理。
            problem = any(m['status'] == 'invalid' for m in summary['modules'])
            checks.append({'item': '模块索引', 'status': '需处理' if problem else '就绪', 'detail': summary})
        else:
            listed = subprocess.run(['git', '-C', str(root), 'ls-files', '-z'], capture_output=True, text=True)
            count = len([name for name in listed.stdout.split('\0') if name]) if listed.returncode == 0 else 0
            if count >= LARGE_PROJECT_FILES:
                # 大工程没有索引时，Agent 定位代码只能广泛搜索，读取成本随规模增长。
                checks.append({'item': '模块索引', 'status': '提示',
                               'detail': f'Git 跟踪 {count} 个文件，建议按 MODULE-CONTEXT 记录模块索引以增量定位'})
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        checks.append({'item': '模块索引', 'status': '需处理', 'detail': str(error)})
    return {'checks': checks, 'needs_action': any(item['status'] == '需处理' for item in checks)}


def _brief(item):
    detail = item['detail']
    if isinstance(detail, list):
        return '、'.join(map(str, detail))
    if isinstance(detail, dict) and 'requirement' in detail:
        return '；'.join(detail['problems']) + '（req status ' + detail['requirement'] + ' 查看）'
    if isinstance(detail, dict) and 'modules' in detail:
        counts = {}
        for module in detail['modules']:
            counts[module['status']] = counts.get(module['status'], 0) + 1
        return (f"{len(detail['modules'])} 个模块，基线 {detail['base']}：" +
                '，'.join(f'{name} {count}' for name, count in sorted(counts.items())) + '（--json 查看）')
    return str(detail)


def format_report(report):
    """默认摘要：每项一行，就绪需求与历史需求各合并为一行。"""
    lines, ready, history = [], [], []
    for item in report['checks']:
        if item['item'].startswith('REQ-') and item['status'] == '就绪':
            ready.append(item['item'])
        elif item['status'] == '历史':
            history.append(item['item'])
        elif item['status'] == '进行中':
            lines.append(f"[进行中] {item['item']}：{item['detail']['next_step']}")
        else:
            lines.append(f"[{item['status']}] {item['item']}：{_brief(item)}")
    if ready:
        lines.append(f'[就绪] 需求：{len(ready)} 张')
    if history:
        lines.append(f'[历史] 已交付需求证据无法对应交付提交 {len(history)} 张，仅提示（--json 查看）')
    pending = sum(item['status'] == '需处理' for item in report['checks'])
    lines.append(f'结论：需处理 {pending} 项' if pending else '结论：就绪')
    return '\n'.join(lines)


def pr_body(root, requirement, allow_stage=False):
    """由需求卡生成 PR 描述：默认仅完整交付；--allow-stage 且用户明确阶段交付时才生成阶段 PR。"""
    import teamflow as flow
    from requirement_model import delivery_blockers, accepted_human_ids
    card = parse_card(flow.requirement_path(root, requirement))
    summary, _ = requirement_summary(root, requirement)
    blockers = delivery_blockers(card)
    complete_ok = card['state'] == '完成' and not blockers
    if not complete_ok and not allow_stage:
        detail = '、'.join(item['id'] for item in blockers) if blockers else card['state_display']
        raise ValueError(
            '正式 PR 要求需求已完成且人工 AC 已用户确认或免除；当前：' + detail
            + '。用户明确阶段交付时加 --allow-stage')
    lines = ['## 范围', '', card['scope'], '']
    if card['excluded'] and card['excluded'] != '无':
        lines += ['## 不包含', '', card['excluded'], '']
    lines += ['## 验收条件', '']
    accepted = accepted_human_ids(card)
    waived = set(card['meta'].get('human_waived') or []) - stale_acceptance(card)
    lines += [f"- [{'x' if item['done'] else ' '}] {item['id']}：{item['condition']}"
              + ('（已免除人工验收）' if item['id'] in waived else
                 '（用户确认）' if item['id'] in accepted else '') for item in card['ac']]
    lines += ['', '## 验证', '']
    saved = card['evidence'] if isinstance(card['evidence'], dict) else {}
    if saved:
        lines.append(f"- {saved.get('profile') or '人工核对'}：{saved.get('status', '未知')}，证据{summary['evidence_status']}，"
                     f"HEAD {str(saved.get('head', ''))[:12]}，{saved.get('at', '')}")
    else:
        lines.append('- 未验证')
    if summary['pending_ac']:
        lines.append('- 未确认：' + '、'.join(item['id'] for item in summary['pending_ac']))
    if blockers and allow_stage:
        lines.append('- 阶段交付，待人工确认：' + '、'.join(item['id'] for item in blockers))
    lines += ['', 'Requirement: ' + requirement]
    title = card['title'] if complete_ok else '[阶段] ' + card['title']
    return {'requirement': requirement, 'title': title, 'body': '\n'.join(lines),
            'stage': not complete_ok}


def historical_coverage(root, saved, commit, config, candidates):
    """历史通过只覆盖仍与交付版本一致的检查输入；包括依赖变化与删除。"""
    import project_checks
    if not commit:
        return set()
    settings = config['profiles'][saved['profile']]
    groups = [[name] for name in saved['checks']] if saved.get('checks') else [None]
    covered = set()
    for group in groups:
        try:
            before = project_checks.source_snapshot(root, config, saved['profile'], commit=commit, checks=group, algorithm=saved.get('algorithm', 'sha256-files-v5'))
            after = project_checks.source_snapshot(root, config, saved['profile'], commit='HEAD', checks=group, algorithm=saved.get('algorithm', 'sha256-files-v5'))
        except (ValueError, KeyError, TypeError, subprocess.CalledProcessError):
            continue
        if before != after:
            continue
        scope = (project_checks.check_coverage(settings, group[0]) if group
                 else project_checks.coverage_inputs(settings))
        if scope != []:
            covered.update(project_checks.input_paths(root, scope, candidates))
    return covered


def ci_check(root, base):
    """CI 只读核对：本次范围内改动的完成卡，其证据必须对应当前内容或某个交付提交；
    非文档改动须由这些卡（或证据仍有效的阶段卡）的验证范围覆盖。不重跑项目检查。"""
    import teamflow as flow
    import project_checks
    checks = []
    try:
        config = project_checks.load_config(root)
        checks.append({'item': '验证配置', 'status': '就绪', 'detail': project_checks.CONFIG})
    except (ValueError, OSError, KeyError, TypeError) as error:
        config = None
        checks.append({'item': '验证配置', 'status': '需处理', 'detail': str(error)})
    changed = subprocess.run(['git', '-C', str(root), 'diff', '--name-only', '--no-renames', '-z', base + '...HEAD'],
                             capture_output=True, text=True)
    if changed.returncode:
        raise ValueError('无法比较 ' + base + '...HEAD；CI 需完整历史（fetch-depth: 0）：' + changed.stderr.strip())
    files = {name for name in changed.stdout.split('\0') if name}
    names = sorted(name for name in files
                   if name.startswith('requirements/REQ-') and name.endswith('.md') and (root / name).is_file())
    covered = set()
    for name in names:
        requirement = name[len('requirements/'):-3]
        card = parse_card(flow.requirement_path(root, requirement))
        summary, _ = requirement_summary(root, requirement)
        valid = summary['evidence_status'] == '有效' or summary['evidence_status'].startswith('交付时有效')
        if card['state'] != '完成':
            checks.append({'item': requirement, 'status': '提示',
                           'detail': card['state'] + '，阶段交付，不作为完整交付核对'})
        elif valid:
            checks.append({'item': requirement, 'status': '就绪', 'detail': summary['evidence_status']})
        else:
            checks.append({'item': requirement, 'status': '需处理', 'detail': summary})
        saved = card['evidence'] if isinstance(card['evidence'], dict) else {}
        if valid and saved.get('kind') == 'manual':
            covered.update(project_checks.input_paths(root, saved['paths'], files))
        elif valid and config and saved.get('profile') in config['profiles']:
            evidence_config = config
            if summary['evidence_status'].startswith('交付时有效'):
                commit = flow.delivered_commit(root, card)
                if commit:
                    shown = subprocess.check_output(
                        ['git', '-C', str(root), 'show', commit + ':' + project_checks.CONFIG], text=True)
                    historical = json.loads(shown)
                    evidence_config = {'profiles': {name: project_checks.resolve_profile(
                        historical['profiles'], name) for name in historical['profiles']}}
            inputs = project_checks.evidence_inputs(root, saved, config=evidence_config)
            if inputs != []:
                candidates = project_checks.input_paths(root, inputs, files)
                if summary['evidence_status'].startswith('交付时有效'):
                    candidates = historical_coverage(root, saved, commit, evidence_config, candidates)
                covered.update(candidates)
            if summary['evidence_status'] == '有效':
                covered.add(project_checks.CONFIG)
    if not names:
        checks.append({'item': '需求卡', 'status': '提示', 'detail': base + ' 之后未改动需求卡'})
    rest = {name for name in files - covered if not name.startswith('logs/')}
    code = project_checks.non_document_paths(root, rest)
    if code:
        # 只有代码、没有完成卡的 PR 不能借“未改动需求卡”通过核对。
        checks.append({'item': '未覆盖改动', 'status': '需处理',
                       'detail': '以下非文档改动没有本 PR 需求卡的有效证据覆盖：' + '、'.join(code[:10])
                       + (f' 等 {len(code)} 个' if len(code) > 10 else '')})
    documents = sorted(name for name in rest - set(code) if not name.startswith('requirements/')
                       and name not in project_checks.installed_files(root))
    if documents:
        checks.append({'item': '文档改动', 'status': '提示',
                       'detail': '无需求卡覆盖的文档改动（轻量改动）：' + '、'.join(documents[:10])})
    return {'base': base, 'checks': checks, 'needs_action': any(item['status'] == '需处理' for item in checks)}
