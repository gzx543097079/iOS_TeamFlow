#!/usr/bin/env python3
"""按显式清单生成可重复的通用工作流 ZIP，不包含使用项目的数据。"""
import hashlib
import re
import zipfile
from pathlib import Path
SKILL = '.agents/skills/ios-team-flow'
REFERENCES = (
    'COMMANDS.md', 'DATA-MIGRATION.md', 'SECURITY-BOUNDARIES.md',
    'LOGGING.md', 'LOCALIZATION.md', 'ARCHITECTURE.md', 'APP-LIFECYCLE.md', 'EVOLUTION.md', 'SCENARIOS.md', 'APP-RELEASE.md', 'templates/app-release.md', 'VERSION', 'CHANGELOG.md', 'WORKFLOW.md', 'GIT-ACTIONS.md',
    'RELEASE.md', 'SOURCES.md', 'INSTALL.md', 'standards/ui.md',
    'standards/comments.md', 'standards/objective-c.md', 'standards/swift.md', 'standards/swiftui.md',
    'templates/new-project.md', 'templates/feature.md', 'templates/requirement.md', 'BUGFIX.md',
    'PROJECT-CHECKS.md', 'EXISTING-PROJECT.md', 'MODULE-CONTEXT.md', 'templates/project-context.md',
)
# 仅打包明确登记的通用文件，不打包项目接入记录、需求或日志。
FILES = (
    'tests/test_boundaries.py', 'tests/test_diagnostics.py', SKILL + '/scripts/diagnostics.py',
    'AGENTS.md', 'README.md', '.gitignore',
    '.github/workflows/teamflow-check.yml', '.github/workflows/teamflow-release.yml',
    'scripts/check_logging.py', '.github/workflows/teamflow-logging.yml', 'tests/test_logging_install.py',
    'scripts/teamflow.py', 'scripts/package_release.py', 'scripts/validate_workflow.py', 'scripts/run_workflow_checks.py',
    'tests/release_fixture.py', 'tests/test_consumer_release.py', 'tests/test_workflow.py', 'tests/test_project_checks.py', 'tests/test_teamflow.py', 'tests/test_module_context.py', SKILL + '/SKILL.md',
    SKILL + '/assets/logging/TFLogger.swift', SKILL + '/assets/logging/TFLogger.h', SKILL + '/assets/logging/TFLogger.m',
    SKILL + '/scripts/install_logging.py', SKILL + '/scripts/teamflow_common.py', SKILL + '/scripts/requirement_model.py',
    SKILL + '/scripts/module_context.py', SKILL + '/scripts/teamflow.py', SKILL + '/scripts/project_checks.py', SKILL + '/scripts/setup_project.py',
) + tuple(SKILL + '/references/' + name for name in REFERENCES)


def write_package(root, prefix, entries):
    root = root.resolve()
    version = (root / SKILL / 'references/VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('VERSION 必须为 X.Y.Z')
    for name in entries:
        path = root / name
        if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('分发文件缺失或包含符号链接：' + name)
        if not path.resolve().is_relative_to(root):
            raise ValueError('文件越出项目目录：' + name)
    output = root / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / (prefix + version + '.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as stream:
        for name, destination in sorted(entries.items()):
            entry = zipfile.ZipInfo(destination, date_time=(2020, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            stream.writestr(entry, (root / name).read_bytes())
    archive.with_suffix('.zip.sha256').write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')
    print(archive)
    return archive


def package(root):
    return write_package(root, 'iOS-TeamFlow-v', {name: name for name in FILES})


def package_skill(root):
    return write_package(root, 'ios-team-flow-skill-v', {
        name: 'ios-team-flow/' + name[len(SKILL) + 1:]
        for name in FILES if name.startswith(SKILL + '/')})


if __name__ == '__main__':
    package(Path(__file__).resolve().parents[1])
    package_skill(Path(__file__).resolve().parents[1])
