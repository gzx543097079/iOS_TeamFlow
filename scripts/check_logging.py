#!/usr/bin/env python3
"""用 Apple 编译器验证真实日志行为；缺少 macOS/Xcode 时失败，不伪称通过。"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / '.agents/skills/ios-team-flow/assets/logging'
SWIFT_MAIN = r'''
var calls = 0
// 副作用仅用于验证 Release 的延迟求值边界。
@MainActor func message() -> String { calls += 1; return "中文消息100%" }
TFLog.debug(message())
TFLog.info(message())
TFLog.warning(message())
TFLog.error(message())
TFLog.fault(message())
TFLog.log(.info, message())
print("calls=\(calls)")
'''
OBJC_MAIN = r'''
#import "TFLogger.h"
static int calls = 0;
// 日志宏在 Release 中不能执行本函数。
static NSString *message(void) { calls++; return @"中文消息100%"; }
int main(void) {
    @autoreleasepool {
        if (YES) TFLDebug(@"%@", message()); else return 9;
        TFLInfo(@"%@", message());
        TFLWarning(@"%@", message());
        TFLError(@"%@", message());
        TFLFault(@"%@", message());
        TFLLog(TFLogLevelInfo, @"%@", message());
        printf("calls=%d\n", calls);
    }
    return 0;
}
'''


def run(argv, env):
    """保留编译/运行的失败诊断，避免截断输出掩盖失败。"""
    result = subprocess.run(argv, env=env, capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result


def verify_output(binary, env, debug):
    """同时验证等级、中文消息、调用位置和消息副作用次数。"""
    result = run([str(binary)], env)
    if result.stdout.strip() != ('calls=6' if debug else 'calls=0'):
        raise RuntimeError('消息求值次数错误：' + result.stdout)
    if debug:
        if result.stderr.count('中文消息100%') != 6:
            raise RuntimeError('Debug 未全量输出：' + result.stderr)
        for level in ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'FAULT'):
            if '[TFLog][' + level + ']' not in result.stderr:
                raise RuntimeError('缺少日志等级：' + level)
        if 'main.' not in result.stderr or 'TFLogger.swift:' in result.stderr:
            raise RuntimeError('未保留真实调用位置：' + result.stderr)
    elif result.stderr:
        raise RuntimeError('Release 仍有日志：' + result.stderr)


def main():
    """Debug、未定义 DEBUG、OC DEBUG=0 均用实际可执行文件验证。"""
    if sys.platform != 'darwin':
        raise RuntimeError('原生日志检查需要 macOS 和 Xcode')
    env = os.environ.copy()
    if not env.get('DEVELOPER_DIR') and Path('/Applications/Xcode.app').exists():
        env['DEVELOPER_DIR'] = '/Applications/Xcode.app/Contents/Developer'
    sdk = run(['xcrun', '--sdk', 'iphonesimulator', '--show-sdk-path'], env).stdout.strip()
    with tempfile.TemporaryDirectory() as name:
        temp = Path(name)
        swift_main, objc_main = temp / 'main.swift', temp / 'main.m'
        swift_main.write_text(SWIFT_MAIN)
        objc_main.write_text(OBJC_MAIN)
        for debug in (True, False):
            flags = ['-D', 'DEBUG'] if debug else []
            binary = temp / 'swift-log'
            run(['xcrun', 'swiftc', '-swift-version', '6', '-strict-concurrency=complete',
                 '-import-objc-header', str(ASSETS / 'TFLogger.h'),
                 *flags, str(ASSETS / 'TFLogger.swift'), str(swift_main), '-o', str(binary)], env)
            verify_output(binary, env, debug)
            # 同时用 iOS 14 模拟器 SDK 编译，不把 macOS 运行等同于 iOS 产品验证。
            run(['xcrun', 'swiftc', '-swift-version', '5', '-sdk', sdk,
                 '-target', 'arm64-apple-ios14.0-simulator', '-emit-module', '-parse-as-library',
                 *flags, str(ASSETS / 'TFLogger.swift'), '-o', str(temp / 'TFLog.swiftmodule')], env)
            print('Swift ' + ('Debug' if debug else 'Release') + '：运行及 iOS SDK 编译通过')
        for flags, debug in [(['-DDEBUG=1'], True), ([], False), (['-DDEBUG=0'], False)]:
            binary = temp / 'objc-log'
            common = ['-fobjc-arc', '-I', str(ASSETS), *flags]
            run(['xcrun', 'clang', *common, str(ASSETS / 'TFLogger.m'), str(objc_main),
                 '-framework', 'Foundation', '-o', str(binary)], env)
            verify_output(binary, env, debug)
            # Objective-C++ 调用同一 C 链接入口，验证 .mm 与 .m 混合链接。
            objcxx = temp / 'main.mm'
            objcxx.write_text(OBJC_MAIN)
            run(['xcrun', 'clang++', *common, str(ASSETS / 'TFLogger.m'), str(objcxx),
                 '-framework', 'Foundation', '-o', str(binary)], env)
            verify_output(binary, env, debug)
            run(['xcrun', 'clang', *common, '-isysroot', sdk, '-target', 'arm64-apple-ios14.0-simulator',
                 '-fsyntax-only', str(ASSETS / 'TFLogger.m'), str(objc_main)], env)
            print('OC/OC++ ' + ('Debug' if debug else 'Release') + '：运行及 iOS SDK 编译通过')


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
        print('原生日志检查失败：' + str(error), file=sys.stderr)
        raise SystemExit(1)
