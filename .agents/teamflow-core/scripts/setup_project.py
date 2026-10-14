#!/usr/bin/env python3
"""把 TeamFlow 接入项目并诊断实际文件；由 teamflow setup / doctor 调用。"""
import os
import re
import shutil
import subprocess
from pathlib import Path
from teamflow_common import local_path as safe

START = '<!-- teamflow:start -->'
END = '<!-- teamflow:end -->'
LEGACY_MARKERS = ('<!-- ios-team-flow:start -->', '<!-- ios-team-flow:end -->')
READING_RULES = '''首次仅读取上述 Skill 和 `.agents/teamflow-core/references/WORKFLOW.md`，其余资料按 WORKFLOW「按需读取」加载。'''
BLOCK = '''<!-- teamflow:start -->
## 工作流

读取并遵循 `.agents/skills/iOS/SKILL.md`；命令使用 `python3 scripts/teamflow.py`。

{reading_rules}
<!-- teamflow:end -->
'''.format(reading_rules=READING_RULES)
GODOT_SKILL = '.agents/skills/Godot'
GODOT_BLOCK = '''<!-- teamflow:start -->
## Godot 工作流

读取并遵循 `.agents/skills/Godot/SKILL.md`；iOS 原生插件按该 Skill 的路由加载对应规范。需求、验证和交付复用 TeamFlow 核心；命令使用 `python3 scripts/teamflow.py`。

{reading_rules}
<!-- teamflow:end -->
'''.format(reading_rules=READING_RULES)
IGNORE = '/logs/project-checks/'
ENTRY = '''#!/usr/bin/env python3
"""从项目内 Skill 加载 TeamFlow 唯一实现。"""
import runpy
import sys
from pathlib import Path

_source = Path(__file__).resolve().parents[1] / '.agents/teamflow-core/scripts/teamflow.py'
sys.path.insert(0, str(_source.parent))
globals().update(runpy.run_path(str(_source), run_name=__name__))
'''


def validate_version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('版本必须为 X.Y.Z')


def managed_span(current):
    """更新旧接入标记时替换原区块，避免升级后叠加两个入口。"""
    found = [(start, end) for start, end in ((START, END), LEGACY_MARKERS)
             if start in current or end in current]
    if not found:
        return None
    if len(found) != 1:
        raise ValueError('AGENTS.md 存在多个托管区块')
    start, end = found[0]
    if current.count(start) != 1 or current.count(end) != 1 or current.index(start) >= current.index(end):
        raise ValueError('AGENTS.md 托管标记无效')
    return current.index(start), current.index(end) + len(end), current.split(start, 1)[1].split(end, 1)[0]


def agents_content(current, block=BLOCK):
    span = managed_span(current)
    if span:
        start, end, _ = span
        return current[:start] + block.strip() + current[end:]
    return current + ('\n\n' if current else '') + block


def install_mode(project, mode=None):
    """选型只记录在托管入口；重复 setup 沿用已有选择，首次默认 iOS 原生。"""
    if mode is not None:
        if mode not in ('ios', 'godot-ios'):
            raise ValueError('安装模式必须为 ios 或 godot-ios')
        return mode
    agents = safe(project, 'AGENTS.md')
    current = agents.read_text() if agents.is_file() else ''
    span = managed_span(current)
    if span:
        block = span[2]
        if any(line.startswith('## Godot ') for line in block.splitlines()):
            return 'godot-ios'
    return 'ios'


def project_block(project, mode=None):
    """只检查选中的安装路径；残留扩展目录不改变原生项目模式。"""
    if install_mode(project, mode) == 'ios':
        if not safe(project, '.agents/skills/iOS/SKILL.md').is_file():
            raise ValueError('原生 Skill 不完整：请先安装 iOS 原生包')
        return BLOCK
    if not safe(project, '.agents/skills/iOS/SKILL.md').is_file():
        raise ValueError('iOS 平台依赖不完整：请先安装完整 Godot + iOS 包')
    extension = safe(project, GODOT_SKILL)
    if not extension.is_dir() or not safe(project, GODOT_SKILL + '/SKILL.md').is_file():
        raise ValueError('Godot 扩展不完整：请先安装含同版核心的 Godot 扩展包')
    return GODOT_BLOCK


