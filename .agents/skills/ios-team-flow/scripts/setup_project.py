#!/usr/bin/env python3
"""把 vNext TeamFlow 接入一个新项目；不迁移或兼容旧版接入。"""
import argparse
import base64
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

START = '<!-- ios-team-flow:start -->'
END = '<!-- ios-team-flow:end -->'
BLOCK = '''<!-- ios-team-flow:start -->
## iOS 单人工作流

本项目使用 `.agents/skills/ios-team-flow/SKILL.md`。开发变更维护一张需求卡和一份验证证据；问答、检查和只读分析不建卡。
项目空间是当前 Git 根及其目录树；处理空间外对象前必须说明并取得用户本次明确允许。
需求卡和需求列表用固定彩色图标显示状态与 AC 进度；完整映射以 Skill 的 WORKFLOW 为准。
有实现与交付的任务按“完成全部改动 → 环境预检 → 针对性测试 → 文件冻结 → 一次完整验证 → 目标交付”执行；完整验证后受跟踪输入变化时必须重新冻结并验证。
commit、push、PR、合并、标签、GitHub Release，以及 Archive、TestFlight、Beta Review、App Store 审核、发布和下架只在用户明确目标时执行；目标若依赖尚未完成的前置步骤，自动执行最小必要前置，但不扩张到可选或后续动作。
普通 TestFlight 上传不启用 TestFlight Internal Only；只有用户明确要求仅内部测试时才允许写入 `testFlightInternalTestingOnly: true`。
使用 `python3 scripts/teamflow.py` 处理需求、验证和显式动作。未经明确指令不提交、不上传、不提审、不发布。
<!-- ios-team-flow:end -->
'''
ENTRY = '''#!/usr/bin/env python3
"""从项目内 Skill 加载 TeamFlow 唯一实现。"""
import runpy
from pathlib import Path

_source = Path(__file__).resolve().parents[1] / '.agents/skills/ios-team-flow/scripts/teamflow.py'
globals().update(runpy.run_path(str(_source), run_name=__name__))
'''


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('版本必须为 X.Y.Z')
    return tuple(map(int, value.split('.')))


def safe(project, name):
    path = project / name
    if Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('接入路径必须位于项目内：' + name)
    for node in (path, *path.parents):
        if node == project:
            break
        if node.is_symlink():
            raise ValueError('接入路径不能含符号链接：' + name)
    return path


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
    version_tuple(version)
    manifest_path = safe(project, '.agents/teamflow.json')
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text())
        if manifest.get('schema_version') != 2:
            raise ValueError('检测到旧版接入；vNext 不提供兼容升级，请在新项目或清理旧入口后接入')
    agents = safe(project, 'AGENTS.md')
    entry = safe(project, 'scripts/teamflow.py')
    for path in (agents, entry, manifest_path, safe(project, 'requirements')):
        if path.exists() and path not in (agents, entry, manifest_path) and not path.is_dir():
            raise ValueError('接入目标类型不正确：' + str(path.relative_to(project)))
    current = agents.read_text() if agents.exists() else ''
    return {
        'AGENTS.md': agents_content(current).encode(),
        'scripts/teamflow.py': ENTRY.encode(),
        '.agents/teamflow.json': (json.dumps({'schema_version': 2, 'skill': 'ios-team-flow',
                                              'version': version, 'instruction_file': 'AGENTS.md'},
                                             ensure_ascii=False, indent=2) + '\n').encode(),
    }


def setup(project, skill, dry_run=False):
    project = project.expanduser().resolve()
    planned = plan(project, skill)
    if dry_run:
        return planned
    for name, data in planned.items():
        target = safe(project, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    safe(project, 'requirements').mkdir(exist_ok=True)
    print('项目已接入 ios-team-flow vNext：' + str(project))


def diagnose(project):
    project = project.expanduser().resolve()
    items = []
    def add(name, ready, detail):
        items.append({'item': name, 'status': '就绪' if ready else '需处理', 'detail': detail})
    add('Python', sys.version_info >= (3, 10), sys.version.split()[0])
    try:
        top = subprocess.check_output(['git', '-C', str(project), 'rev-parse', '--show-toplevel'], text=True).strip()
        git_ready = Path(top).resolve() == project
    except (OSError, subprocess.CalledProcessError):
        git_ready = False
    add('Git 根目录', git_ready, '项目根必须是 Git 根')
    try:
        manifest = json.loads((project / '.agents/teamflow.json').read_text())
        version = (project / '.agents/skills/ios-team-flow/references/VERSION').read_text().strip()
        entry_ready = (manifest.get('schema_version') == 2 and manifest.get('version') == version
                       and (project / 'scripts/teamflow.py').is_file())
    except (OSError, ValueError, TypeError):
        entry_ready = False
        version = '未知'
    add('Skill 与入口', entry_ready, '版本 ' + version)
    add('项目验证', (project / '.agents/project-checks.json').is_file(),
        '工程就绪后配置实际构建/测试命令')
    add('Xcode', bool(shutil.which('xcodebuild')), '只检查工具入口')
    report = {'project': str(project), 'checks': items,
              'needs_action': any(item['status'] == '需处理' for item in items)}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--plan', action='store_true')
    parser.add_argument('--doctor', action='store_true')
    args = parser.parse_args()
    try:
        if args.doctor:
            if args.plan:
                raise ValueError('--doctor 与 --plan 不能组合')
            diagnose(args.project)
        else:
            planned = setup(args.project, Path(__file__).resolve().parents[1], args.plan)
            if args.plan:
                print(json.dumps({name: base64.b64encode(data).decode() for name, data in planned.items()}))
            else:
                diagnose(args.project)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
