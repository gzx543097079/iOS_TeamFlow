#!/usr/bin/env python3
"""验证分发入口、版本与内部 Markdown 链接。仅检查通用分发文件。"""
import re
from pathlib import Path
from package_release import FILES, SKILL


def validate(root):
    errors = []
    for name in FILES:
        path = root / name
        if not path.is_file():
            errors.append('缺文件：' + name)
            continue
        if path.suffix == '.md':
            for link in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                if '://' in link or link.startswith('#'):
                    continue
                target = link.split('#')[0]
                if not (path.parent / target).exists():
                    errors.append(f'{name} 的链接不存在：{target}')
    skill = root / '.agents/skills/ios-team-flow/SKILL.md'
    if skill.exists() and not re.match(r'---\nname: ios-team-flow\ndescription: [^\n]+\n---\n', skill.read_text()):
        errors.append('Skill 元数据不完整')
    if len((root / 'AGENTS.md').read_bytes()) >= 32768:
        errors.append('AGENTS.md 超出默认 32 KiB 预算')
    if not re.fullmatch(r'\d+\.\d+\.\d+', (root / SKILL / 'references/VERSION').read_text().strip()):
        errors.append('版本格式错误')
    if errors:
        raise ValueError('\n'.join(errors))
    print('工作流入口、版本、文件清单和内部链接检查通过')


if __name__ == '__main__':
    validate(Path(__file__).resolve().parents[1])
