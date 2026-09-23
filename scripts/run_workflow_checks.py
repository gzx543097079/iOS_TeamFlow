#!/usr/bin/env python3
"""自动发现并执行工作流测试，不维护按文件或方法名的测试路由。"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    suite = unittest.TestLoader().discover(str(ROOT / 'tests'))
    if suite.countTestCases() == 0:
        raise SystemExit('未发现测试，不能将空套件视为通过')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(main())
