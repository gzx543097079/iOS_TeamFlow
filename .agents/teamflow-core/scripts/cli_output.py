"""命令结果呈现；不读取或改变项目状态。"""

# ---- 默认简短输出；--json 输出完整结构 ----

def _evidence_line(evidence):
    if not evidence:
        return '证据：未绑定'
    if evidence.get('kind') == 'manual':
        return f"证据：人工核对 @ {evidence.get('at', '')}"
    return f"证据：{evidence.get('profile')} {evidence.get('status')} @ {evidence.get('at', '')}"


def _pending_lines(requirement, pending, waiting=False):
    if not pending:
        return []
    hint = (f'用户明确确认后执行：req complete {requirement} --user-confirmed AC-编号' if waiting
            else f'核对后执行：req complete {requirement} --confirm-ac AC-编号（证据有效时无需重跑）')
    return ['剩余：' + '；'.join(f"{p['id']} {p['condition']}" for p in pending), hint]


def render(kind, data):
    if kind == 'create':
        return f"已创建 {data['requirement']}（{data['state']}）：{data['card']}"
    if kind == 'state':
        return f"{data['requirement']} → {data['state']}"
    if kind == 'list':
        rows, skipped, *hidden = data
        lines = ['| 需求 | 标题 | 状态 | 进度 |', '| --- | --- | --- | --- |']
        lines.extend(f"| [{r['requirement']}](requirements/{r['requirement']}.md) | {r['title']} | "
                     f"{r['state']} | {r['progress']['display']} |" for r in rows)
        lines.extend(f"已跳过异常需求卡 {s['requirement']}：{s['error']}" for s in skipped)
        if hidden and hidden[0]:
            lines.append(f'另有已完成或取消 {hidden[0]} 张（--all 查看）')
        return '\n'.join(lines)
    if kind == 'status':
        pending = [item for item in data['ac'] if not item['done']]
        lines = [f"{data['requirement']} {data['title']}",
                 f"{data['state']} {data['progress']['display']}",
                 _evidence_line(data['evidence']) + (f"（{data['evidence_status']}）" if data['evidence'] else '')]
        if data['reason']:
            lines.append('原因：' + data['reason'])
        lines.extend('问题：' + problem for problem in data['problems'])
        lines.extend(_pending_lines(data['requirement'], pending, data['state_key'] == '待用户验证')[:1])
        return '\n'.join(lines + ['下一步：' + data['next_step']])
    if kind == 'complete':
        lines = [data['verification']] if data['verification'] else []
        lines.append(f"{data['requirement']} {data['state']} {data['progress']}")
        if data.get('handover'):
            lines.extend(['', data['handover']])
        else:
            lines.extend(_pending_lines(data['requirement'], data['pending_conditions'],
                                        data['state_key'] == '待用户验证'))
        return '\n'.join(lines)
    if kind == 'git':
        proof = data['validation']
        if proof['kind'] == 'document':
            return f"提交检查：通过（{len(data['staged_files'])} 个暂存文件均为文档，轻量改动无需需求证据；未运行测试）"
        source = proof['profile'] if proof['kind'] == 'result' else '人工核对'
        lines = [f"提交检查：通过（{len(data['staged_files'])} 个暂存文件，证据：{source}；未运行测试）",
                 '提交尾注：' + data['commit_trailer']]
        if data['release_sensitive_files']:
            lines.append('发布敏感文件：' + '、'.join(data['release_sensitive_files']))
        if data.get('unverified_profiles'):
            lines.append('验证配置中以下 profile 的命令或范围有变化，未经本次证据执行，请人工核对：'
                         + '、'.join(data['unverified_profiles']))
        return '\n'.join(lines)
    if kind == 'suggest':
        total = len(data['changed_files'])
        lines = [f'改动文件：{total} 个' + (f"，建议 {data['recommended']}" if data['recommended'] else '')]
        for p in data['profiles']:
            line = f"{p['profile']}：覆盖 {len(p['covered_files'])}/{total}"
            if p.get('manual'):
                line += '（仅显式执行）'
            elif p['covers_all_changes']:
                line += '（全部）'
            if 'selected' in p:
                line += '；触发：' + ('、'.join(p['selected']) or '无')
                if p.get('skipped'):
                    line += '；未触发：' + '、'.join(p['skipped'])
            if p.get('last_pass'):
                line += f"；上次通过 {p['last_pass']['wall_seconds']:g} 秒"
                if p['last_pass'].get('reused'):
                    line += '（含复用）'
                if p['last_pass'].get('partial'):
                    line += '（部分检查）'
            lines.append(line)
        if data.get('ambiguous_profiles'):
            lines.append('优先级相同，请指定 profile 或配置 priority：' + '、'.join(data['ambiguous_profiles']))
        if data['uncovered_files']:
            shown = data['uncovered_files'][:5]
            more = len(data['uncovered_files']) - len(shown)
            lines.append('无 profile 覆盖：' + '、'.join(shown) + (f' 等 {len(data["uncovered_files"])} 个' if more else ''))
        lines.append('仅按路径建议，不代表测试充分')
        return '\n'.join(lines)
    if kind == 'module':
        lines = [f"基线 {data['base']}（{data['merge_base'][:12]}）" +
                 ('，需扩大检查范围' if data['expand_scope'] else '')]
        if data['route_problem']:
            lines.append('路由：' + data['route_problem'])
        for module in data['modules']:
            line = f"{module['name']} {module['status']}"
            if module['problems']:
                line += '：' + '；'.join(module['problems'])
            elif module['suggested_read_files']:
                files = module['suggested_read_files']
                line += '，先读 ' + '、'.join(files[:5]) + (f' 等 {len(files)} 个' if len(files) > 5 else '')
            lines.append(line)
        return '\n'.join(lines)
    raise ValueError(kind)

