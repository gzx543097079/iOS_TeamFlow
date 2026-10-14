"""只读诊断和需求状态摘要，不写第二套状态或执行项目检查。"""
import subprocess
from teamflow_common import local_path
from requirement_model import require_ready, parse_card


def requirement_summary(root, requirement):
    """返回证据有效性、问题与下一步，以及是否为已交付但证据无法对应交付提交的历史需求。"""
    import teamflow as flow
    card = parse_card(flow.requirement_path(root, requirement))
    problems = []
    try:
        require_ready(card)
    except ValueError as error:
        problems.append(str(error))
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
    elif pending:
        next_step = '实际核对剩余 AC，使用 --confirm-ac 确认；证据有效时无需重跑'
    elif card['state'] == '完成':
        next_step = '需求已完成；仅执行用户明确授权的交付目标'
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
    try:
        config = project_checks.load_config(root)
        if not config['profiles']:
            raise ValueError('未配置任何验证 profile')
        for profile in config['profiles']:
            project_checks.source_snapshot(root, config, profile)
        checks.append({'item': '验证配置及输入', 'status': '就绪', 'detail': list(config['profiles'])})
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        checks.append({'item': '验证配置及输入', 'status': '需处理', 'detail': str(error)})
    directory = local_path(root, 'requirements')
    if directory.exists():
        for path in sorted(directory.glob('REQ-*.md')):
            try:
                local_path(root, str(path.relative_to(root)))
                summary, finished = requirement_summary(root, path.stem)
                status = '就绪' if not summary['problems'] else '历史' if finished else '需处理'
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
        else:
            lines.append(f"[{item['status']}] {item['item']}：{_brief(item)}")
    if ready:
        lines.append(f'[就绪] 需求：{len(ready)} 张')
    if history:
        lines.append(f'[历史] 已交付需求证据无法对应交付提交 {len(history)} 张，仅提示（--json 查看）')
    pending = sum(item['status'] == '需处理' for item in report['checks'])
    lines.append(f'结论：需处理 {pending} 项' if pending else '结论：就绪')
    return '\n'.join(lines)


def pr_body(root, requirement):
    """由需求卡生成 PR 描述：范围、AC 进度与证据摘要只取卡片现有内容，不另写状态。"""
    import teamflow as flow
    card = parse_card(flow.requirement_path(root, requirement))
    summary, _ = requirement_summary(root, requirement)
    lines = ['## 范围', '', card['scope'], '']
    if card['excluded'] and card['excluded'] != '无':
        lines += ['## 不包含', '', card['excluded'], '']
    lines += ['## 验收条件', '']
    lines += [f"- [{'x' if item['done'] else ' '}] {item['id']}：{item['condition']}" for item in card['ac']]
    lines += ['', '## 验证', '']
    saved = card['evidence'] if isinstance(card['evidence'], dict) else {}
    if saved:
        lines.append(f"- {saved.get('profile') or '人工核对'}：{saved.get('status', '未知')}，证据{summary['evidence_status']}，"
                     f"HEAD {str(saved.get('head', ''))[:12]}，{saved.get('at', '')}")
    else:
        lines.append('- 未验证')
    if summary['pending_ac']:
        lines.append('- 未确认：' + '、'.join(item['id'] for item in summary['pending_ac']))
    lines += ['', 'Requirement: ' + requirement]
    return {'requirement': requirement, 'title': card['title'], 'body': '\n'.join(lines)}


def ci_check(root, base):
    """CI 只读核对：本次范围内改动的完成卡，其证据必须对应当前内容或某个交付提交；不重跑项目检查。"""
    import teamflow as flow
    import project_checks
    checks = []
    try:
        project_checks.load_config(root)
        checks.append({'item': '验证配置', 'status': '就绪', 'detail': project_checks.CONFIG})
    except (ValueError, OSError, KeyError, TypeError) as error:
        checks.append({'item': '验证配置', 'status': '需处理', 'detail': str(error)})
    changed = subprocess.run(['git', '-C', str(root), 'diff', '--name-only', base + '...HEAD', '--', 'requirements'],
                             capture_output=True, text=True)
    if changed.returncode:
        raise ValueError('无法比较 ' + base + '...HEAD；CI 需完整历史（fetch-depth: 0）：' + changed.stderr.strip())
    names = sorted(name for name in changed.stdout.split()
                   if name.startswith('requirements/REQ-') and name.endswith('.md') and (root / name).is_file())
    for name in names:
        requirement = name[len('requirements/'):-3]
        card = parse_card(flow.requirement_path(root, requirement))
        summary, _ = requirement_summary(root, requirement)
        if card['state'] != '完成':
            checks.append({'item': requirement, 'status': '提示', 'detail': card['state'] + '，不作为交付核对'})
        elif summary['evidence_status'] == '有效' or summary['evidence_status'].startswith('交付时有效'):
            checks.append({'item': requirement, 'status': '就绪', 'detail': summary['evidence_status']})
        else:
            checks.append({'item': requirement, 'status': '需处理', 'detail': summary})
    if not names:
        checks.append({'item': '需求卡', 'status': '提示', 'detail': base + ' 之后未改动需求卡'})
    return {'base': base, 'checks': checks, 'needs_action': any(item['status'] == '需处理' for item in checks)}
