#!/usr/bin/env python3
"""选择可用 iPhone 模拟器，运行真实测试工程；失败保留非零退出码。"""
import argparse
import json
import os
from pathlib import Path
import re
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
    devices = []
    for runtime, group in data['devices'].items():
        match = re.search(r'\.iOS-(\d+)-(\d+)$', runtime)
        if not match:
            continue
        version = tuple(map(int, match.groups()))
        devices.extend((version, device) for device in group
                       if device.get('isAvailable') and device['name'].startswith('iPhone'))
    if not devices:
        raise ValueError('没有可用 iPhone 模拟器，请先在 Xcode 安装 iOS runtime')
    requested = env.get('TEAMFLOW_SIMULATOR_ID')
    if requested:
        selected = next((device for _, device in devices if device['udid'] == requested), None)
        if selected is None:
            raise ValueError('TEAMFLOW_SIMULATOR_ID 不是可用 iPhone 模拟器')
    else:
        latest = max(version for version, _ in devices)
        compatible = [device for version, device in devices if version == latest]
        selected = next((device for device in compatible if device['state'] == 'Booted'), compatible[0])
    print('测试模拟器：' + selected['name'] + ' ' + selected['udid'], flush=True)
    workspace = root / 'examples/TeamFlowDemo/TeamFlowDemo.xcworkspace'
    if not (root / 'examples/TeamFlowDemo/Pods/Manifest.lock').exists():
        raise ValueError('请先在 examples/TeamFlowDemo 执行 pod install，再运行测试')
    command = ['xcodebuild', 'test', '-workspace', str(workspace),
               '-scheme', 'TeamFlowDemo', '-configuration', args.configuration, '-destination', 'platform=iOS Simulator,id=' + selected['udid'],
               '-derivedDataPath', str(root / 'DerivedData/TeamFlowDemo'),
               '-parallel-testing-enabled', 'NO', 'CODE_SIGNING_ALLOWED=NO',
               # Xcode 27 的模拟器不再接受 iOS 14；只提升测试构建目标，不改产品声明。
               'IPHONEOS_DEPLOYMENT_TARGET=15.0']
    if args.unit_tests_only:
        # Release 单测允许访问内部类型，不改变 DEBUG 条件或日志行为。
        command.extend(['-only-testing:TeamFlowDemoTests', 'ENABLE_TESTABILITY=YES'])
    sys.exit(subprocess.run(command, cwd=root, env=env).returncode)
except (OSError, ValueError, subprocess.CalledProcessError) as error:
    print('测试工程未通过：' + str(error), file=sys.stderr)
    sys.exit(1)
