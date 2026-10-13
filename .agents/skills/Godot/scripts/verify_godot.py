#!/usr/bin/env python3
"""检查项目内 Godot 导入与真实测试脚本，错误日志不能被退出码 0 掩盖。"""
import argparse
import re
import shutil
import subprocess
from pathlib import Path


def find_godot(explicit=None):
    if explicit:
        candidate = shutil.which(explicit) or explicit
    else:
        candidate = shutil.which('godot') or shutil.which('godot4')
        if not candidate and Path('/Applications/Godot.app/Contents/MacOS/Godot').is_file():
            candidate = '/Applications/Godot.app/Contents/MacOS/Godot'
    if not candidate or not Path(candidate).is_file():
        raise ValueError('未找到 Godot；使用 --godot 指定已有可执行文件')
    return str(Path(candidate).resolve())


def project_file(project, name):
    path = project / name
    if Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('文件必须相对游戏根：' + name)
    current = project
    for part in Path(name).parts:
        current /= part
        if current.is_symlink():
            raise ValueError('项目路径包含符号链接：' + name)
    if not path.is_file():
        raise ValueError('缺少项目文件：' + name)
    return path


def run_phase(argv, project, timeout):
    result = subprocess.run(argv, cwd=project, capture_output=True, text=True, timeout=timeout)
    output = result.stdout + '\n' + result.stderr
    if result.returncode or re.search(r'^\s*(?:SCRIPT ERROR|ERROR):', output, re.MULTILINE):
        raise ValueError('Godot 检查失败：\n' + output.strip())
    return result.stdout.strip()


def verify(project, godot=None, test_script=None, import_only=False, timeout=120, expected_version=None):
    project = Path(project).expanduser().resolve()
    project_file(project, 'project.godot')
    if import_only and test_script:
        raise ValueError('--import-only 与 --test-script 互斥')
    if not import_only:
        if not test_script:
            raise ValueError('必须提供真实 --test-script；仅导入需明确 --import-only')
        project_file(project, test_script)
    if timeout <= 0:
        raise ValueError('timeout 必须大于 0')
    executable = find_godot(godot)
    version = run_phase([executable, '--version'], project, timeout)
    if expected_version and version.split('.stable', 1)[0] != expected_version:
        raise ValueError('Godot 版本不匹配：预期 ' + expected_version + '，实际 ' + version)
    logs = project / '.godot/teamflow-checks'
    for path in (project / '.godot', logs):
        if path.is_symlink():
            raise ValueError('缓存路径包含符号链接')
    logs.mkdir(parents=True, exist_ok=True)
    for name in ('import.log', 'tests.log'):
        if (logs / name).is_symlink():
            raise ValueError('日志路径包含符号链接')
    base = [executable, '--headless', '--path', str(project)]
    run_phase(base + ['--log-file', str(logs / 'import.log'), '--editor', '--import'], project, timeout)
    if not import_only:
        run_phase(base + ['--log-file', str(logs / 'tests.log'), '--script', 'res://' + test_script], project, timeout)
    return version


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True)
    parser.add_argument('--godot')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--test-script')
    mode.add_argument('--import-only', action='store_true')
    parser.add_argument('--expect-version')
    parser.add_argument('--timeout', type=float, default=120)
    args = parser.parse_args()
    try:
        version = verify(args.project, args.godot, args.test_script, args.import_only,
                         args.timeout, args.expect_version)
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        parser.exit(1, '验证：失败\n' + str(error) + '\n')
    print('验证：通过（Godot ' + version + '，' + ('仅导入' if args.import_only else '导入与项目测试') + '）')


if __name__ == '__main__':
    main()
