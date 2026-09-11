#!/usr/bin/env python3
"""从仓库单一规范源生成独立 Skill 的资源快照；--check 检测漂移。"""
import argparse
from pathlib import Path

SKILL = '.agents/skills/ios-team-flow'
SOURCES = (
    'WORKFLOW.md', 'REVIEW.md', 'SOURCES.md', 'VERSION',
    'standards/ui.md', 'standards/objective-c.md', 'standards/swift.md',
    'standards/swiftui.md', 'templates/new-project.md', 'templates/requirement.md',
)


def expected(root):
    result = {}
    for name in SOURCES:
        content = (root / 'workflow' / name).read_text()
        # 独立 Skill 中的资料根与项目产物根不能混淆。
        content = content.replace('workflow/', '<SKILL_ROOT>/references/')
        content = content.replace('[发布规程](RELEASE.md)', '[安装说明](INSTALL.md)')
        result['references/' + name] = content.encode()
    result['scripts/review_gate.py'] = (root / 'scripts/review_gate.py').read_bytes()
    return result


def build(root, check=False):
    for name, content in expected(root).items():
        target = root / SKILL / name
        if check:
            if not target.is_file() or target.read_bytes() != content:
                raise ValueError('Skill 资源未同步，运行 python3 scripts/build_skill.py：' + name)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    print('独立 Skill 资源检查通过' if check else '独立 Skill 资源已同步')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    build(Path(__file__).resolve().parents[1], parser.parse_args().check)
