#!/usr/bin/env python3
"""把 TeamFlow 接入项目并诊断实际文件；由 teamflow setup / doctor 调用。"""
import os
import re
import shutil
import subprocess
from pathlib import Path
from teamflow_common import local_path as safe

START = '<!-- ios-team-flow:start -->'
END = '<!-- ios-team-flow:end -->'
BLOCK = '''<!-- ios-team-flow:start -->
## iOS 工作流

读取并遵循 `.agents/skills/ios-team-flow/SKILL.md`；命令使用 `python3 scripts/teamflow.py`。
<!-- ios-team-flow:end -->
'''
IGNORE = '/logs/project-checks/'
CLAUDE_LINK = '.claude/skills/ios-team-flow'
CLAUDE_TARGET = '../../.agents/skills/ios-team-flow'
ENTRY = '''#!/usr/bin/env python3
"""从项目内 Skill 加载 TeamFlow 唯一实现。"""
import runpy
import sys
from pathlib import Path

_source = Path(__file__).resolve().parents[1] / '.agents/skills/ios-team-flow/scripts/teamflow.py'
sys.path.insert(0, str(_source.parent))
globals().update(runpy.run_path(str(_source), run_name=__name__))
'''


def validate_version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('版本必须为 X.Y.Z')


def agents_content(current):
    if START in current or END in current:
        if current.count(START) != 1 or current.count(END) != 1 or current.index(START) >= current.index(END):
            raise ValueError('AGENTS.md 托管标记无效')
        start = current.index(START)
        end = current.index(END) + len(END)
        return current[:start] + BLOCK.strip() + current[end:]
    return current + ('\n\n' if current else '') + BLOCK


def plan(project, skill):
    project = project.expanduser().resolve()
    skill = skill.resolve()
    expected = project / '.agents/skills/ios-team-flow'
    if skill != expected or not (skill / 'SKILL.md').is_file():
        raise ValueError('请先把完整 Skill 放到当前项目 .agents/skills/ios-team-flow')
    version = (skill / 'references/VERSION').read_text().strip()
    validate_version(version)
    agents = safe(project, 'AGENTS.md')
    entry = safe(project, 'scripts/teamflow.py')
    for path in (agents, entry, safe(project, 'requirements')):
        if path.exists() and path not in (agents, entry) and not path.is_dir():
            raise ValueError('接入目标类型不正确：' + str(path.relative_to(project)))
    current = agents.read_text() if agents.exists() else ''
    ignore = safe(project, '.gitignore')
    ignored = ignore.read_text() if ignore.exists() else ''
    planned = {
        'AGENTS.md': agents_content(current).encode(),
        'scripts/teamflow.py': ENTRY.encode(),
    }
    # 验证日志只作本地证据，需求卡保存可复核的指纹摘要。
    if IGNORE not in ignored.split('\n'):
        planned['.gitignore'] = (ignored + ('' if not ignored or ignored.endswith('\n') else '\n')
                                 + IGNORE + '\n').encode()
    return planned


def claude_link_ready(project):
    link = project / CLAUDE_LINK
    return link.is_symlink() and os.readlink(link) == CLAUDE_TARGET


def setup(project, skill, dry_run=False, claude_link=False):
    """返回计划写入的文件；claude_link 额外让 Claude Code 把 Skill 识别为原生 Skill。"""
    project = project.expanduser().resolve()
    planned = plan(project, skill)
    link = project / CLAUDE_LINK
    if claude_link and not claude_link_ready(project) and (link.exists() or link.is_symlink()):
        raise ValueError(CLAUDE_LINK + ' 已存在且不是指向本项目 Skill 的软链接')
    if dry_run:
        return planned
    for name, data in planned.items():
        target = safe(project, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    safe(project, 'requirements').mkdir(exist_ok=True)
    if claude_link and not claude_link_ready(project):
        safe(project, '.claude/skills').mkdir(parents=True, exist_ok=True)
        link.symlink_to(CLAUDE_TARGET, target_is_directory=True)
    return planned


def diagnose(project):
    project = project.expanduser().resolve()
    items = []
    def add(name, ready, detail):
        items.append({'item': name, 'status': '就绪' if ready else '需处理', 'detail': detail})
    try:
        top = subprocess.check_output(['git', '-C', str(project), 'rev-parse', '--show-toplevel'], text=True).strip()
        git_ready = Path(top).resolve() == project
    except (OSError, subprocess.CalledProcessError):
        git_ready = False
    add('Git 根目录', git_ready, '项目根必须是 Git 根')
    try:
        skill = safe(project, '.agents/skills/ios-team-flow')
        version = safe(project, '.agents/skills/ios-team-flow/references/VERSION').read_text().strip()
        validate_version(version)
        entry_ready = (safe(project, '.agents/skills/ios-team-flow/SKILL.md').is_file()
                       and safe(project, 'scripts/teamflow.py').read_text() == ENTRY
                       and BLOCK.strip() in safe(project, 'AGENTS.md').read_text())
    except (OSError, ValueError, TypeError):
        entry_ready = False
        version = '未知'
    add('Skill 与入口', entry_ready, '版本 ' + version)
    try:
        config_ready = safe(project, '.agents/project-checks.json').is_file()
    except ValueError:
        config_ready = False
    add('项目验证', config_ready, '工程就绪后配置实际构建/测试命令')
    add('Xcode', bool(shutil.which('xcodebuild')), '只检查工具入口')
    return {'project': str(project), 'checks': items,
            'needs_action': any(item['status'] == '需处理' for item in items)}
