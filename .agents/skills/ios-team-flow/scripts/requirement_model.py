"""需求卡的唯一解析规则，以及用于验证的稳定语义。"""
import json
import re

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

def field_pattern(name):
    return r'^[ \t]*-[ \t]+' + re.escape(name) + r'：[ \t]*(.+?)[ \t]*$'


def field(text, name):
    values = re.findall(field_pattern(name), text, re.M)
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


def parse_requirement(text, requirement):
    if MARKER not in text:
        raise ValueError('只支持 vNext 需求卡：' + requirement)
    if not ID.fullmatch(requirement):
        raise ValueError('需求文件名格式无效：' + requirement)
    state = parse_state(field(text, '状态'))
    scope = field(text, '范围')
    excluded = field(text, '不包含') if re.search(field_pattern('不包含'), text, re.M) else ''
    if scope in ('待填写', '—') or excluded in ('待填写', '—'):
        raise ValueError('范围和不包含必须填写实际内容')
    ac = []
    for line in text.splitlines():
        match = re.match(r'^[ \t]*-[ \t]+(⚪|✅)[ \t]+(AC-\d+)：[ \t]*(.+?)[ \t]*$', line)
        if match and match.group(3).strip():
            ac.append({'id': match.group(2), 'done': match.group(1) == '✅',
                       'condition': match.group(3).strip()})
    if not ac or len({item['id'] for item in ac}) != len(ac):
        raise ValueError('需求卡必须包含不重复的 AC 项')
    done = sum(item['done'] for item in ac)
    return {'requirement': requirement, 'state': state, 'state_display': state_display(state),
            'progress': {'done': done, 'total': len(ac),
                         'display': progress_display(done, len(ac))},
            'scope': scope, 'excluded': excluded, 'ac': ac, 'text': text}


def parse_card(path):
    return parse_requirement(path.read_text(), path.stem)


def require_ready(card):
    """草稿可以列出，但占位内容不能进入验收。"""
    values = [card['scope'], card['excluded']] + [item['condition'] for item in card['ac']]
    if any('待填写' in value or '填写可观察的输入、操作和预期结果' in value
           or '〈' in value for value in values):
        raise ValueError('需求仍含占位内容，请填写实际范围和 AC 后验收')


def semantic_content(text, requirement):
    card = parse_requirement(text, requirement)
    payload = {key: card[key] for key in ('scope', 'excluded')}
    payload['ac'] = sorted([{'id': item['id'], 'condition': item['condition']}
                            for item in card['ac']], key=lambda item: item['id'])
    return json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')
