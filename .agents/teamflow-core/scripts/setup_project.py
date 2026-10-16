#!/usr/bin/env python3
"""把 TeamFlow 接入项目并诊断实际文件；由 teamflow setup / doctor 调用。"""
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from teamflow_common import local_path as safe

START = '<!-- teamflow:start -->'
END = '<!-- teamflow:end -->'
READING_RULES = '''首次仅读取上述 Skill 和 `.agents/teamflow-core/references/WORKFLOW.md`，其余资料按 WORKFLOW「按需读取」加载。'''
TEAM_RULES = '''存在 `.agents/team/RULES.md` 时一并读取；团队规则可细化规范，不突破 WORKFLOW 的授权边界。'''
BLOCK = '''<!-- teamflow:start -->
## 工作流

读取并遵循 `.agents/skills/iOS/SKILL.md`；命令使用 `python3 scripts/teamflow.py`。

{reading_rules}
{team_rules}
<!-- teamflow:end -->
'''.format(reading_rules=READING_RULES, team_rules=TEAM_RULES)
GODOT_SKILL = '.agents/skills/Godot'
GODOT_BLOCK = '''<!-- teamflow:start -->
## Godot 工作流

读取并遵循 `.agents/skills/Godot/SKILL.md`；iOS 原生插件按该 Skill 的路由加载对应规范。需求、验证和交付复用 TeamFlow 核心；命令使用 `python3 scripts/teamflow.py`。

{reading_rules}
{team_rules}
<!-- teamflow:end -->
'''.format(reading_rules=READING_RULES, team_rules=TEAM_RULES)
GODOT_ONLY_MARK = '本项目不含 iOS 目标'
GODOT_ONLY_BLOCK = '''<!-- teamflow:start -->
## Godot 工作流

读取并遵循 `.agents/skills/Godot/SKILL.md`；{mark}，跳过该 Skill 的 iOS 导出、原生桥接与发布路由。需求、验证和交付复用 TeamFlow 核心；命令使用 `python3 scripts/teamflow.py`。

{reading_rules}
{team_rules}
<!-- teamflow:end -->
'''.format(mark=GODOT_ONLY_MARK, reading_rules=READING_RULES, team_rules=TEAM_RULES)
MODES = ('ios', 'godot', 'godot-ios')
MODE_LABELS = {'ios': 'iOS 原生', 'godot': 'Godot', 'godot-ios': 'Godot + iOS'}
# 各模式实际依赖的 Skill 目录；升级与打包按同一表选择文件。
MODE_SKILLS = {'ios': ('iOS',), 'godot': ('Godot',), 'godot-ios': ('iOS', 'Godot')}
IGNORE = '/logs/project-checks/'
GODOT_IGNORE = '.godot/'
TOOLCHAIN = '.agents/team/toolchain.json'
HOOK_MARK = '# teamflow:managed-hook'
HOOK = '''#!/bin/sh
{mark}
# 由 teamflow setup --git-hook 安装；git commit --no-verify 可临时跳过，--no-git-hook 移除。
exec python3 scripts/teamflow.py verify run --profile '{profile}'
'''
ENTRY = '''#!/usr/bin/env python3
"""从项目内 Skill 加载 TeamFlow 唯一实现。"""
import runpy
import sys
from pathlib import Path

# 工具运行不向业务仓库写入字节码缓存，也不改变子进程的 Python 配置。
sys.dont_write_bytecode = True
_source = Path(__file__).resolve().parents[1] / '.agents/teamflow-core/scripts/teamflow.py'
sys.path.insert(0, str(_source.parent))
globals().update(runpy.run_path(str(_source), run_name=__name__))
'''


