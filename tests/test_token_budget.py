"""按典型任务的实际读取链路约束文档体量，防止规则膨胀抵消按需加载。"""
import math
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.agents/teamflow-core/scripts'))
import setup_project

CORE = '.agents/teamflow-core/references/'
IOS = '.agents/skills/iOS/'
GODOT = '.agents/skills/Godot/'
# 估算值：中日韩字符按 1 token，其余按 3.5 字符 1 token；只用于相对约束，不代表计费。
# 上限是防膨胀护栏而非优化目标，留约 10% 余量；不为压低估算而牺牲规则清晰度。
FILE_BUDGET = 2500
ENTRY_BUDGET = 3650
SCENARIOS = {
    'iOS UI 缺陷修复并提交': (10700, 'ios', (
        CORE + 'REPAIR.md', CORE + 'CHECKS.md', CORE + 'BOUNDARIES.md',
        IOS + 'references/standards/swift.md', IOS + 'references/standards/ui.md')),
    'iOS 新功能（含输入与多语言）': (17100, 'ios', (
        IOS + 'references/templates/feature.md', CORE + 'ARCHITECTURE.md', IOS + 'references/ARCHITECTURE.md',
        CORE + 'LOCALIZATION.md', IOS + 'references/LOCALIZATION.md', IOS + 'references/standards/swift.md',
        IOS + 'references/standards/ui.md', IOS + 'references/standards/ui-keyboard.md', CORE + 'CHECKS.md')),
    'iOS UI 评审': (8000, 'ios', (
        IOS + 'references/UI-REVIEW.md', IOS + 'references/standards/ui.md')),
    'Godot + iOS 发布': (10800, 'godot-ios', (
        GODOT + 'references/IOS.md', IOS + 'references/APP-RELEASE.md', GODOT + 'references/CHECKS.md',
        CORE + 'CHECKS.md', CORE + 'BOUNDARIES.md')),
    '纯 Godot 发布': (9100, 'godot', (
        GODOT + 'references/RELEASE.md', GODOT + 'references/CHECKS.md', CORE + 'CHECKS.md', CORE + 'BOUNDARIES.md')),
}


def estimate(text):
    cjk = len(re.findall(r'[　-〿一-鿿＀-￯]', text))
    return cjk + math.ceil((len(text) - cjk) / 3.5)


def entry(mode):
    skill = IOS if mode == 'ios' else GODOT
    agents = setup_project.agents_content('', setup_project.block_for(mode))
    return estimate(agents) + sum(estimate((ROOT / name).read_text()) for name in (skill + 'SKILL.md', CORE + 'WORKFLOW.md'))


def scenario(mode, files):
    return entry(mode) + sum(estimate((ROOT / name).read_text()) for name in files)


class TokenBudgetTests(unittest.TestCase):
    def test_entry_chain_per_mode(self):
        for mode in setup_project.MODE_SKILLS:
            with self.subTest(mode=mode):
                self.assertLessEqual(entry(mode), ENTRY_BUDGET)

    def test_each_routed_document(self):
        for path in sorted((ROOT / '.agents').rglob('*.md')):
            with self.subTest(path=str(path.relative_to(ROOT))):
                self.assertLessEqual(estimate(path.read_text()), FILE_BUDGET)

    def test_typical_scenarios(self):
        for name, (budget, mode, files) in SCENARIOS.items():
            with self.subTest(name):
                self.assertLessEqual(scenario(mode, files), budget)


if __name__ == '__main__':
    for mode in setup_project.MODE_SKILLS:
        print('入口', mode, entry(mode))
    for name, (budget, mode, files) in SCENARIOS.items():
        print(name, scenario(mode, files), '/', budget)
    for path in sorted((ROOT / '.agents').rglob('*.md'), key=lambda p: -estimate(p.read_text()))[:5]:
        print(estimate(path.read_text()), path.relative_to(ROOT))
