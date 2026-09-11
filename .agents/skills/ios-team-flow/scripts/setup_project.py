#!/usr/bin/env python3
"""将已安装 Skill 接入指定项目，预检冲突并保留既有文件。"""
import argparse
import base64
import os
import json
import hashlib
import re
import tempfile
from pathlib import Path

START = '<!-- ios-team-flow:start -->'
END = '<!-- ios-team-flow:end -->'
BLOCK = '''<!-- ios-team-flow:start -->
## iOS 团队工作流

本项目采用仓库内的 `.agents/skills/ios-team-flow/SKILL.md`。实施 iOS 需求和提交前必须读取该文件，无需用户再次点名 Skill；按 OC / Swift / SwiftUI / UI 类型加载规范，维护 requirements/ 需求过程与 logs/ 审查记录。
新产品先整理 PRD 交团队确认。提交前只 review 本次改动，相同有效指纹复用；运行 `python3 scripts/review_gate.py check`。未经授权不提交或发布。
版本见 .agents/teamflow.json，Skill 与项目一起提交和克隆，不依赖用户级安装。找不到本地 Skill 时明确报告缺失，不自动改用其他项目或用户级同名版本。遵守项目现有具体约定，有冲突先说明。
<!-- ios-team-flow:end -->
'''


GATE_ENTRY = '#!/usr/bin/env python3\n"""从项目内 Skill 加载审查门禁，唯一实现维护在 Skill 内。"""\nimport runpy\nfrom pathlib import Path\n\n_source = Path(__file__).resolve().parents[1] / \'.agents/skills/ios-team-flow/scripts/review_gate.py\'\nglobals().update(runpy.run_path(str(_source), run_name=__name__))\n'

# 已发布 1.2.1 的托管内容指纹；仅用于没有基线的旧接入记录。
LEGACY_121 = {'agents_block': '2ed1594fbeb374590c3ecd0cca48910b7f86726acc3204ce1634d5a58e6f9a8e', 'gate_entry': '1c6e0ee2a0554883d7fd1ce35b4f93a3dccb3d4a7aabe9aa8fecabdd9124db94'}


def digest(content):
    return hashlib.sha256(content.encode()).hexdigest()


def version_tuple(value):
    if not isinstance(value, str) or not re.fullmatch(r'\d+\.\d+\.\d+', value):
        raise ValueError('版本必须为 X.Y.Z')
    return tuple(map(int, value.split('.')))


MANAGED_FILES = {'.agents/teamflow.json', 'scripts/review_gate.py', 'AGENTS.md', 'AGENTS.override.md', '.agents/teamflow-skill-baseline.json'}


def managed_name(name):
    if not isinstance(name, str) or Path(name).is_absolute() or '..' in Path(name).parts:
        return False
    return name in MANAGED_FILES or name.startswith('.agents/skills/ios-team-flow/')


def atomic_write(path, content, mode=0o644):
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.teamflow-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def recover(project, journal_path):
    project = project.expanduser().resolve()
    journal_path = journal_path.absolute()
    expected = project / '.agents/teamflow-backups'
    if not journal_path.resolve().is_relative_to(expected):
        raise ValueError('恢复记录必须位于本项目 .agents/teamflow-backups')
    for node in (journal_path, *journal_path.parents):
        if node == project:
            break
        if node.is_symlink():
            raise ValueError('恢复路径不允许符号链接')
    data = json.loads(journal_path.read_text())
    if (data.get('schema') != 1 or data.get('project') != str(project)
            or not isinstance(data.get('files'), dict) or not data['files']
            or not all(managed_name(name) for name in data['files'])):
        raise ValueError('恢复记录无效或属于其他项目')
    originals = {}
    # 在任何恢复写入之前核对所有文件，拒绝覆盖升级后的人工修改。
    for name, entry in data['files'].items():
        target = project / name
        for node in (target, *target.parents):
            if node == project:
                break
            if node.is_symlink():
                raise ValueError('恢复目标包含符号链接：' + name)
        old = None if entry['before'] is None else base64.b64decode(entry['before'], validate=True)
        new = None if entry['after'] is None else base64.b64decode(entry['after'], validate=True)
        mode = entry['mode']
        if type(mode) is not int or not 0 <= mode <= 0o777:
            raise ValueError('恢复权限无效')
        current = target.read_bytes() if target.exists() else None
        if current != old and current != new:
            raise ValueError('恢复冲突，文件已有其他修改：' + name)
        originals[name] = (old, mode)
    for name, (old, mode) in originals.items():
        target = project / name
        if old is None:
            target.unlink(missing_ok=True)
        else:
            atomic_write(target, old, mode)
    data['state'] = 'restored'
    atomic_write(journal_path, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode(), 0o600)
    print('已恢复接入前托管文件：' + str(journal_path))


