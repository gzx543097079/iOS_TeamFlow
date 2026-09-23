#!/usr/bin/env python3
"""把 TeamFlow 接入项目并诊断实际文件。"""
import argparse
import difflib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from teamflow_common import local_path as safe

START = '<!-- ios-team-flow:start -->'
END = '<!-- ios-team-flow:end -->'
BLOCK = '''<!-- ios-team-flow:start -->
## iOS 工作流

读取项目内 `.agents/skills/ios-team-flow/SKILL.md`，由其路由主流程与专题。
项目空间是项目根及其目录树；处理空间外对象前，说明范围和操作并取得用户本次明确允许。
开发工具使用官方或既有包管理器默认位置；无法直接默认安装时停止，说明原因及安装、验证命令。
使用 `python3 scripts/teamflow.py`。主流程与状态以 Skill 的 `references/WORKFLOW.md` 为唯一规则来源。
<!-- ios-team-flow:end -->
'''
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
    return {
        'AGENTS.md': agents_content(current).encode(),
        'scripts/teamflow.py': ENTRY.encode(),

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
    print('项目已接入 ios-team-flow：' + str(project))


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
        skill = safe(project, '.agents/skills/ios-team-flow')
        version = (skill / 'references/VERSION').read_text().strip()
        validate_version(version)
        entry_ready = ((skill / 'SKILL.md').is_file()
                       and safe(project, 'scripts/teamflow.py').read_text() == ENTRY
                       and BLOCK.strip() in safe(project, 'AGENTS.md').read_text())
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
                for name, data in planned.items():
                    target = safe(args.project.resolve(), name)
                    current = target.read_text() if target.exists() else ''
                    sys.stdout.writelines(difflib.unified_diff(
                        current.splitlines(keepends=True), data.decode('utf-8').splitlines(keepends=True),
                        fromfile=name, tofile=name))
            else:
                diagnose(args.project)
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
