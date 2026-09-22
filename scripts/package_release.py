#!/usr/bin/env python3
"""按显式清单生成可重复的通用工作流 ZIP，不包含使用项目的数据。"""
import hashlib
import re
import zipfile
from pathlib import Path
SKILL = '.agents/skills/ios-team-flow'
REFERENCES = (
    'LOGGING.md', 'ARCHITECTURE.md', 'APP-LIFECYCLE.md', 'EVOLUTION.md', 'SCENARIOS.md', 'APP-RELEASE.md', 'templates/app-release.md', 'ACCEPTANCE.md', 'templates/acceptance.md', 'VERSION', 'README.md', 'CHANGELOG.md', 'WORKFLOW.md', 'REVIEW.md',
    'RELEASE.md', 'SOURCES.md', 'INSTALL.md', 'standards/ui.md',
    'standards/comments.md', 'standards/objective-c.md', 'standards/swift.md', 'standards/swiftui.md',
    'templates/new-project.md', 'templates/requirement.md', 'templates/lightweight.md', 'BUGFIX.md', 'templates/bug-fix.md',
    'GIT-CHECKS.md', 'DELIVERY.md', 'PROJECT-CHECKS.md', 'EXISTING-PROJECT.md', 'MODULE-CONTEXT.md', 'templates/project-context.md',
)
# 仅打包明确登记的通用文件，不打包项目接入记录、需求或日志。
FILES = (
    'AGENTS.md', 'README.md', '.gitignore',
    '.github/workflows/teamflow-check.yml', '.github/workflows/teamflow-release.yml',
    'scripts/check_logging.py', '.github/workflows/teamflow-logging.yml', 'tests/test_logging_install.py',
    'scripts/review_gate.py', 'scripts/package_release.py', 'scripts/validate_workflow.py', 'scripts/run_workflow_checks.py',
    'tests/test_check_selection.py', 'tests/test_consumer_release.py', 'tests/test_skill_upgrade.py', 'tests/test_scenarios.py', 'tests/test_setup_recovery.py', 'tests/test_workflow.py', 'tests/test_project_checks.py', 'tests/test_delivery.py', 'tests/test_git_checks.py', 'tests/test_module_context.py', SKILL + '/SKILL.md',
    SKILL + '/assets/logging/TFLogger.swift', SKILL + '/assets/logging/TFLogger.h', SKILL + '/assets/logging/TFLogger.m',
    SKILL + '/scripts/install_logging.py',
    SKILL + '/scripts/upgrade_skill.py', SKILL + '/scripts/install_git_checks.py', SKILL + '/scripts/module_context.py', SKILL + '/scripts/delivery.py', SKILL + '/scripts/project_checks.py', SKILL + '/scripts/setup_project.py', SKILL + '/scripts/review_gate.py',
) + tuple(SKILL + '/references/' + name for name in REFERENCES)


def package(root):
    root = root.resolve()
    version = (root / SKILL / 'references/VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('VERSION 必须为 X.Y.Z')
    for name in FILES:
        path = root / name
        if not path.is_file() or any(p.is_symlink() for p in [path, *path.parents] if p != root.parent):
            raise ValueError('分发文件缺失或包含符号链接：' + name)
        if not path.resolve().is_relative_to(root):
            raise ValueError('文件越出项目目录：' + name)
    output = root / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / ('iOS-TeamFlow-v' + version + '.zip')
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED) as stream:
        for name in sorted(FILES):
            entry = zipfile.ZipInfo(name, date_time=(2020, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            stream.writestr(entry, (root / name).read_bytes())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    archive.with_suffix('.zip.sha256').write_text(checksum + '  ' + archive.name + '\n')
    print(archive)
    return archive


def package_skill(root):
    root = root.resolve()
    version = (root / SKILL / 'references/VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('VERSION 必须为 X.Y.Z')
    output = root / 'dist'
    output.mkdir(exist_ok=True)
    archive = output / ('ios-team-flow-skill-v' + version + '.zip')
    names = sorted(name for name in FILES if name.startswith(SKILL + '/'))
    for name in names:
        path = root / name
        if not path.is_file() or any(p.is_symlink() for p in (path, *path.parents)):
            raise ValueError('Skill 文件缺失或含符号链接：' + name)
    with zipfile.ZipFile(archive, 'w') as stream:
        for name in names:
            entry = zipfile.ZipInfo('ios-team-flow/' + name[len(SKILL) + 1:],
                                    date_time=(2020, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.create_system = 3
            entry.external_attr = 0o100644 << 16
            stream.writestr(entry, (root / name).read_bytes())
    archive.with_suffix('.zip.sha256').write_text(
        hashlib.sha256(archive.read_bytes()).hexdigest() + '  ' + archive.name + '\n')
    print(archive)
    return archive


if __name__ == '__main__':
    package(Path(__file__).resolve().parents[1])
    package_skill(Path(__file__).resolve().parents[1])
