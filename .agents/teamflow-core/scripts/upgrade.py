"""按安装清单升级项目内核心与所选 Skill；本地改动不静默覆盖，团队定制层、需求和配置不触碰。"""
import hashlib
import json
import stat
import subprocess
import sys
import zipfile
from pathlib import Path
from teamflow_common import local_path as safe
import setup_project

CORE = '.agents/teamflow-core'
MANIFEST = CORE + '/references/MANIFEST.json'


def digest(data):
    return 'sha256:' + hashlib.sha256(data).hexdigest()


def version_key(value):
    setup_project.validate_version(value)
    return tuple(int(part) for part in value.split('.'))


def read_package(path):
    """读取安装包中的核心与 Skill 文件；兼容 5.x 解压到 .agents/ 的布局。"""
    path = Path(path).expanduser()
    if not path.is_file():
        raise ValueError('安装包不存在：' + str(path))
    try:
        return _read_package(path)
    except zipfile.BadZipFile:
        raise ValueError('安装包不是有效 ZIP：' + str(path))


def _read_package(path):
    with zipfile.ZipFile(path) as stream:
        infos = [info for info in stream.infolist() if not info.is_dir()]
        names = [info.filename for info in infos]
        prefix = '' if any(name.startswith('.agents/') for name in names) else '.agents/'
        files, manifest = {}, None
        for info in infos:
            name = prefix + info.filename
            if Path(name).is_absolute() or '..' in Path(name).parts or '\\' in name:
                raise ValueError('安装包包含不安全路径：' + info.filename)
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError('安装包包含符号链接：' + info.filename)
            if name == MANIFEST:
                manifest = json.loads(stream.read(info))
            elif name.startswith((CORE + '/', '.agents/skills/')):
                files[name] = stream.read(info)
    if CORE + '/references/VERSION' not in files:
        raise ValueError('不是 TeamFlow 安装包：缺少共用核心 VERSION')
    version = files[CORE + '/references/VERSION'].decode().strip()
    version_key(version)
    skills = sorted({name.split('/')[2] for name in files if name.startswith('.agents/skills/')})
    return {'version': version, 'skills': skills, 'files': files,
            'package': (manifest or {}).get('package')}


def mode_files(package, mode):
    """只取当前模式需要的核心与 Skill，含 iOS 的包也可用于纯 Godot 项目。"""
    needed = setup_project.MODE_SKILLS[mode]
    missing = [name for name in needed if name not in package['skills']]
    if missing:
        raise ValueError('安装包不含当前模式（' + setup_project.MODE_LABELS[mode] + '）所需 Skill：'
                         + '、'.join(missing))
    scope = (CORE + '/',) + tuple('.agents/skills/' + name + '/' for name in needed)
    return {name: data for name, data in package['files'].items() if name.startswith(scope)}


def baseline(root, baseline_zip, mode):
    """旧版文件指纹：优先使用已安装清单，5.x 没有清单时可传旧版安装包作对照。"""
    if baseline_zip:
        old = read_package(baseline_zip)
        return {name: digest(data) for name, data in mode_files(old, mode).items()}, old['version']
    path = safe(root, MANIFEST)
    if path.is_file():
        data = json.loads(path.read_text())
        return dict(data.get('files', {})), data.get('version')
    return None, None


def current_hash(root, name):
    path = safe(root, name)
    return digest(path.read_bytes()) if path.is_file() else None


