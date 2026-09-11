#!/usr/bin/env python3
"""完整独立 Skill ZIP 升级：默认预览，三方合并，显式应用并记录完整恢复事务。"""
import argparse
import base64
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import re
from pathlib import Path, PurePosixPath
import stat
import subprocess
import sys
import tempfile
import zipfile

PREFIX = '.agents/skills/ios-team-flow/'
BASELINE = '.agents/teamflow-skill-baseline.json'
ENTRY_FILES = ('AGENTS.md', 'AGENTS.override.md', '.agents/teamflow.json', 'scripts/review_gate.py')
spec = importlib.util.spec_from_file_location('teamflow_setup', Path(__file__).with_name('setup_project.py'))
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


def digest(data):
    return None if data is None else hashlib.sha256(data).hexdigest()


def safe(root, name):
    path = root / name
    for node in (path, *path.parents):
        if node == root:
            break
        if node.is_symlink():
            raise ValueError('升级路径不能含符号链接：' + name)
        if node != path and node.exists() and not node.is_dir():
            raise ValueError('升级父路径不是目录：' + name)
    return path


def archive_files(archive):
    result = {}
    with zipfile.ZipFile(archive) as source:
        size = 0
        for entry in source.infolist():
            name = PurePosixPath(entry.filename)
            mode = entry.external_attr >> 16
            if (name.is_absolute() or '..' in name.parts or not name.parts
                    or name.parts[0] != 'ios-team-flow' or '\\' in entry.filename):
                raise ValueError('必须是独立 Skill 包，且不能含越界路径')
            if entry.is_dir():
                continue
            if stat.S_IFMT(mode) not in (0, stat.S_IFREG):
                raise ValueError('压缩包仅允许普通文件')
            relative = '/'.join(name.parts[1:])
            if not relative or relative in result:
                raise ValueError('压缩包含重复或无效路径')
            size += entry.file_size
            if size > 32 * 1024 * 1024 or len(result) >= 2000:
                raise ValueError('Skill 包超过大小或文件数限制')
            result[relative] = source.read(entry)
    required = {'SKILL.md', 'references/VERSION', 'scripts/setup_project.py', 'scripts/review_gate.py'}
    if not required <= result.keys():
        raise ValueError('Skill 包不完整')
    setup.version_tuple(result['references/VERSION'].decode().strip())
    return result


def installed_files(root):
    folder = safe(root, PREFIX.rstrip('/'))
    if not folder.is_dir():
        raise ValueError('请先在当前项目安装 Skill；此命令用于完整升级')
    result = {}
    for path in folder.rglob('*'):
        if '__pycache__' in path.parts or path.suffix == '.pyc':
            continue
        safe(root, str(path.relative_to(root)))
        if path.is_file():
            result[str(path.relative_to(folder))] = path.read_bytes()
        elif not path.is_dir():
            raise ValueError('Skill 含非普通文件')
    return result


@contextmanager
def upgrade_lock(root):
    lock = safe(root, '.agents/teamflow-upgrade.lock')
    try:
        lock.mkdir()
    except FileExistsError as error:
        raise ValueError('升级锁已存在；确认无其他升级进程并处理未完成恢复后移除该空锁目录') from error
    try:
        yield
    finally:
        lock.rmdir()


