#!/usr/bin/env python3
"""按 Git 改动选择源仓库测试；未知范围回退全量，不替代 App 验证。"""
import argparse
import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = '.agents/skills/ios-team-flow/'
DOCUMENTS = 'test_workflow.WorkflowTests.test_repository_documents'
TEMPLATE = 'test_workflow.WorkflowTests.test_requirement_template_links_at_destination'
TOOLS = {
    'project_checks.py': ['test_project_checks', 'test_delivery', 'test_workflow', 'test_consumer_release', 'test_scenarios'],
    'delivery.py': ['test_delivery', 'test_workflow', 'test_consumer_release'],
    'review_gate.py': ['test_workflow', 'test_git_checks', 'test_consumer_release', 'test_scenarios'],
    'range_review.py': ['test_git_checks', 'test_workflow', 'test_consumer_release', 'test_scenarios'],
    'install_git_checks.py': ['test_git_checks', 'test_workflow', 'test_consumer_release'],
    'setup_project.py': ['test_workflow', 'test_setup_recovery', 'test_skill_upgrade', 'test_consumer_release', 'test_scenarios'],
    'upgrade_skill.py': ['test_workflow', 'test_setup_recovery', 'test_skill_upgrade', 'test_consumer_release'],
}


def select_checks(paths):
    selected = {DOCUMENTS}
    for path in paths:
        if (re.fullmatch(r'requirements/(?:DELIVERY\.md|(?:delivery/)?REQ-\d{8}-\d{9}Z-[0-9a-f]{8}\.(?:md|json))', path)
                or (path.startswith('logs/reviews/') and Path(path).suffix in ('.md', '.json', '.patch'))):
            continue
        if path in ('AGENTS.md', 'README.md', SKILL + 'SKILL.md'):
            continue
        if path.startswith(SKILL + 'references/') and path.endswith('.md'):
            if '/templates/' in path:
                selected.update([TEMPLATE, 'test_scenarios', 'test_consumer_release'])
            continue
        name = path.removeprefix(SKILL + 'scripts/')
        if path == 'scripts/review_gate.py':
            name = 'review_gate.py'
        if name in TOOLS and (path.startswith(SKILL + 'scripts/') or path == 'scripts/review_gate.py'):
            selected.update(TOOLS[name])
            continue
        # 未知文件、测试/CI/打包及版本变化都执行全量，避免遗漏跨模块依赖。
        return None
    # 某个模块已被选择时，不再额外执行该模块内的单项测试。
    return sorted(item for item in selected if '.' not in item or item.split('.')[0] not in selected)


def changed_paths(root, base, head):
    if not base or not re.fullmatch(r'[0-9a-fA-F]{40,64}', base) or set(base) == {'0'}:
        return None
    try:
        resolved = []
        for ref in (base, head):
            resolved.append(subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}'],
                           check=True, capture_output=True, text=True).stdout.strip())
        result = subprocess.run(['git', '-C', str(root), 'diff', '--name-only', '--no-renames', '-z', *resolved, '--'],
                                check=True, capture_output=True)
        return [p for p in result.stdout.decode().split('\0') if p]
    except (OSError, UnicodeError, subprocess.CalledProcessError):
        return None


def load_suite(root, selection):
    loader = unittest.TestLoader()
    if selection is None:
        return loader.discover(str(root / 'tests'))
    sys.path.insert(0, str(root / 'tests'))
    return loader.loadTestsFromNames(selection)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', help='完整基准提交 SHA；缺失或无法读取时执行全量')
    parser.add_argument('--head', default='HEAD')
    parser.add_argument('--full', action='store_true', help='发布或手动全量验证')
    parser.add_argument('--list', action='store_true', help='只读显示选择结果，不执行验证')
    args = parser.parse_args()
    paths = None if args.full else changed_paths(ROOT, args.base, args.head)
    selection = None if paths is None else select_checks(paths)
    print(json.dumps({'scope': 'full' if selection is None else 'changed',
                      'tests': ['all'] if selection is None else selection,
                      'reason': '显式全量、基准不可用或包含公共/未知改动' if selection is None else '按变更路径及关联模块选择'}, ensure_ascii=False), flush=True)
    if args.list:
        return 0
    suite = load_suite(ROOT, selection)
    if suite.countTestCases() == 0:
        parser.error("未发现测试，不能将空套件视为通过")
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    raise SystemExit(main())
