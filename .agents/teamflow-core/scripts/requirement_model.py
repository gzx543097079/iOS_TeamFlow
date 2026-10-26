"""需求卡的唯一解析规则，以及用于验证的稳定语义。

卡片 = 头部元数据（工具读写）+ Markdown 正文（人和 Agent 自由编辑）。
元数据只支持 `键: 值` 与一层缩进的子对象；以 [ { " 开头的值按 JSON 解析。
"""
import hashlib
import json
import re

ID = re.compile(r'REQ-(\d{8})-([0-9a-f]{4})')
STATE_ICONS = {
    '进行中': '🔵',
    '待用户验证': '🟣',
    '阻塞': '🔴',
    '完成': '✅',
    '取消': '⚫',
}
STATES = tuple(STATE_ICONS)
BLOCK_KINDS = ('待确认', '外部', '暂停')
TYPES = ('feature', 'bug')
AC_LINE = re.compile(r'^[ \t]*[-*][ \t]+\[([ xX])\][ \t]+(AC-\d+)[ \t]*[：:][ \t]*(.+?)[ \t]*$')
PLACEHOLDER = re.compile(r'〈[^〉]*〉')


def _scalar(value):
    value = value.strip()
    if value[:1] in ('[', '{', '"'):
        return json.loads(value)
    if value in ('true', 'false'):
        return value == 'true'
    return value


def _dump_scalar(value):
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, str) and value and value == value.strip() and value[0] not in '[{"' \
            and value not in ('true', 'false') and '\n' not in value:
        return value
    return json.dumps(value, ensure_ascii=False)


def split_card(text):
    """拆出头部元数据和正文；格式错误给出明确位置。"""
    lines = text.split('\n')
    if not lines or lines[0].strip() != '---':
        raise ValueError('需求卡缺少头部元数据（首行应为 ---）')
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == '---')
    except StopIteration:
        raise ValueError('需求卡头部元数据未闭合（缺少第二个 ---）') from None
    meta, parent = {}, None
    for number, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        match = re.fullmatch(r'( *)([A-Za-z_][A-Za-z0-9_-]*):(.*)', line)
        if not match:
            raise ValueError(f'需求卡头部第 {number} 行格式无效：{line.strip()}')
        indent, key, value = match.groups()
        try:
            if indent:
                if parent is None:
                    raise ValueError(f'需求卡头部第 {number} 行缩进无上级字段')
                meta[parent][key] = _scalar(value)
            elif value.strip():
                meta[key], parent = _scalar(value), None
            else:
                meta[key], parent = {}, key
        except json.JSONDecodeError as error:
            raise ValueError(f'需求卡头部第 {number} 行值无效：{error}') from None
    return meta, '\n'.join(lines[end + 1:])


def dump_card(meta, body):
    lines = ['---']
    for key, value in meta.items():
        if value is None or value == {}:
            continue
        if isinstance(value, dict):
            lines.append(key + ':')
            lines.extend(f'  {sub}: {_dump_scalar(item)}' for sub, item in value.items() if item is not None)
        else:
            lines.append(f'{key}: {_dump_scalar(value)}')
    lines.append('---')
    return '\n'.join(lines) + '\n\n' + body.lstrip('\n')


def sections(body):
    """按二级标题切分正文，标题文字为键。"""
    result, current = {}, None
    for line in body.split('\n'):
        heading = re.match(r'^##[ \t]+(.+?)[ \t]*$', line)
        if heading:
            current = heading.group(1)
            result[current] = []
        elif current is not None:
            result[current].append(line)
    return {name: '\n'.join(lines) for name, lines in result.items()}


def normalize(text):
    """排版不进入语义：合并全部空白。"""
    return ' '.join(text.split())


def state_display(state):
    return STATE_ICONS[state] + ' ' + state


def progress_display(done, total):
    icon = '✅' if done == total else ('🔵' if done else '⚪')
    return f'{icon} {done}/{total}'


