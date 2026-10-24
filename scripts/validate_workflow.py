#!/usr/bin/env python3
"""验证分发入口、版本与内部 Markdown 链接。仅检查通用分发文件与需求记录。"""
import re
import json
from pathlib import Path
from package_release import FILES, SKILL, GODOT_SKILL, CORE

MODE_SKILLS = {'ios': (SKILL,), 'godot': (GODOT_SKILL,), 'godot-ios': (SKILL, GODOT_SKILL)}
LINK = re.compile(r'\]\(([^)\s]+)\)')


def validate_profile_overlap(config):
    release = config['profiles']['workflow-release']
    if release.get('extends') != 'workflow' or 'inputs' in release:
        raise ValueError('workflow-release 必须 extends workflow 且不覆盖 inputs')


def slug(heading):
    """按 GitHub 规则生成标题锚点：小写、去标点、空格转连字符。"""
    return re.sub(r'[^\w\- ]', '', heading.strip().lower()).replace(' ', '-')


def anchors(path):
    seen, result = {}, set()
    for heading in re.findall(r'^#{1,6} +(.+?) *#*$', path.read_text(), re.M):
        base = slug(heading)
        count = seen.get(base, 0)
        seen[base] = count + 1
        result.add(base if count == 0 else f'{base}-{count}')
    return result


def document_links(root, name):
    path = root / name
    # 需求模板直接落地到 requirements/，链接按使用位置校验。
    parent = root / 'requirements' if name.endswith('/templates/requirement.md') else path.parent
    for link in LINK.findall(path.read_text()):
        if '://' in link or link.startswith('mailto:'):
            continue
        target, _, anchor = link.partition('#')
        yield (parent / target).resolve() if target else path.resolve(), anchor


def mode_link_errors(root, links):
    """每个安装包只含核心与所选 Skill，包内文档不能依赖未安装的 Skill。"""
    errors = []
    for mode, skills in MODE_SKILLS.items():
        packaged = {(root / name).resolve() for name in FILES if name.startswith((CORE + '/',) + tuple(s + '/' for s in skills))}
        for name, targets in links.items():
            if (root / name).resolve() not in packaged:
                continue
            for target, _ in targets:
                if target in packaged:
                    continue
                # 纯 Godot 模式下 Godot Skill 指向 iOS 的链接只属于标注「iOS」的路由，不会被加载。
                if mode == 'godot' and name.startswith(GODOT_SKILL + '/') and target.is_relative_to((root / SKILL).resolve()):
                    continue
                errors.append(f'{mode} 安装包中 {name} 链接了包外文件：{target.relative_to(root)}')
    return errors


def validate(root):
    root = Path(root).resolve()
    errors = []
    config = root / '.agents/project-checks.json'
    if config.is_file():
        validate_profile_overlap(json.loads(config.read_text()))
    missing = [name for name in FILES if not (root / name).is_file()]
    errors += ['缺文件：' + name for name in missing]
    documents = [name for name in FILES if name.endswith('.md') and name not in missing]
    documents += sorted(str(path.relative_to(root)) for path in (root / 'requirements').glob('*.md'))
    links = {name: list(document_links(root, name)) for name in documents}
    for name, targets in links.items():
        for target, anchor in targets:
            if not target.exists():
                errors.append(f'{name} 的链接不存在：{target.relative_to(root) if target.is_relative_to(root) else target}')
            elif anchor and target.suffix == '.md' and anchor not in anchors(target):
                errors.append(f'{name} 的锚点不存在：{target.name}#{anchor}')
    errors += mode_link_errors(root, links)
    for directory in (SKILL, GODOT_SKILL):
        skill = root / directory / 'SKILL.md'
        name = Path(directory).name.lower()
        if skill.exists() and not re.match(r'---\nname: ' + name + r'\ndescription: [^\n]+\n---\n', skill.read_text()):
            errors.append(name + ' Skill 元数据不完整')
    if len((root / 'AGENTS.md').read_bytes()) >= 32768:
        errors.append('AGENTS.md 超出默认 32 KiB 预算')
    if not re.fullmatch(r'\d+\.\d+\.\d+', (root / CORE / 'references/VERSION').read_text().strip()):
        errors.append('版本格式错误')
    version = (root / CORE / 'references/VERSION').read_text().strip()
    readme = (root / 'README.md').read_text()
    if '当前版本为 **' + version + '**' not in readme:
        errors.append('README 当前版本与 VERSION 不一致')
    # 分发文档中的版本示例必须与当前 VERSION 一致；CHANGELOG 与内测记录保留历史版本。
    historical = {'CHANGELOG.md', 'docs/TRIAL.md'}
    for name in FILES:
        if not name.endswith('.md') or name in historical:
            continue
        for found in {(a or b) for a, b in re.findall(r'-v(\d+\.\d+\.\d+)\.zip|至 (\d+\.\d+\.\d+)', (root / name).read_text())} - {version}:
            errors.append(f'{name} 的版本示例 {found} 与 VERSION {version} 不一致')
    if errors:
        raise ValueError('\n'.join(errors))


if __name__ == '__main__':
    validate(Path(__file__).resolve().parents[1])
    print('工作流入口、版本、文件清单和内部链接检查通过')
