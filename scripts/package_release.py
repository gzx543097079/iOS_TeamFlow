#!/usr/bin/env python3
"""按显式清单生成可重复的通用工作流 ZIP，不包含使用项目的数据。"""
import hashlib
import re
import sys
import zipfile
from pathlib import Path
SKILL = '.agents/skills/iOS'
CORE = '.agents/teamflow-core'
CORE_FILES = tuple(CORE + '/' + name for name in (
    'scripts/cli_output.py', 'scripts/cli_parser.py', 'scripts/check_history.py',
    'scripts/diagnostics.py', 'scripts/teamflow_common.py', 'scripts/requirement_model.py',
    'scripts/module_context.py', 'scripts/teamflow.py', 'scripts/project_checks.py', 'scripts/setup_project.py',
    'scripts/upgrade.py',
    'references/WORKFLOW.md', 'references/ARTIFACTS.md', 'references/CHECKS.md', 'references/CHECKS-CONFIG.md', 'references/COMMANDS.md', 'references/REPAIR.md', 'references/BOUNDARIES.md', 'references/INSTALL.md',
    'references/MODULE-CONTEXT.md', 'references/VERSION', 'references/ARCHITECTURE.md', 'references/LOCALIZATION.md',
    'references/templates/requirement.md', 'references/templates/project-context.md', 'references/standards/comments.md',
    'references/REVIEW.md', 'references/DEPENDENCIES.md', 'references/THIRD-PARTY.md', 'assets/ci/github-teamflow.yml',
    'assets/permissions/claude-settings.json', 'assets/permissions/codex.rules',
))
# 可选严格模式模板，仅作为核心资源分发，不在宿主目录自动激活。
PERMISSIONS = {
    '.claude/settings.json': CORE + '/assets/permissions/claude-settings.json',
    '.codex/rules/teamflow.rules': CORE + '/assets/permissions/codex.rules',
}
GODOT_SKILL = '.agents/skills/Godot'
GODOT_FILES = tuple(GODOT_SKILL + '/' + name for name in (
    'SKILL.md', 'references/ENGINE.md', 'references/GDSCRIPT.md',
    'references/CHECKS.md', 'references/IOS.md', 'references/TEAM.md', 'references/RELEASE.md', 'references/PERFORMANCE.md', 'references/TESTING.md',
    'scripts/verify_godot.py', 'scripts/export_ios.py', 'assets/project-checks.example.json',
))
REFERENCES = (
    'APP-RELEASE.md', 'APP-LIFECYCLE.md', 'PERFORMANCE.md', 'UI-REVIEW.md', 'LOGGING.md', 'EXISTING-PROJECT.md', 'ARCHITECTURE.md', 'LOCALIZATION.md', 'DESIGN-TOKENS.md',
    'standards/ui.md', 'standards/ui-keyboard.md', 'standards/ui-paywall.md', 'standards/objective-c.md', 'standards/swift.md', 'standards/swiftui.md',
    'templates/new-project.md', 'templates/feature.md', 'templates/app-release.md',
)
# 仅打包明确登记的通用文件，不打包项目接入记录、需求或日志。
FILES = (
    '.agents/project-checks.json', 'tests/test_review_fixes.py', 'tests/test_verify_speed.py',
    'tests/test_check_triggers.py', 'tests/test_trigger_delivery.py', 'tests/test_verify_wait.py',
    'tests/test_boundaries.py', 'tests/test_diagnostics.py',
    'AGENTS.md', 'README.md', 'CHANGELOG.md', 'docs/RELEASE.md', 'docs/TRIAL.md', '.gitignore',
    '.github/workflows/release.yml',
    'scripts/check_logging.py', 'tests/test_logging_install.py',
    'scripts/teamflow.py', 'scripts/package_release.py', 'scripts/validate_workflow.py', 'scripts/run_workflow_checks.py',
    'tests/release_fixture.py', 'tests/test_consumer_release.py', 'tests/test_workflow.py', 'tests/test_project_checks.py', 'tests/test_teamflow.py', 'tests/test_module_context.py', SKILL + '/SKILL.md',
    SKILL + '/assets/logging/TFLogger.swift', SKILL + '/assets/logging/TFLogger.h', SKILL + '/assets/logging/TFLogger.m',
    SKILL + '/scripts/install_logging.py', SKILL + '/scripts/check_design_tokens.py', 'tests/test_design_tokens.py',
) + tuple(SKILL + '/references/' + name for name in REFERENCES) + CORE_FILES + GODOT_FILES + (
    'docs/GODOT.md', 'tests/test_godot_extension.py', 'tests/test_godot_export.py', 'tests/test_upgrade.py', 'tests/test_team.py', 'tests/test_token_budget.py',
)


