#!/usr/bin/env python3
"""将已安装 Skill 接入指定项目，预检冲突并保留既有文件。"""
import argparse
import json
from pathlib import Path

START = '<!-- ios-team-flow:start -->'
END = '<!-- ios-team-flow:end -->'
BLOCK = '''<!-- ios-team-flow:start -->
## iOS 团队工作流

本项目采用仓库内的 `.agents/skills/ios-team-flow/SKILL.md`。实施 iOS 需求和提交前必须读取该文件，无需用户再次点名 Skill；按 OC / Swift / SwiftUI / UI 类型加载规范，维护 requirements/ 需求过程与 logs/ 审查记录。
新产品先整理 PRD 交团队确认。提交前只 review 本次改动，相同有效指纹复用；运行 `python3 scripts/review_gate.py check`。未经授权不提交或发布。
版本见 .agents/teamflow.json，Skill 与项目一起提交和克隆，不依赖用户级安装。找不到本地 Skill 时明确报告缺失，不自动改用其他项目或用户级同名版本。遵守项目现有具体约定，有冲突先说明。
<!-- ios-team-flow:end -->
'''


GATE_ENTRY = '#!/usr/bin/env python3\n"""从项目内 Skill 加载审查门禁，唯一实现维护在 Skill 内。"""\nimport runpy\nfrom pathlib import Path\n\n_source = Path(__file__).resolve().parents[1] / \'.agents/skills/ios-team-flow/scripts/review_gate.py\'\nglobals().update(runpy.run_path(str(_source), run_name=__name__))\n'

def setup(project, skill):
    project = project.expanduser().resolve()
    skill = skill.resolve()
    if project == skill or project.is_relative_to(skill):
        raise ValueError('项目产物不能写入 Skill 安装目录')
    local_skill = project / '.agents/skills/ios-team-flow'
    if skill != local_skill or any(node.is_symlink() for node in
                                   (local_skill, local_skill.parent, local_skill.parent.parent)):
        raise ValueError('请先将完整 Skill 放入目标项目的 .agents/skills/ios-team-flow，再运行该项目内的接入脚本')
    version = (skill / 'references/VERSION').read_text().strip()
    manifest = json.dumps({'skill': 'ios-team-flow', 'version': version}, ensure_ascii=False, indent=2) + '\n'
    planned = {
        '.agents/teamflow.json': manifest.encode(),
        'scripts/review_gate.py': GATE_ENTRY.encode(),
    }
    conflicts = []
    override = project / 'AGENTS.override.md'
    if override.exists() and (not override.is_file() or override.stat().st_size > 0):
        conflicts.append('存在 AGENTS.override.md，需先将工作流入口合入有效指令文件')
    for name in (*planned, 'AGENTS.md', 'requirements', 'logs/reviews'):
        path = project / name
        for node in (path, *path.parents):
            if node == project:
                break
            if node.is_symlink():
                conflicts.append(name + ' 路径包含符号链接')
        for parent in path.parents:
            if parent == project:
                break
            if parent.exists() and not parent.is_dir():
                conflicts.append(name + ' 的父路径不是目录')
    for name, content in planned.items():
        target = project / name
        if target.exists() and (not target.is_file() or target.read_bytes() != content):
            conflicts.append(name + ' 已存在且内容/版本不同')
    agents = project / 'AGENTS.md'
    if agents.exists() and not agents.is_file():
        conflicts.append('AGENTS.md 不是文件')
    old = agents.read_text() if agents.is_file() else ''
    if START in old or END in old:
        if old.count(START) != 1 or old.count(END) != 1 or BLOCK.strip() not in old:
            conflicts.append('AGENTS.md 的工作流区块已定制或不完整')
        updated = old
    else:
        updated = old + ('\n\n' if old else '') + BLOCK
    for name in ('requirements', 'logs/reviews'):
        target = project / name
        if target.exists() and not target.is_dir():
            conflicts.append(name + ' 不是目录')
    if conflicts:
        raise ValueError('接入前预检发现冲突，未写入文件：\n' + '\n'.join(sorted(set(conflicts))))
    project.mkdir(parents=True, exist_ok=True)
    for name, content in planned.items():
        target = project / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    agents.write_text(updated)
    for name in ('requirements', 'logs/reviews'):
        (project / name).mkdir(parents=True, exist_ok=True)
    print('项目已接入 ios-team-flow ' + version + '：' + str(project))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    args = parser.parse_args()
    try:
        setup(args.project, Path(__file__).resolve().parents[1])
    except (ValueError, OSError) as error:
        parser.exit(1, str(error) + '\n')