def apply_transaction(project, changed, before):
    if not changed:
        return None
    backup_root = project / '.agents/teamflow-backups'
    backup_root.mkdir(parents=True, exist_ok=True)
    backup = Path(tempfile.mkdtemp(prefix='upgrade-', dir=backup_root))
    journal = backup / 'transaction.json'
    files = {}
    for name, content in changed.items():
        target = project / name
        mode = (target.stat().st_mode & 0o777) if target.exists() else 0o644
        files[name] = {'before': None if before[name] is None else base64.b64encode(before[name]).decode(),
                       'after': None if content is None else base64.b64encode(content).decode(), 'mode': mode}
        if before[name] is not None:
            saved = backup / name
            atomic_write(saved, before[name], mode)
    data = {'schema': 1, 'project': str(project), 'state': 'prepared', 'files': files}
    atomic_write(journal, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode(), 0o600)
    try:
        for name, content in changed.items():
            if content is None:
                (project / name).unlink(missing_ok=True)
            else:
                atomic_write(project / name, content, files[name]['mode'])
        for name in ('requirements', 'logs/reviews'):
            (project / name).mkdir(parents=True, exist_ok=True)
        data['state'] = 'applied'
        atomic_write(journal, (json.dumps(data, ensure_ascii=False, indent=2) + '\n').encode(), 0o600)
    except OSError as error:
        try:
            recover(project, journal)
        except (OSError, ValueError) as rollback_error:
            raise OSError(f'接入失败：{error}；自动恢复失败：{rollback_error}；修复原因后使用 --recover {journal}') from error
        raise OSError(f'接入失败，托管文件已恢复：{error}；记录：{journal}') from error
    return backup


