#!/usr/bin/env python3
"""设计变量检查：字体、圆角、颜色、间距只能在设计变量模块中写字面量，模块外引用模块中的语义值。

配置默认读取 .agents/design-tokens.json，说明见 references/DESIGN-TOKENS.md。基于逐行正则扫描，
不解析 Swift/OC 语法；存量违规写入基线放行，新增违规退出 1。
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

NUMBER = r'(?P<n>-?\d+(?:\.\d+)?)'
# 每条为 (正则, 是否放行取值 0)；含命名组 n 的模式在取值为 0 时放行。
BUILTIN = {
    'font': [
        (r'\.system\(\s*size\s*:\s*\d', False),
        (r'\bFont\.custom\(|\.custom\(\s*"', False),
        (r'\b(?:systemFont|boldSystemFont|italicSystemFont|monospacedSystemFont|monospacedDigitSystemFont)\(\s*ofSize\s*:\s*\d', False),
        (r'\bUIFont\(\s*name\s*:', False),
        (r'\[UIFont\s+\w*[sS]ystemFontOfSize\s*:\s*\d|\[UIFont\s+fontWithName\s*:', False),
    ],
    'corner-radius': [
        (r'[cC]ornerRadius\s*[:=(]\s*' + NUMBER, True),
        (r'setCornerRadius\s*:\s*' + NUMBER, True),
    ],
    'color': [
        (r'\b(?:Color|UIColor|NSColor)\(\s*(?:red|white|hue|displayP3Red)\s*:', False),
        (r'\bcolorWith(?:Red|White|Hue|DisplayP3Red)\s*:', False),
        (r'\bColor\(\s*hex\s*:|\bUIColor\(\s*hex\s*:', False),
    ],
    'spacing': [
        (r'\.padding\(\s*(?:\.\w+\s*,\s*)?' + NUMBER, True),
        (r'\bspacing\s*:\s*' + NUMBER, True),
    ],
}
EXTENSIONS = ('.swift', '.m', '.mm', '.h')


def fail(message):
    print('设计变量检查：' + message, file=sys.stderr)
    sys.exit(2)


def load(root, config_path):
    path = root / config_path
    if not path.is_file():
        fail(f'缺少配置 {config_path}，见 DESIGN-TOKENS.md')
    try:
        config = json.loads(path.read_text(encoding='utf-8'))
    except ValueError as error:
        fail(f'配置不是有效 JSON：{error}')
    for field in ('sources', 'modules'):
        if not isinstance(config.get(field), list) or not config[field]:
            fail(f'{field} 必须为非空路径列表')
    names = config.get('rules', list(BUILTIN))
    unknown = [name for name in names if name not in BUILTIN]
    if unknown:
        fail('未知规则：' + '、'.join(unknown) + '；可选 ' + '、'.join(BUILTIN))
    rules = {name: [(re.compile(p), zero) for p, zero in BUILTIN[name]] for name in names}
    for name, pattern in config.get('custom_rules', {}).items():
        try:
            rules[name] = [(re.compile(pattern), False)]
        except re.error as error:
            fail(f'自定义规则 {name} 正则无效：{error}')
    if not rules:
        fail('未启用任何规则')
    return config, rules


def inside(relative, paths):
    return any(relative == p or relative.startswith(p.rstrip('/') + '/') for p in paths)


def violations(root, config, rules):
    modules = [str(Path(p).as_posix()) for p in config['modules']]
    extensions = tuple(config.get('extensions', EXTENSIONS))
    found, scanned = [], 0
    for source in config['sources']:
        base = root / source
        if not base.exists():
            fail('扫描路径不存在：' + source)
        files = [base] if base.is_file() else sorted(base.rglob('*'))
        for path in files:
            if not path.is_file() or path.suffix not in extensions:
                continue
            relative = path.relative_to(root).as_posix()
            if inside(relative, modules):
                continue
            scanned += 1
            for number, line in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
                text = line.strip()
                if text.startswith(('//', '/*', '*')):
                    continue
                code = text.split('//', 1)[0]
                for name, patterns in rules.items():
                    if any(hit(pattern, zero, code) for pattern, zero in patterns):
                        found.append({'path': relative, 'line': number, 'rule': name, 'text': text})
    if not scanned:
        fail('未扫描到任何源文件，核对 sources、modules 与 extensions')
    return found, scanned


def hit(pattern, zero_ok, code):
    for match in pattern.finditer(code):
        value = match.groupdict().get('n')
        if zero_ok and value is not None and float(value) == 0:
            continue
        return True
    return False


def key(item):
    return item['path'], item['rule'], item['text']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', default='.')
    parser.add_argument('--config', default='.agents/design-tokens.json')
    parser.add_argument('--update-baseline', action='store_true', help='把当前全部违规写入基线后退出')
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    config, rules = load(root, args.config)
    found, scanned = violations(root, config, rules)
    baseline_path = config.get('baseline')
    if args.update_baseline:
        if not baseline_path:
            fail('配置未设置 baseline')
        entries = [{'path': p, 'rule': r, 'text': t} for p, r, t in sorted(key(i) for i in found)]
        (root / baseline_path).write_text(json.dumps({'version': 1, 'entries': entries}, ensure_ascii=False, indent=2) + '\n',
                                          encoding='utf-8')
        print(f'设计变量检查：已写入基线 {len(entries)} 条（{baseline_path}）')
        return 0
    allowed = Counter()
    if baseline_path and (root / baseline_path).is_file():
        try:
            allowed.update(key(e) for e in json.loads((root / baseline_path).read_text(encoding='utf-8'))['entries'])
        except (ValueError, KeyError, TypeError) as error:
            fail(f'基线无效：{error}')
    new = []
    for item in found:
        if allowed[key(item)] > 0:
            allowed[key(item)] -= 1
        else:
            new.append(item)
    for item in new:
        print(f"{item['path']}:{item['line']}: [{item['rule']}] {item['text']}")
    stale = sum(allowed.values())
    summary = f'扫描 {scanned} 个文件，新增违规 {len(new)}，基线放行 {len(found) - len(new)}'
    if stale:
        summary += f'，基线中 {stale} 条已不存在（可用 --update-baseline 清理）'
    print('设计变量检查：' + ('失败，' if new else '通过，') + summary)
    if new:
        print('改为引用设计变量模块（' + '、'.join(config['modules']) + '）中的语义值；缺少时先在模块中新增')
    return 1 if new else 0


if __name__ == '__main__':
    sys.exit(main())