def plan(project, skill, mode=None):
    project = project.expanduser().resolve()
    skill = skill.resolve()
    expected = safe(project, '.agents/teamflow-core')
    if skill != expected or not (skill / 'scripts/teamflow.py').is_file():
        raise ValueError('请先把完整共用核心放到当前项目 .agents/teamflow-core')
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
        'AGENTS.md': agents_content(current, project_block(project, mode)).encode(),
        'scripts/teamflow.py': ENTRY.encode(),
    }
    # 验证日志只作本地证据，需求卡保存可复核的指纹摘要。
    if IGNORE not in ignored.split('\n'):
        planned['.gitignore'] = (ignored + ('' if not ignored or ignored.endswith('\n') else '\n')
                                 + IGNORE + '\n').encode()
    return planned


def claude_link_spec(mode):
    name = 'godot' if mode == 'godot-ios' else 'ios'
    directory = 'Godot' if mode == 'godot-ios' else 'iOS'
    return '.claude/skills/' + name, '../../.agents/skills/' + directory


def setup(project, skill, dry_run=False, claude_link=False, mode=None):
    """返回计划写入的文件；claude_link 额外让 Claude Code 把 Skill 识别为原生 Skill。"""
    project = project.expanduser().resolve()
    mode = install_mode(project, mode)
    planned = plan(project, skill, mode)
    link_name, link_target = claude_link_spec(mode)
    link = project / link_name
    opposite_name, opposite_target = claude_link_spec('ios' if mode == 'godot-ios' else 'godot-ios')
    opposite = project / opposite_name
    # 曾选择 Claude 接入的项目切换模式时，同步唯一受管理的 Skill 链接。
    managed_opposite = opposite.is_symlink() and os.readlink(opposite) == opposite_target
    link_ready = link.is_symlink() and os.readlink(link) == link_target
    legacy_links = []
    for name in ('ios-team-flow', 'godot-team-flow'):
        old_link = project / '.claude/skills' / name
        if old_link.is_symlink() and os.readlink(old_link) == '../../.agents/skills/' + name:
            legacy_links.append(old_link)
    enable_link = claude_link or managed_opposite or link_ready or bool(legacy_links)
    if enable_link:
        safe(project, '.claude/skills')
        if not link_ready and (link.exists() or link.is_symlink()):
            raise ValueError(link_name + ' 已存在且不是指向本项目 Skill 的软链接')
    if dry_run:
        return planned
    for name, data in planned.items():
        target = safe(project, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    safe(project, 'requirements').mkdir(exist_ok=True)
    if enable_link and not link_ready:
        safe(project, '.claude/skills').mkdir(parents=True, exist_ok=True)
        link.symlink_to(link_target, target_is_directory=True)
    if enable_link and managed_opposite:
        opposite.unlink()
    for old_link in legacy_links:
        old_link.unlink()
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
    mode = '未知'
    try:
        safe(project, '.agents/teamflow-core')
        mode = install_mode(project)
        version = safe(project, '.agents/teamflow-core/references/VERSION').read_text().strip()
        validate_version(version)
        entry_ready = (safe(project, '.agents/teamflow-core/scripts/teamflow.py').is_file()
                       and safe(project, 'scripts/teamflow.py').read_text() == ENTRY
                       and project_block(project).strip() in safe(project, 'AGENTS.md').read_text())
    except (OSError, ValueError, TypeError):
        entry_ready = False
        version = '未知'
    mode_label = {'godot-ios': 'Godot + iOS', 'ios': 'iOS 原生'}.get(mode, '未知模式')
    add('Skill 与入口', entry_ready, mode_label + '，版本 ' + version)
    try:
        config_ready = safe(project, '.agents/project-checks.json').is_file()
    except ValueError:
        config_ready = False
    add('项目验证', config_ready, '工程就绪后配置实际构建/测试命令')
    add('Xcode', bool(shutil.which('xcodebuild')), '只检查工具入口')
    return {'project': str(project), 'checks': items,
            'needs_action': any(item['status'] == '需处理' for item in items)}