def plan(root, package_zip, baseline_zip=None, force=False, mode=None):
    root = root.expanduser().resolve()
    current_mode = setup_project.install_mode(root)
    mode = setup_project.install_mode(root, mode)
    installed = safe(root, CORE + '/references/VERSION')
    if not installed.is_file():
        raise ValueError('项目尚未安装 TeamFlow；新项目直接把安装包解压到项目根')
    old_version = installed.read_text().strip()
    package = read_package(package_zip)
    new = mode_files(package, mode)
    if version_key(package['version']) < version_key(old_version) and not force:
        raise ValueError(f'安装包版本 {package["version"]} 低于已安装 {old_version}；确认降级时加 --force')
    # 旧版指纹按原模式取，切换模式时原模式独有且未改动的文件随之移除。
    known, _ = baseline(root, baseline_zip, current_mode)
    actions = {'add': [], 'update': [], 'remove': [], 'unchanged': [], 'conflict': []}
    for name, data in sorted(new.items()):
        now = current_hash(root, name)
        target = digest(data)
        if now == target:
            actions['unchanged'].append(name)
        elif now is None:
            actions['add'].append(name)
        elif known is not None and known.get(name) == now:
            actions['update'].append(name)
        else:
            # 没有旧版指纹或与旧版不同，都可能是团队直接改过的规范。
            actions['conflict'].append(name)
    for name in sorted(set(known or {}) - set(new)):
        now = current_hash(root, name)
        if now is None:
            continue
        if now == known[name]:
            actions['remove'].append(name)
        else:
            actions['conflict'].append(name)
    return {'project': str(root), 'mode': mode, 'from': old_version, 'to': package['version'],
            'baseline': 'manifest' if known is not None and not baseline_zip else
                        'package' if baseline_zip else 'none',
            'actions': actions, 'files': new}


def manifest_text(version, package, files):
    data = {'version': version, 'package': package,
            'files': {name: digest(content) for name, content in sorted(files.items())}}
    return json.dumps(data, ensure_ascii=False, indent=2) + '\n'


def upgrade(root, package_zip, baseline_zip=None, force=False, dry_run=False, mode=None):
    result = plan(root, package_zip, baseline_zip, force, mode)
    actions = result['actions']
    files = result.pop('files')
    result['blocked'] = bool(actions['conflict']) and not force
    if dry_run:
        return result
    if result['blocked']:
        raise ValueError('以下文件有本地改动，未升级：\n  ' + '\n  '.join(actions['conflict']) + '\n' + conflict_hint(result))
    root = Path(result['project'])
    for name, data in files.items():
        if name in actions['unchanged']:
            continue
        target = safe(root, name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    removals = actions['remove'] + [name for name in actions['conflict'] if name not in files]
    for name in removals:
        target = safe(root, name)
        if target.is_file():
            target.unlink()
        parent = target.parent
        stop = safe(root, '.agents')
        while parent != stop and parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()
            parent = parent.parent
    safe(root, MANIFEST).write_text(manifest_text(result['to'], result['mode'], files))
    # 入口文本可能随版本变化，由新核心刷新；未指定模式时沿用已有选择。
    entry = safe(root, CORE + '/scripts/teamflow.py')
    refreshed = subprocess.run([sys.executable, str(entry), '--project', str(root), 'setup', '--mode', result['mode']],
                               capture_output=True, text=True)
    if refreshed.returncode:
        raise ValueError('文件已升级，但刷新入口失败：' + refreshed.stderr.strip())
    return result


def conflict_hint(result):
    return (('5.x 项目没有安装清单：传 --baseline 旧版安装包对照，' if result['baseline'] == 'none' else '')
            + '把定制移到 .agents/team/ 后重试，或核对后加 --force 覆盖')


def describe(result, dry_run=False):
    actions = result['actions']
    counts = '，'.join(f'{label} {len(actions[key])}' for key, label in (
        ('add', '新增'), ('update', '更新'), ('remove', '移除'), ('conflict', '覆盖本地改动'),
        ('unchanged', '未变')) if actions[key])
    head = ('升级预览' if dry_run else '已升级') + f'（{setup_project.MODE_LABELS[result["mode"]]}）：' \
        f'{result["from"]} → {result["to"]}'
    lines = [head, counts or '无变化']
    if dry_run:
        for key, label in (('add', '+'), ('update', '~'), ('remove', '-'), ('conflict', '!')):
            lines.extend(f'  {label} {name}' for name in actions[key])
        if result['blocked']:
            lines.append('! 为本地改动，直接升级会被拒绝：' + conflict_hint(result))
    else:
        lines.append('下一步：python3 scripts/teamflow.py doctor')
    return '\n'.join(lines)