def parse_requirement(text, requirement):
    if not ID.fullmatch(requirement):
        raise ValueError('需求编号格式应为 REQ-YYYYMMDD-xxxx：' + requirement)
    meta, body = split_card(text)
    if meta.get('id') != requirement:
        raise ValueError('需求卡头部 id 与文件名不一致：' + requirement)
    state = meta.get('state')
    if state not in STATES:
        raise ValueError('需求状态无效：' + str(state) + '；可选 ' + '、'.join(STATES))
    if state == '阻塞' and meta.get('blocked') not in BLOCK_KINDS:
        raise ValueError('阻塞状态必须填写 blocked：' + '/'.join(BLOCK_KINDS))
    parts = sections(body)
    if '范围' not in parts or not normalize(parts['范围']):
        raise ValueError('需求卡必须填写“## 范围”')
    ac = []
    for line in parts.get('验收条件', '').split('\n'):
        match = AC_LINE.match(line)
        if match:
            ac.append({'id': match.group(2), 'done': match.group(1) != ' ',
                       'condition': normalize(match.group(3))})
    if not ac or len({item['id'] for item in ac}) != len(ac):
        raise ValueError('“## 验收条件”必须包含不重复的 `- [ ] AC-01：条件` 项')
    title = next((line[2:].strip() for line in body.split('\n') if line.startswith('# ')), requirement)
    done = sum(item['done'] for item in ac)
    display = state_display(state) + ('（排队）' if meta.get('queued') else '') + \
        (f"（{meta['blocked']}）" if state == '阻塞' else '')
    return {'requirement': requirement, 'title': title, 'type': meta.get('type', 'feature'),
            'state': state, 'state_display': display, 'queued': bool(meta.get('queued')),
            'blocked': meta.get('blocked'), 'reason': meta.get('reason'),
            'progress': {'done': done, 'total': len(ac), 'display': progress_display(done, len(ac))},
            'scope': normalize(parts['范围']), 'excluded': normalize(parts.get('不包含', '')),
            'ac': ac, 'evidence': meta.get('evidence') or None, 'meta': meta, 'body': body, 'text': text}


def acceptance_fingerprints(card):
    """确认绑定范围与该条 AC；排版变化不使确认失效。"""
    return {item['id']: hashlib.sha256(json.dumps(
        [card['scope'], card['excluded'], item['condition']], ensure_ascii=False).encode()).hexdigest()
        for item in card['ac']}


def stale_acceptance(card):
    saved = card['meta'].get('confirmed_ac')
    current = acceptance_fingerprints(card)
    if isinstance(saved, dict):
        return {item['id'] for item in card['ac'] if item['done'] and saved.get(item['id']) != current[item['id']]}
    # 旧卡无逐条确认指纹：语义未变化可沿用，变化时保守取消全部旧确认。
    proof = card['evidence'] or {}
    semantic = 'sha256:' + hashlib.sha256(semantic_content(card['text'], card['requirement'])).hexdigest()
    return {item['id'] for item in card['ac'] if item['done']} if proof and proof.get('requirement') != semantic else set()


# 人工/视觉类 AC：条件含这些词时，完整交付须 user_confirmed 或 human_waived。
HUMAN_AC = re.compile(
    r'视觉|真机|截图|观感|界面效果|布局|间距|对齐|字号|颜色|预览|人工验收|肉眼|用户可见')


def human_required_acs(card):
    """须用户确认或明确免除的 AC（按条件关键词识别）。"""
    return [item for item in card['ac'] if HUMAN_AC.search(item['condition'] or '')]


def accepted_human_ids(card):
    stale = stale_acceptance(card)
    users = set(card['meta'].get('user_confirmed') or []) - stale
    waived = set(card['meta'].get('human_waived') or []) - stale
    return users | waived


def delivery_blockers(card):
    """阻止完整交付（完成态提交 / 正式 PR）的人工项；进行中阶段提交不使用本列表。"""
    allowed = accepted_human_ids(card)
    if card['state'] == '待用户验证':
        return [item for item in card['ac'] if not item['done']]
    blockers = []
    for item in human_required_acs(card):
        if not item['done'] or item['id'] not in allowed:
            blockers.append(item)
    return blockers


def handover_checklist(requirement, pending_conditions):
    """待用户确认时的固定交接表（Markdown）。"""
    if not pending_conditions:
        return ''
    lines = ['## 待用户确认', '', '| 编号 | 条件 |', '| --- | --- |']
    lines.extend(f"| {item['id']} | {item['condition']} |" for item in pending_conditions)
    lines.append('')
    lines.extend(f"- [ ] {item['id']}：{item['condition']}" for item in pending_conditions)
    lines += ['', f'确认后执行：`python3 scripts/teamflow.py req complete {requirement} --user-confirmed AC-编号`',
              '（可重复传入多个编号；用户明确免除人工验收时用 `--waive-human AC-编号` 并配合 `--confirm-ac`）']
    return '\n'.join(lines)


def parse_card(path):
    return parse_requirement(path.read_text(), path.stem)


def require_ready(card):
    """草稿可以列出，但占位内容不能进入验收。"""
    values = [card['scope'], card['excluded']] + [item['condition'] for item in card['ac']]
    if any(PLACEHOLDER.search(value) for value in values):
        raise ValueError('需求仍含〈占位〉内容，请填写实际范围和 AC 后验收')


def semantic_content(text, requirement):
    card = parse_requirement(text, requirement)
    payload = {key: card[key] for key in ('scope', 'excluded')}
    payload['ac'] = sorted([{'id': item['id'], 'condition': item['condition']}
                            for item in card['ac']], key=lambda item: item['id'])
    return json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')
