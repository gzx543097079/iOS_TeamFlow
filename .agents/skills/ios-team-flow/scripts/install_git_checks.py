#!/usr/bin/env python3
"""显式安装/移除本仓库 Hook 或 PR 检查模板，不修改全局 Git 配置。"""
import argparse
import json
import os
import stat
import subprocess
from pathlib import Path

HOOK = '''#!/bin/sh
# ios-team-flow managed pre-commit v1
set -eu
hook_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ -f "$hook_dir/teamflow-pre-commit.previous" ]; then
  "$hook_dir/teamflow-pre-commit.previous" "$@"
fi
project_root=$(git rev-parse --show-toplevel)
cd "$project_root"
exec python3 .agents/skills/ios-team-flow/scripts/review_gate.py check
'''


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE).strip()


def paths(root):
    root = root.resolve()
    git_dir = Path(git(root, 'rev-parse', '--absolute-git-dir')).resolve()
    directory = Path(git(root, 'rev-parse', '--git-path', 'hooks'))
    if not directory.is_absolute():
        directory = root / directory
    if not (directory.resolve().is_relative_to(root) or directory.resolve().is_relative_to(git_dir)):
        raise ValueError('hooksPath 位于项目之外，可能被多个仓库共享；请在该 Hook 中手动调用审查命令')
    for node in (directory, *directory.parents):
        if node == root or node == git_dir:
            break
        if node.is_symlink():
            raise ValueError('Hook 路径不能含符号链接')
    return directory, directory / 'pre-commit', directory / 'teamflow-pre-commit.previous'


def install_hook(root):
    directory, target, backup = paths(root)
    if target.is_symlink() or backup.is_symlink():
        raise ValueError('不替换符号链接 Hook')
    if target.exists() and target.read_text() == HOOK:
        if not os.access(target, os.X_OK):
            target.chmod(target.stat().st_mode | stat.S_IXUSR)
        print('Hook 已安装')
        return
    if backup.exists():
        raise ValueError('已有 Hook 备份，当前入口不同，请先人工核对，不覆盖')
    if target.exists() and not os.access(target, os.X_OK):
        raise ValueError('现有 Hook 不可执行，先由团队确认如何处理')
    if target.exists() and 'ios-team-flow managed pre-commit' in target.read_text():
        raise ValueError('托管 Hook 已修改，先合并定制再安装')
    directory.mkdir(parents=True, exist_ok=True)
    if target.exists():
        target.rename(backup)
    try:
        with target.open('x') as stream:
            stream.write(HOOK)
        target.chmod(0o755)
    except OSError:
        if target.exists():
            target.unlink()
        if backup.exists():
            backup.rename(target)
        raise
    print('Hook 已安装；已有 Hook 会先执行并保留退出码')


def uninstall_hook(root):
    _, target, backup = paths(root)
    if target.is_symlink() or backup.is_symlink():
        raise ValueError('不处理符号链接 Hook')
    if not target.exists():
        if backup.exists():
            raise ValueError('入口缺失但备份存在，请人工恢复')
        return
    if target.read_text() != HOOK:
        raise ValueError('Hook 已被修改，拒绝覆盖或删除')
    target.unlink()
    if backup.exists():
        backup.rename(target)
    print('Hook 已移除，原 Hook 已恢复（如有）')


def install_ci(root):
    target = root / '.github/workflows/teamflow-pr-review.yml'
    for node in (target, target.parent, target.parent.parent):
        if node.is_symlink():
            raise ValueError('CI 目标不能包含符号链接')
    source = Path(__file__).resolve().parents[1] / 'assets/pr-review.yml'
    if target.exists():
        if target.read_bytes() == source.read_bytes():
            print('PR 检查模板已安装')
            return
        raise ValueError('同名 CI 已存在且内容不同，请合并后再使用')
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(source.read_bytes())
    print('已生成 PR 检查；提交到目标分支后生效，并在仓库规则中按需设为必需检查')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('hook-install', 'hook-uninstall', 'ci-install'))
    parser.add_argument('--project', type=Path, default=Path('.'))
    args = parser.parse_args()
    try:
        root = args.project.resolve()
        if Path(git(root, 'rev-parse', '--show-toplevel')).resolve() != root:
            raise ValueError('请指定 Git 根目录')
        {'hook-install': install_hook, 'hook-uninstall': uninstall_hook, 'ci-install': install_ci}[args.command](root)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
