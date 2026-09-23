#!/usr/bin/env python3
"""验证分发入口、版本与内部 Markdown 链接。仅检查通用分发文件。"""
import re
import json
from pathlib import Path
from package_release import FILES, SKILL


def validate_profile_overlap(config):
    profiles = config['profiles']
    base = profiles['workflow']
    release = profiles['workflow-release']
    if base.get('inputs') != release.get('inputs') or any(
            release['checks'].get(name) != check for name, check in base['checks'].items()):
        raise ValueError('workflow-release 必须保留 workflow 的相同输入和检查')


def validate(root):
    errors = []
    config = root / '.agents/project-checks.json'
    if config.is_file():
        validate_profile_overlap(json.loads(config.read_text()))
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
                # 需求模板直接落地到 requirements/，链接按使用位置校验。
                parent = root / 'requirements' if name.endswith('/templates/requirement.md') else path.parent
                if not (parent / target).resolve().exists():
                    errors.append(f'{name} 的链接不存在：{target}')
    skill = root / '.agents/skills/ios-team-flow/SKILL.md'
    if skill.exists() and not re.match(r'---\nname: ios-team-flow\ndescription: [^\n]+\n---\n', skill.read_text()):
        errors.append('Skill 元数据不完整')
    if len((root / 'AGENTS.md').read_bytes()) >= 32768:
        errors.append('AGENTS.md 超出默认 32 KiB 预算')
    if not re.fullmatch(r'\d+\.\d+\.\d+', (root / SKILL / 'references/VERSION').read_text().strip()):
        errors.append('版本格式错误')
    version = (root / SKILL / 'references/VERSION').read_text().strip()
    readme = (root / 'README.md').read_text()
    if '当前版本为 **' + version + '**' not in readme:
        errors.append('README 当前版本与 VERSION 不一致')
    if errors:
        raise ValueError('\n'.join(errors))
    print('工作流入口、版本、文件清单和内部链接检查通过')


if __name__ == '__main__':
    validate(Path(__file__).resolve().parents[1])
