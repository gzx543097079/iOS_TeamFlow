#!/usr/bin/env python3
"""选择可用 iPhone 模拟器，运行真实测试工程；失败保留非零退出码。"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--configuration', choices=('Debug', 'Release'), default='Debug')
parser.add_argument('--unit-tests-only', action='store_true')
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
env = os.environ.copy()
if not env.get('DEVELOPER_DIR') and Path('/Applications/Xcode.app/Contents/Developer').exists():
    env['DEVELOPER_DIR'] = '/Applications/Xcode.app/Contents/Developer'
try:
    subprocess.run(['xcodebuild', '-version'], env=env, check=True)
    data = json.loads(subprocess.check_output(['xcrun', 'simctl', 'list', 'devices', 'available', '-j'], env=env))
    devices = [d for runtime, group in data['devices'].items() if 'iOS' in runtime
               for d in group if d.get('isAvailable') and d['name'].startswith('iPhone')]
    if not devices:
        raise ValueError('没有可用 iPhone 模拟器，请先在 Xcode 安装 iOS runtime')
    requested = env.get('TEAMFLOW_SIMULATOR_ID')
    if requested:
        selected = next((d for d in devices if d['udid'] == requested), None)
        if selected is None:
            raise ValueError('TEAMFLOW_SIMULATOR_ID 不是可用 iPhone 模拟器')
    else:
        selected = next((d for d in reversed(devices) if d['state'] == 'Booted'), devices[-1])
    print('测试模拟器：' + selected['name'] + ' ' + selected['udid'], flush=True)
    command = ['xcodebuild', 'test', '-project', str(root / 'App/TeamFlowDemo/TeamFlowDemo.xcodeproj'),
               '-scheme', 'TeamFlowDemo', '-configuration', args.configuration, '-destination', 'platform=iOS Simulator,id=' + selected['udid'],
               '-derivedDataPath', str(root / 'DerivedData/TeamFlowDemo'),
               '-parallel-testing-enabled', 'NO', 'CODE_SIGNING_ALLOWED=NO']
    if args.unit_tests_only:
        # Release 单测允许访问内部类型，不改变 DEBUG 条件或日志行为。
        command.extend(['-only-testing:TeamFlowDemoTests', 'ENABLE_TESTABILITY=YES'])
    sys.exit(subprocess.run(command, cwd=root, env=env).returncode)
except (OSError, ValueError, subprocess.CalledProcessError) as error:
    print('测试工程未通过：' + str(error), file=sys.stderr)
    sys.exit(1)