def validate_version(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('版本必须为 X.Y.Z')


def managed_span(current):
    """定位唯一托管区块，重复接入时原位替换。"""
    if START not in current and END not in current:
        return None
    if current.count(START) > 1 or current.count(END) > 1:
        raise ValueError('AGENTS.md 存在多个托管区块')
    if current.count(START) != 1 or current.count(END) != 1 or current.index(START) >= current.index(END):
        raise ValueError('AGENTS.md 托管标记无效')
    return current.index(START), current.index(END) + len(END), current.split(START, 1)[1].split(END, 1)[0]


def agents_content(current, block=BLOCK):
    span = managed_span(current)
    if span:
        start, end, _ = span
        return current[:start] + block.strip() + current[end:]
    return current + ('\n\n' if current else '') + block


def install_mode(project, mode=None):
    """选型只记录在托管入口；重复 setup 沿用已有选择，首次默认 iOS 原生。"""
    if mode is not None:
        if mode not in MODES:
            raise ValueError('安装模式必须为 ' + '、'.join(MODES))
        return mode
    agents = safe(project, 'AGENTS.md')
    current = agents.read_text() if agents.is_file() else ''
    span = managed_span(current)
    if span:
        block = span[2]
        if any(line.startswith('## Godot ') for line in block.splitlines()):
            return 'godot' if GODOT_ONLY_MARK in block else 'godot-ios'
    return 'ios'


def project_block(project, mode=None):
    """只检查选中的安装路径；残留扩展目录不改变原生项目模式。"""
    mode = install_mode(project, mode)
    if mode == 'ios':
        if not safe(project, '.agents/skills/iOS/SKILL.md').is_file():
            raise ValueError('原生 Skill 不完整：请先安装 iOS 原生包')
        return BLOCK
    if mode == 'godot':
        if not safe(project, GODOT_SKILL + '/SKILL.md').is_file():
            raise ValueError('Godot 扩展不完整：请先安装 Godot 包')
        return GODOT_ONLY_BLOCK
    if not safe(project, '.agents/skills/iOS/SKILL.md').is_file():
        raise ValueError('iOS 平台依赖不完整：请先安装完整 Godot + iOS 包')
    extension = safe(project, GODOT_SKILL)
    if not extension.is_dir() or not safe(project, GODOT_SKILL + '/SKILL.md').is_file():
        raise ValueError('Godot 扩展不完整：请先安装含同版核心的 Godot 扩展包')
    return GODOT_BLOCK


def block_for(mode):
    """打包与接入共用同一份入口文本。"""
    return {'ios': BLOCK, 'godot': GODOT_ONLY_BLOCK, 'godot-ios': GODOT_BLOCK}[mode]


def ignore_lines(mode):
    return [IGNORE] + ([GODOT_IGNORE] if mode != 'ios' else [])


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
    # 验证日志只作本地证据，需求卡保存可复核的指纹摘要；Godot 编辑器缓存与导出凭据不提交。
    missing = [line for line in ignore_lines(install_mode(project, mode)) if line not in ignored.split('\n')]
    if missing:
        planned['.gitignore'] = (ignored + ('' if not ignored or ignored.endswith('\n') else '\n')
                                 + ''.join(line + '\n' for line in missing)).encode()
    return planned


def claude_link_spec(mode):
    name = 'ios' if mode == 'ios' else 'godot'
    directory = 'iOS' if mode == 'ios' else 'Godot'
    return '.claude/skills/' + name, '../../.agents/skills/' + directory


def hook_path(project):
    """按 Git 实际解析的 Hook 位置安装，支持 worktree 与项目内 core.hooksPath；不改项目外共享目录。"""
    def git(*args):
        return subprocess.check_output(['git', '-C', str(project), *args], text=True,
                                       stderr=subprocess.DEVNULL).strip()
    try:
        path = Path(git('rev-parse', '--git-path', 'hooks/pre-commit'))
        common = Path(git('rev-parse', '--git-common-dir'))
    except (OSError, subprocess.CalledProcessError):
        raise ValueError('提交前检查需要项目位于 Git 仓库')
    path = (path if path.is_absolute() else project / path).resolve()
    common = (common if common.is_absolute() else project / common).resolve()
    if not (path.is_relative_to(project) or path.is_relative_to(common)):
        raise ValueError('core.hooksPath 指向项目外，不修改共享 Hook 目录：' + str(path))
    return path


def managed_hook_profile(path):
    """返回托管 Hook 的 profile；非托管 Hook 返回空串，不存在返回 None。"""
    if not path.exists() and not path.is_symlink():
        return None
    text = path.read_text() if path.is_file() and not path.is_symlink() else ''
    if HOOK_MARK not in text:
        return ''
    match = re.search(r"--profile '([^']+)'", text)
    return match.group(1) if match else ''


def hook_plan(project, profile=None, remove=False):
    """返回 Hook 目标路径与新内容；None 表示删除托管 Hook。"""
    path = hook_path(project)
    current = managed_hook_profile(path)
    if current == '':
        raise ValueError('已存在非 TeamFlow 管理的 pre-commit Hook，不覆盖：' + str(path))
    if remove:
        return path, None
    if not re.fullmatch(r'[A-Za-z0-9_.-]+', profile):
        raise ValueError('profile 名称只能包含字母、数字、点、下划线和连字符')
    import project_checks
    if profile not in project_checks.load_config(project)['profiles']:
        raise ValueError('未配置所选 profile：' + profile)
    return path, HOOK.format(mark=HOOK_MARK, profile=profile)


def setup(project, skill, dry_run=False, claude_link=False, mode=None, git_hook=None, remove_hook=False):
    """返回计划写入的文件；claude_link 额外让 Claude Code 把 Skill 识别为原生 Skill。"""
    project = project.expanduser().resolve()
    mode = install_mode(project, mode)
    planned = plan(project, skill, mode)
    hook = hook_plan(project, git_hook, remove_hook) if git_hook or remove_hook else None
    if hook and hook[1] is not None:
        planned[str(hook[0])] = hook[1].encode()
    link_name, link_target = claude_link_spec(mode)
    link = project / link_name
    opposite_name, opposite_target = claude_link_spec('godot' if mode == 'ios' else 'ios')
    opposite = project / opposite_name
    # 曾选择 Claude 接入的项目切换模式时，同步唯一受管理的 Skill 链接。
    managed_opposite = opposite.is_symlink() and os.readlink(opposite) == opposite_target
    link_ready = link.is_symlink() and os.readlink(link) == link_target
    enable_link = claude_link or managed_opposite or link_ready
    if enable_link:
        safe(project, '.claude/skills')
        if not link_ready and (link.exists() or link.is_symlink()):
            raise ValueError(link_name + ' 已存在且不是指向本项目 Skill 的软链接')
    if dry_run:
        return planned
    for name, data in planned.items():
        if Path(name).is_absolute():
            continue
        target = safe(project, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    if hook:
        path, content = hook
        if content is None:
            if path.exists():
                path.unlink()
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            path.chmod(0o755)
    safe(project, 'requirements').mkdir(exist_ok=True)
    if enable_link and not link_ready:
        safe(project, '.claude/skills').mkdir(parents=True, exist_ok=True)
        link.symlink_to(link_target, target_is_directory=True)
    if enable_link and managed_opposite:
        opposite.unlink()
    return planned


def diagnose(project):
    project = project.expanduser().resolve()
    items = []
    def add(name, ready, detail):
        items.append({'item': name, 'status': '就绪' if ready else '需处理', 'detail': detail})
    try:
        top = subprocess.check_output(['git', '-C', str(project), 'rev-parse', '--show-toplevel'], text=True,
                                      stderr=subprocess.DEVNULL).strip()
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
    if source_repository(project):
        add('Skill 与入口', True, 'TeamFlow 源码仓库，不安装托管入口，版本 ' + version)
        mode = '未知'
    else:
        add('Skill 与入口', entry_ready, MODE_LABELS.get(mode, '未知模式') + '，版本 ' + version)
    try:
        config_ready = safe(project, '.agents/project-checks.json').is_file()
    except ValueError:
        config_ready = False
    add('项目验证', config_ready, '工程就绪后配置实际构建/测试命令')
    add('Xcode', bool(shutil.which('xcodebuild')), '只检查工具入口')
    if git_ready:
        items.extend(hook_status(project))
    if mode in ('godot', 'godot-ios'):
        items.extend(godot_status(project, git_ready))
    if mode in ('ios', 'godot-ios'):
        items.extend(xcode_status(project))
    return {'project': str(project), 'checks': items,
            'needs_action': any(item['status'] == '需处理' for item in items)}


def source_repository(project):
    """工作流源码仓库带打包脚本且 AGENTS 不含托管区块；安装包不含打包脚本。"""
    agents = project / 'AGENTS.md'
    return ((project / 'scripts/package_release.py').is_file()
            and not (agents.is_file() and START in agents.read_text()))


def hook_status(project):
    try:
        profile = managed_hook_profile(hook_path(project))
    except ValueError:
        return []
    if not profile:
        return []
    try:
        import project_checks
        ready = profile in project_checks.load_config(project)['profiles']
    except (ValueError, OSError, KeyError, TypeError):
        ready = False
    return [{'item': '提交前检查', 'status': '就绪' if ready else '需处理',
             'detail': 'pre-commit 运行 ' + profile + ('' if ready else '；该 profile 不存在')}]


def toolchain(project):
    """读取团队锁定的工具链版本；未锁定返回空字典。"""
    path = safe(project, TOOLCHAIN)
    if not path.is_file():
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(TOOLCHAIN + ' 必须为 JSON 对象')
    for key in ('godot', 'xcode'):
        value = data.get(key)
        if value is not None and not (isinstance(value, str) and re.fullmatch(r'\d+\.\d+(?:\.\d+)?', value)):
            raise ValueError(TOOLCHAIN + ' 的 ' + key + ' 须为 X.Y 或 X.Y.Z')
    return data


def xcode_version():
    first = subprocess.run(['xcodebuild', '-version'], capture_output=True, text=True, timeout=30).stdout
    return first.split('\n', 1)[0].removeprefix('Xcode ').strip()


def xcode_status(project):
    """Xcode 版本只在团队锁定时核对；xcodebuild -version 首行形如 Xcode 16.4。"""
    try:
        pinned = toolchain(project).get('xcode')
    except (ValueError, OSError):
        return []  # 格式错误由 Godot 或通用诊断报告一次即可
    if not pinned:
        return []
    try:
        actual = xcode_version()
        ready, detail = actual == pinned, '锁定 ' + pinned + '，本机 ' + (actual or '未知')
    except (OSError, subprocess.SubprocessError) as error:
        ready, detail = False, '锁定 ' + pinned + '；' + str(error)
    return [{'item': 'Xcode 版本锁定', 'status': '就绪' if ready else '需处理', 'detail': detail}]


def engine_matches(version, pinned):
    """Godot --version 形如 4.7.2.stable.official.hash；锁定值与 .stable 之前部分精确比较。"""
    return version.split('.stable', 1)[0] == pinned


def godot_version(project):
    import importlib.util
    script = safe(project, GODOT_SKILL + '/scripts/verify_godot.py')
    spec = importlib.util.spec_from_file_location('verify_godot', script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    executable = module.find_godot()
    return subprocess.run([executable, '--version'], capture_output=True, text=True, timeout=30).stdout.strip()


def godot_status(project, git_ready):
    """团队协作最常见的问题是引擎版本不一致和编辑器缓存入库，只读报告。"""
    items = []
    try:
        pinned = toolchain(project).get('godot')
    except (ValueError, OSError) as error:
        items.append({'item': 'Godot 版本锁定', 'status': '需处理', 'detail': str(error)})
        pinned = None
    else:
        if not pinned:
            items.append({'item': 'Godot 版本锁定', 'status': '提示',
                          'detail': '未锁定；团队协作建议在 ' + TOOLCHAIN + ' 写入 {"godot": "X.Y.Z"}'})
    if pinned:
        try:
            actual = godot_version(project)
            ready = engine_matches(actual, pinned)
            detail = '锁定 ' + pinned + '，本机 ' + actual
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            ready, detail = False, '锁定 ' + pinned + '；' + str(error)
        items.append({'item': 'Godot 版本锁定', 'status': '就绪' if ready else '需处理', 'detail': detail})
    if not git_ready:
        return items
    listed = subprocess.run(['git', '-C', str(project), 'ls-files', '-z', '--cached', '--others',
                             '--exclude-standard', '--', ':(glob)**/project.godot'],
                            capture_output=True, text=True)
    roots = sorted({str(Path(name).parent) for name in listed.stdout.split('\0') if name})
    if not roots:
        items.append({'item': 'Godot 缓存忽略', 'status': '提示', 'detail': '未找到 project.godot'})
        return items
    exposed = []
    for root in roots:
        probe = ('' if root == '.' else root + '/') + '.godot/teamflow-probe'
        if subprocess.run(['git', '-C', str(project), 'check-ignore', '-q', '--no-index', probe]).returncode:
            exposed.append(root)
    items.append({'item': 'Godot 缓存忽略', 'status': '需处理' if exposed else '就绪',
                  'detail': ('未忽略 .godot/：' + '、'.join(exposed)) if exposed else '、'.join(roots)})
    return items
