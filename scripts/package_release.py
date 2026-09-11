#!/usr/bin/env python3
"""按显式清单生成可重复的通用工作流 ZIP，不包含使用项目的数据。"""
import hashlib
import re
import zipfile
from pathlib import Path
from build_skill import SKILL, SOURCES, build

# 新增分发文件需显式登记，避免误打包消费项目的业务脚本或私有文档。
FILES = (
    'AGENTS.md', '.gitignore',
    '.agents/skills/ios-team-flow/SKILL.md',
    '.github/pull_request_template.md',
    '.github/workflows/teamflow-check.yml', '.github/workflows/teamflow-release.yml',
    'workflow/VERSION', 'workflow/README.md', 'workflow/CHANGELOG.md',
    'workflow/WORKFLOW.md', 'workflow/REVIEW.md', 'workflow/RELEASE.md', 'workflow/SOURCES.md',
    'workflow/standards/ui.md', 'workflow/standards/objective-c.md',
    'workflow/standards/swift.md', 'workflow/standards/swiftui.md',
    'workflow/templates/new-project.md', 'workflow/templates/requirement.md',
    'scripts/review_gate.py', 'scripts/package_release.py', 'scripts/validate_workflow.py',
    'tests/test_workflow.py',
)
FILES += ('scripts/build_skill.py', SKILL + '/scripts/setup_project.py',
          SKILL + '/scripts/review_gate.py', SKILL + '/references/INSTALL.md')
FILES += tuple(SKILL + '/references/' + name for name in SOURCES)


def package(root):
    root = root.resolve()
    version = (root / 'workflow/VERSION').read_text().strip()
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
    build(root, check=True)
    version = (root / 'workflow/VERSION').read_text().strip()
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
