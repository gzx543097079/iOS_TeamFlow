#!/usr/bin/env python3
"""执行工作流测试：无参数时自动发现全部测试；传入测试文件名时只运行这些文件（分组见项目检查配置）。"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main(names):
    tests = ROOT / 'tests'
    loader = unittest.TestLoader()
    if names:
        missing = [name for name in names if not (tests / name).is_file()]
        if missing:
            raise SystemExit('测试文件不存在：' + '、'.join(missing))
        suite = unittest.TestSuite(loader.discover(str(tests), pattern=name) for name in names)
    else:
        suite = loader.discover(str(tests))
    if suite.countTestCases() == 0:
        raise SystemExit('未发现测试，不能将空套件视为通过')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
