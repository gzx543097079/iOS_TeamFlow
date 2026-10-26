#!/usr/bin/env python3
"""Release 构建检查（manual profile）。首次接入后与 check_debug.py 使用同一 scheme 配置。"""
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
    raise SystemExit('未找到 .xcworkspace / .xcodeproj')


def main():
    scheme = scheme_name()
    if not scheme:
        raise SystemExit('未配置 scheme：见 scripts/check_debug.py 顶部说明')
    kind, path = workspace_or_project()
    destination = os.environ.get(
        'TEAMFLOW_IOS_RELEASE_DESTINATION',
        'generic/platform=iOS Simulator',
    )
    cmd = [
        'xcodebuild', kind, path, '-scheme', scheme, '-configuration', 'Release',
        '-destination', destination, 'build',
    ]
    print('运行：', ' '.join(cmd), flush=True)
    raise SystemExit(subprocess.call(cmd, cwd=ROOT))


if __name__ == '__main__':
    main()
