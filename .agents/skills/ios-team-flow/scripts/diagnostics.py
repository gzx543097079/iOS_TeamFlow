"""只读诊断和需求恢复摘要，不写第二套状态或执行项目检查。"""
import contextlib
import io
import json
import subprocess
from teamflow_common import local_path
from requirement_model import require_ready, parse_card, field


def resume(root, requirement):
    return _resume(root, requirement)[0]


def _resume(root, requirement):
    """返回恢复摘要及是否仅为已完成需求的证据失效。"""
    import teamflow as flow
    card = parse_card(flow.requirement_path(root, requirement))
    problems = []
    try:
        require_ready(card)
    except ValueError as error:
        problems.append(str(error))
    content_ready = not problems
    try:
        flow.validation_proof(root, card)
        evidence = '有效'
    except (ValueError, OSError, KeyError, TypeError) as error:
        evidence = '缺失或失效'
        problems.append(str(error))
    pending = [item for item in card['ac'] if not item['done']]
    if card['state'] in ('暂停', '取消'):
        next_step = '等待用户明确恢复；不得自动继续'
    elif card['state'] in ('待确认', '阻塞'):
        next_step = '核对决策与异常中的原因，解除条件后恢复'
    elif problems:
        next_step = '补齐实际需求内容或重新核对失效证据'
    elif pending:
        next_step = '实际核对剩余 AC，使用 --confirm-ac 确认；证据有效时无需重跑'
    elif card['state'] == '完成':
        next_step = '需求已完成；仅执行用户明确授权的交付目标'
    else:
        next_step = '复用有效证据执行 req complete'
    decisions = card['text'].split('## 决策与异常', 1)
    summary = {'requirement': requirement, 'state': card['state_display'],
               'pending_ac': pending, 'evidence_status': evidence, 'problems': problems,
               'decisions': decisions[1].strip() if len(decisions) == 2 else '', 'next_step': next_step}
    # 完成后代码继续演进，旧证据失效属于正常历史状态，不要求重开或补测。
    return summary, card['state'] == '完成' and content_ready and not pending


def doctor(root):
    import setup_project
    import project_checks
    import module_context
    checks = []
    with contextlib.redirect_stdout(io.StringIO()):
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
                summary, finished = _resume(root, path.stem)
                status = '就绪' if not summary['problems'] else '历史' if finished else '需处理'
                checks.append({'item': path.stem, 'status': status, 'detail': summary})
            except (ValueError, OSError, KeyError, TypeError) as error:
                checks.append({'item': path.name, 'status': '需处理', 'detail': str(error)})
    try:
        manifest = local_path(root, str(module_context.MANIFEST))
        if manifest.exists():
            data = module_context.load_manifest(root)
            summary = module_context.inspect(root, data, all_modules=True)
            problem = summary['expand_scope'] or any(m['status'] != 'unchanged' for m in summary['modules'])
            checks.append({'item': '模块索引', 'status': '需处理' if problem else '就绪', 'detail': summary})
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        checks.append({'item': '模块索引', 'status': '需处理', 'detail': str(error)})
    return {'checks': checks, 'needs_action': any(item['status'] == '需处理' for item in checks)}


def _brief(item):
    detail = item['detail']
    if isinstance(detail, list):
        return '、'.join(map(str, detail))
    if isinstance(detail, dict) and 'requirement' in detail:
        return '；'.join(detail['problems']) + '（req resume ' + detail['requirement'] + ' 查看）'
    if isinstance(detail, dict) and 'modules' in detail:
        counts = {}
        for module in detail['modules']:
            counts[module['status']] = counts.get(module['status'], 0) + 1
        return '，'.join(f'{name} {count}' for name, count in sorted(counts.items())) + '（--json 查看）'
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
        lines.append(f'[历史] 已完成需求证据失效 {len(history)} 张，仅提示：' + '、'.join(history))
    pending = sum(item['status'] == '需处理' for item in report['checks'])
    lines.append(f'结论：需处理 {pending} 项' if pending else '结论：就绪')
    return '\n'.join(lines)