def upgrade(root, archive, base_archive=None, apply=False, resolutions=None):
    root = root.expanduser().resolve()
    safe(root, '.agents/teamflow-backups')
    with upgrade_lock(root):
        for journal in (root / '.agents/teamflow-backups').glob('upgrade-*/transaction.json'):
            safe(root, str(journal.relative_to(root)))
            if json.loads(journal.read_text()).get('state') == 'prepared':
                raise ValueError('存在未完成事务，请先 --recover ' + str(journal))
        current = installed_files(root)
        upstream = archive_files(archive)
        old_version = current['references/VERSION'].decode().strip()
        version = upstream['references/VERSION'].decode().strip()
        if setup.version_tuple(version) < setup.version_tuple(old_version):
            raise ValueError('不允许自动降级')
        baseline_path = safe(root, BASELINE)
        if base_archive:
            base = archive_files(base_archive)
            if base['references/VERSION'].decode().strip() != old_version:
                raise ValueError('旧版原包版本与当前 Skill 不一致')
            baseline = {name: digest(data) for name, data in base.items()}
        elif baseline_path.exists():
            record = json.loads(baseline_path.read_text())
            if record.get('schema_version') != 1 or record.get('version') != old_version or not isinstance(record.get('files'), dict):
                raise ValueError('Skill 基线版本或格式不匹配')
            baseline = record['files']
        else:
            raise ValueError('首次完整升级需要 --base-archive 当前版本的原始独立 Skill ZIP，不能用定制目录冒充基线')
        if any(not isinstance(name, str) or '..' in PurePosixPath(name).parts or PurePosixPath(name).is_absolute()
               or not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{64}', value) for name, value in baseline.items()):
            raise ValueError('Skill 基线文件路径或哈希无效')
        merged, conflicts, changes, resolved = {}, [], [], []
        for name in sorted(set(current) | set(upstream) | set(baseline)):
            local, new = current.get(name), upstream.get(name)
            old_hash = baseline.get(name)
            if local == new or digest(local) == old_hash:
                value = new
            elif digest(new) == old_hash:
                value = local
            else:
                resolution = safe(resolutions.resolve(), name) if resolutions else None
                if resolution is None or not resolution.is_file():
                    conflicts.append(name)
                    continue
                value = resolution.read_bytes()
                resolved.append(name)
            if value is not None:
                merged[name] = value
            if value != local:
                changes.append({'path': name, 'action': '删除' if value is None else '新增' if local is None else '更新'})
        print(json.dumps({'from': old_version, 'to': version, 'changes': changes, 'conflicts': conflicts, 'resolved': resolved}, ensure_ascii=False, indent=2))
        if conflicts:
            raise ValueError('团队与新版同时修改上述文件；未写入项目文件。在副本中合并后用 --resolutions 指定合并目录，不强制覆盖')
        # 新版本的 setup 在临时项目中生成计划；源包是用户选定的可执行代码，应先核对发布校验和。
        originals = {name: safe(root, name).read_bytes() if safe(root, name).exists() else None for name in ENTRY_FILES}
        with tempfile.TemporaryDirectory(prefix='teamflow-upgrade-plan-') as directory:
            shadow = Path(directory)
            for name, value in {**{PREFIX + n: b for n, b in merged.items()}, **originals}.items():
                if value is not None:
                    target = shadow / name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(value)
            result = subprocess.run([sys.executable, str(shadow / PREFIX / 'scripts/setup_project.py'),
                                     '--project', str(shadow), '--plan'], capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise ValueError('新版接入预检失败：' + result.stderr.strip())
            planned = json.loads(result.stdout)
            if not isinstance(planned, dict) or not set(planned) <= set(ENTRY_FILES):
                raise ValueError('新版接入计划包含不允许的目标')
            planned = {name: base64.b64decode(value, validate=True) for name, value in planned.items()}
        print('入口计划：' + ', '.join(sorted(planned)))
        if not apply:
            print('仅预览；核对差异后加 --apply 执行。')
            return None
        before = {PREFIX + name: data for name, data in current.items()}
        before.update(originals)
        before[BASELINE] = baseline_path.read_bytes() if baseline_path.exists() else None
        after = {PREFIX + name: data for name, data in merged.items()}
        after.update(originals)
        after.update(planned)
        after[BASELINE] = (json.dumps({'schema_version': 1, 'version': version,
                                     'files': {name: digest(data) for name, data in upstream.items()}}, indent=2) + '\n').encode()
        names = set(before) | set(after)
        # 完整快照包含未变化的 Skill 和入口，恢复时一并核对后续人工修改。
        before = {name: before.get(name) for name in names}
        after = {name: after.get(name) for name in names}
        for name in names:
            target = safe(root, name)
            actual = target.read_bytes() if target.exists() else None
            if actual != before[name]:
                raise ValueError('预检过程中项目文件发生变化，停止升级：' + name)
        if before == after:
            print('当前内容与升级结果一致，无需写入。')
            return None
        backup = setup.apply_transaction(root, after, before)
        print('完整备份及恢复记录：' + str(backup / 'transaction.json'))
        return backup


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, required=True)
    parser.add_argument('--archive', type=Path, required=True)
    parser.add_argument('--base-archive', type=Path)
    parser.add_argument('--resolutions', type=Path, help='显式采用的人工合并文件目录，保持 Skill 内相对路径')
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        upgrade(args.project, args.archive, args.base_archive, args.apply, args.resolutions)
    except (ValueError, OSError, KeyError, TypeError, zipfile.BadZipFile, subprocess.TimeoutExpired) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    main()