def write_package(root, prefix, entries, generated=None, output=None):
    """entries 映射仓库文件到包内路径；generated 为打包时生成的包内文件；output 默认为仓库 dist/。"""
    root = root.resolve()
    version = (root / CORE / 'references/VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('VERSION 必须为 X.Y.Z')
    for name in entries:
        path = root / name
        if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('分发文件缺失或包含符号链接：' + name)
        if not path.resolve().is_relative_to(root):
            raise ValueError('文件越出项目目录：' + name)
    contents = {destination: (root / name).read_bytes() for name, destination in entries.items()}
    contents.update(generated or {})
    output = Path(output) if output else root / 'dist'
    output.mkdir(parents=True, exist_ok=True)
    archive = output / (prefix + version + '.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as stream:
        for destination, data in sorted(contents.items()):
            entry = zipfile.ZipInfo(destination, date_time=(2020, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            stream.writestr(entry, data)
    archive.with_suffix('.zip.sha256').write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')
    return archive


def clean_dist(root):
    """仅移除 dist/ 中非当前版本的压缩包与校验文件，避免误取旧包；其他文件不动。"""
    version = (root / CORE / 'references/VERSION').read_text().strip()
    output = root / 'dist'
    current = ('-v' + version + '.zip', '-v' + version + '.zip.sha256')
    removed = []
    for path in sorted(output.glob('*')) if output.is_dir() else []:
        if path.is_file() and path.name.endswith(('.zip', '.zip.sha256')) and not path.name.endswith(current):
            path.unlink()
            removed.append(path.name)
    return removed


def package(root, output=None):
    return write_package(root, 'TeamFlow-v', {name: name for name in FILES}, output=output)


def package_mode(root, mode, output=None):
    """解压到项目根即可使用：含核心、所选 Skill、入口脚本、对应模式的 AGENTS、宿主权限与安装清单。"""
    root = root.resolve()
    sys.path.insert(0, str(root / CORE / 'scripts'))
    import setup_project
    import upgrade
    skills = tuple('.agents/skills/' + name + '/' for name in setup_project.MODE_SKILLS[mode])
    entries = {name: name for name in FILES if name.startswith((CORE + '/',) + skills)}
    files = {name: (root / name).read_bytes() for name in entries}
    version = (root / CORE / 'references/VERSION').read_text().strip()
    generated = {
        'AGENTS.md': setup_project.agents_content('', setup_project.block_for(mode)).encode(),
        'scripts/teamflow.py': setup_project.ENTRY.encode(),
        upgrade.MANIFEST: upgrade.manifest_text(version, mode, files).encode(),
    }
    return write_package(root, 'teamflow-' + mode + '-v', entries, generated, output)


def package_skill(root, output=None):
    return package_mode(root, 'ios', output)


def package_godot(root, output=None):
    return package_mode(root, 'godot', output)


def package_godot_ios(root, output=None):
    """含 iOS 的 Godot 包；跨 Skill 引用在解压后仍然有效。"""
    return package_mode(root, 'godot-ios', output)


if __name__ == '__main__':
    ROOT = Path(__file__).resolve().parents[1]
    for name in clean_dist(ROOT):
        print('已移除旧包：' + name)
    for build in (package, package_skill, package_godot, package_godot_ios):
        print(build(ROOT))