def setup(project, skill, dry_run=False):
    project = project.expanduser().resolve()
    skill = skill.resolve()
    local_skill = project / '.agents/skills/ios-team-flow'
    if skill != local_skill or any(node.is_symlink() for node in
                                   (local_skill, local_skill.parent, local_skill.parent.parent)):
        raise ValueError('请先将完整 Skill 放入目标项目的 .agents/skills/ios-team-flow，再运行该项目内的接入脚本')
    version = (skill / 'references/VERSION').read_text().strip()
    version_tuple(version)
    manifest_name = '.agents/teamflow.json'
    gate_name = 'scripts/review_gate.py'
    override = project / 'AGENTS.override.md'
    if override.is_symlink():
        raise ValueError('AGENTS.override.md 不能为符号链接')
    agents_name = 'AGENTS.override.md' if override.exists() and override.stat().st_size > 0 else 'AGENTS.md'
    names = (manifest_name, gate_name, agents_name)
    conflicts = []
    for name in (*names, 'requirements', 'logs/reviews', '.agents/teamflow-backups'):
        path = project / name
        for node in (path, *path.parents):
            if node == project:
                break
            if node.is_symlink():
                conflicts.append(name + ' 路径包含符号链接')
        for parent in path.parents:
            if parent == project:
                break
            if parent.exists() and not parent.is_dir():
                conflicts.append(name + ' 的父路径不是目录')
        if path.exists() and (not path.is_file() if name in names else not path.is_dir()):
            conflicts.append(name + ' 类型不正确')
    if conflicts:
        raise ValueError('接入前预检发现冲突，未写入文件：\n' + '\n'.join(sorted(set(conflicts))))
    for journal in (project / '.agents/teamflow-backups').glob('upgrade-*/transaction.json'):
        if json.loads(journal.read_text()).get('state') == 'prepared':
            raise ValueError('发现中断的接入，请先使用 --recover ' + str(journal))
    before = {name: (project / name).read_bytes() if (project / name).exists() else None
              for name in names}
    manifest = {}
    baseline = {}
    if before[manifest_name] is not None:
        try:
            manifest = json.loads(before[manifest_name])
            if not isinstance(manifest, dict) or manifest.get('skill') != 'ios-team-flow':
                raise ValueError('不是 ios-team-flow 的项目记录')
            if version_tuple(manifest.get('version')) > version_tuple(version):
                raise ValueError('不自动降级，请恢复匹配版本的 Skill')
            if 'managed' in manifest:
                baseline = manifest['managed']
                if (manifest.get('schema_version') != 1 or not isinstance(baseline, dict)
                        or set(baseline) != {'agents_block', 'gate_entry'}
                        or any(not isinstance(v, str) or not re.fullmatch(r'[0-9a-f]{64}', v)
                               for v in baseline.values())):
                    raise ValueError('托管基线无效，请从项目 Git 历史恢复接入记录')
            elif manifest.get('version') == '1.2.1':
                baseline = LEGACY_121
            else:
                raise ValueError('旧接入记录没有可识别的基线，请先人工核对托管文件')
        except (ValueError, TypeError) as error:
            raise ValueError('接入前预检发现冲突，未写入文件：' + manifest_name + '：' + str(error)) from error
    old = before[agents_name].decode() if before[agents_name] is not None else ''
    updated = old
    if START in old or END in old:
        if old.count(START) != 1 or old.count(END) != 1 or old.index(START) >= old.index(END):
            conflicts.append('AGENTS.md 托管标记缺失、重复或顺序错误，请恢复成对标记')
        else:
            start, end = old.index(START), old.index(END) + len(END)
            current = old[start:end]
            if digest(BLOCK.strip()) == baseline.get('agents_block'):
                pass  # 新版未改此区块，保留团队定制。
            elif current != BLOCK.strip() and digest(current) != baseline.get('agents_block'):
                conflicts.append('AGENTS.md 托管区块有团队修改，请合并到新版区块；区块外规则会保留')
            else:
                updated = old[:start] + BLOCK.strip() + old[end:]
    elif baseline and manifest.get('instruction_file', 'AGENTS.md') == agents_name:
        conflicts.append(agents_name + ' 托管区块已被移除，请恢复后重试')
    else:
        updated = old + ('\n\n' if old else '') + BLOCK
    current_gate = before[gate_name]
    desired_gate = GATE_ENTRY.encode()
    if current_gate is not None:
        if digest(GATE_ENTRY) == baseline.get('gate_entry'):
            desired_gate = current_gate  # 新版入口未变，保留团队定制。
        elif current_gate != GATE_ENTRY.encode() and hashlib.sha256(current_gate).hexdigest() != baseline.get('gate_entry'):
            conflicts.append(gate_name + ' 有团队修改或来源未知，请合并新版入口后重试')
    elif baseline:
        conflicts.append(gate_name + ' 已被移除，请恢复后重试')
    if conflicts:
        raise ValueError('接入前预检发现冲突，未写入文件：\n' + '\n'.join(conflicts))
    # 保留接入记录中的其他团队字段，只更新本工具拥有的字段。
    manifest.update(skill='ios-team-flow', version=version, schema_version=1, instruction_file=agents_name,
                    managed={'agents_block': digest(BLOCK.strip()), 'gate_entry': digest(GATE_ENTRY)})
    planned = {manifest_name: (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode(),
               gate_name: desired_gate, agents_name: updated.encode()}
    changed = {name: data for name, data in planned.items() if data != before[name]}
    if dry_run:
        return planned
    backup = apply_transaction(project, changed, before)
    for name in ('requirements', 'logs/reviews'):
        (project / name).mkdir(parents=True, exist_ok=True)
    print('项目已接入 ios-team-flow ' + version + '：' + str(project))
    if backup:
        print('升级前文件备份：' + str(backup))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', required=True, type=Path)
    parser.add_argument('--plan', action='store_true', help='只输出接入计划，不写入文件')
    parser.add_argument('--recover', type=Path, help='恢复本项目 transaction.json 中的接入前托管文件')
    args = parser.parse_args()
    try:
        if args.recover:
            recover(args.project, args.recover)
        else:
            planned = setup(args.project, Path(__file__).resolve().parents[1], dry_run=args.plan)
            if args.plan:
                print(json.dumps({name: base64.b64encode(data).decode() for name, data in planned.items()}))
    except (ValueError, OSError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')
