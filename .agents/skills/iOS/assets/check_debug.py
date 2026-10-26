#!/usr/bin/env python3
"""日常 Debug 编译（可选模块测试）。首次接入后按项目修改 SCHEME / 工程路径。

环境变量 TEAMFLOW_IOS_SCHEME 优先；否则读取 .agents/team/ios-verify.json 的 scheme 字段。
加 --all-tests 时跑全套测试（供 manual profile full-test 使用）。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALL_TESTS = '--all-tests' in sys.argv


def scheme_name():
    env = os.environ.get('TEAMFLOW_IOS_SCHEME', '').strip()
    if env:
        return env
    path = ROOT / '.agents/team/ios-verify.json'
    if path.is_file():
        data = json.loads(path.read_text())
        value = data.get('scheme')
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ''


def workspace_or_project():
    workspaces = sorted(ROOT.glob('*.xcworkspace')) + sorted((ROOT / 'App').glob('*.xcworkspace') if (ROOT / 'App').is_dir() else [])
    if workspaces:
        return '-workspace', str(workspaces[0])
    projects = sorted(ROOT.glob('*.xcodeproj')) + sorted((ROOT / 'App').glob('*.xcodeproj') if (ROOT / 'App').is_dir() else [])
    if projects:
        return '-project', str(projects[0])
    raise SystemExit('未找到 .xcworkspace / .xcodeproj；请把工程放在项目根或 App/，或改本脚本路径')


def main():
    scheme = scheme_name()
    if not scheme:
        raise SystemExit(
            '未配置 iOS scheme。任选其一：\n'
            '  export TEAMFLOW_IOS_SCHEME=YourScheme\n'
            '  或写入 .agents/team/ios-verify.json：{"scheme":"YourScheme"}\n'
            '行为改动请在本脚本用 -only-testing:Target/Class 做定向测，勿把全套测试留在日常 profile。'
        )
    kind, path = workspace_or_project()
    destination = os.environ.get('TEAMFLOW_IOS_DESTINATION', 'platform=iOS Simulator,name=iPhone 16')
    cmd = [
        'xcodebuild', kind, path, '-scheme', scheme, '-destination', destination,
        '-parallel-testing-enabled', 'NO',
    ]
    only = os.environ.get('TEAMFLOW_IOS_ONLY_TESTING', '').strip()
    if ALL_TESTS:
        cmd.append('test')
    elif only:
        cmd.extend(['test', '-only-testing:' + only])
    else:
        cmd.append('build')
    print('运行：', ' '.join(cmd), flush=True)
    raise SystemExit(subprocess.call(cmd, cwd=ROOT))


if __name__ == '__main__':
    main()
