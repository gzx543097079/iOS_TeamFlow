#!/usr/bin/env python3
"""记录并检查大型项目模块索引：与基线分支分叉点及工作区比较，给出增量读取范围。"""
import json
import os
import re
import subprocess
from pathlib import Path, PurePosixPath

MANIFEST = Path('.agents/project-modules.json')
LIST_FIELDS = ('triggers', 'paths', 'entry_symbols', 'dependencies', 'callers', 'verification')


def git(root, *args, text=False):
    result = subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)
    return result.stdout.decode() if text else result.stdout


def project_root(path):
    root = path.resolve()
    actual = Path(git(root, 'rev-parse', '--show-toplevel', text=True).strip()).resolve()
    if actual != root:
        raise ValueError('请指定 Git 根目录')
    return root


def safe_path(value):
    if not isinstance(value, str) or not value.strip() or '\\' in value or '\0' in value or '\n' in value:
        raise ValueError('模块路径必须是非空项目相对 POSIX 路径')
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or value.startswith(':') or str(path) in ('.', ''):
        raise ValueError('模块路径不能是绝对路径、Git 魔法 pathspec 或越出项目目录：' + value)
    return str(path)


def string_list(value, field, allow_empty=True):
    if not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(field + ' 必须是非空字符串数组')
    result = list(dict.fromkeys(item.strip() for item in value))
    if not allow_empty and not result:
        raise ValueError(field + ' 不能为空')
    return result


def validate_manifest(data):
    if not isinstance(data, dict) or data.get('schema_version') != 2:
        raise ValueError('project-modules.json schema_version 必须为 2')
    base = data.get('base_branch')
    if base is not None and (not isinstance(base, str) or not re.fullmatch(r'[A-Za-z0-9._/-]+', base)
                             or base.startswith('-')):
        raise ValueError('base_branch 必须是分支名')
    cross = [safe_path(item) for item in string_list(data.get('cross_cutting_paths', []), 'cross_cutting_paths')]
    modules = data.get('modules')
    if not isinstance(modules, list):
        raise ValueError('modules 必须是数组')
    names = set()
    cleaned = []
    for raw in modules:
        if not isinstance(raw, dict):
            raise ValueError('每个模块必须是对象')
        name = raw.get('name')
        if not isinstance(name, str) or not name.strip() or name.strip() in names:
            raise ValueError('模块 name 必须非空且唯一')
        name = name.strip()
        names.add(name)
        responsibility = raw.get('responsibility', '')
        if not isinstance(responsibility, str):
            raise ValueError(name + ' 的 responsibility 必须是字符串')
        item = {'name': name, 'responsibility': responsibility.strip()}
        for field in LIST_FIELDS:
            item[field] = string_list(raw.get(field, []), name + '.' + field,
                                      allow_empty=field not in ('triggers', 'paths'))
        item['paths'] = [safe_path(path) for path in item['paths']]
        cleaned.append(item)
    result = {'schema_version': 2, 'cross_cutting_paths': cross, 'modules': cleaned}
    if base is not None:
        result['base_branch'] = base
    return result


def load_manifest(root, required=True):
    path = root / MANIFEST
    if path.is_symlink():
        raise ValueError(str(MANIFEST) + ' 不能是符号链接')
    if not path.exists():
        if required:
            raise ValueError('缺少 ' + str(MANIFEST) + '；先用 record 建立模块索引')
        return {'schema_version': 2, 'cross_cutting_paths': [], 'modules': []}
    try:
        return validate_manifest(json.loads(path.read_text()))
    except json.JSONDecodeError as error:
        raise ValueError(str(MANIFEST) + ' 不是有效 JSON：' + str(error)) from error


def write_manifest(root, data):
    data = validate_manifest(data)
    path = root / MANIFEST
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError(str(MANIFEST) + ' 不能是符号链接')
    temporary = path.with_name(path.name + '.tmp')
    if temporary.exists() or temporary.is_symlink():
        raise ValueError('临时索引文件已存在，请核对：' + str(temporary.relative_to(root)))
    with temporary.open('x') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    os.replace(temporary, path)


def head_sha(root):
    return git(root, 'rev-parse', '--verify', 'HEAD^{commit}', text=True).strip()


def base_commit(root, data):
    """基线分支与 HEAD 的分叉点；在基线分支上即为 HEAD，只剩工作区改动。"""
    candidates = [data['base_branch']] if data.get('base_branch') else []
    if not candidates:
        remote = subprocess.run(['git', '-C', str(root), 'symbolic-ref', '--quiet', '--short',
                                 'refs/remotes/origin/HEAD'], capture_output=True, text=True)
        candidates = ([remote.stdout.strip()] if remote.returncode == 0 else []) + ['main', 'master']
    for ref in candidates:
        found = subprocess.run(['git', '-C', str(root), 'merge-base', 'HEAD', '--end-of-options', ref],
                               capture_output=True, text=True)
        if found.returncode == 0:
            return ref, found.stdout.strip()
    if data.get('base_branch'):
        raise ValueError('无法解析 base_branch：' + data['base_branch'])
    return 'HEAD', head_sha(root)


def tracked(root, path):
    """按 Git 索引判断，已暂存的移动或新增路径即可生效，无需先提交。"""
    return bool(git(root, 'ls-files', '-z', '--', path))


def names(root, *args):
    return sorted(item for item in git(root, *args).decode().split('\0') if item)


def changes(root, base, paths):
    if not paths:
        return {'committed': [], 'staged': [], 'unstaged': [], 'untracked': []}
    return {
        'committed': names(root, 'diff', '--name-only', '--no-renames', '-z', base, 'HEAD', '--', *paths),
        'staged': names(root, 'diff', '--cached', '--name-only', '--no-renames', '-z', '--', *paths),
        'unstaged': names(root, 'diff', '--name-only', '--no-renames', '-z', '--', *paths),
        'untracked': names(root, 'ls-files', '--others', '--exclude-standard', '-z', '--', *paths),
    }


def changed_files(groups):
    return sorted({path for values in groups.values() for path in values})


def select_modules(data, modules=None, query=None, all_modules=False):
    by_name = {item['name']: item for item in data['modules']}
    if all_modules:
        return list(data['modules']), None
    if modules:
        missing = [name for name in modules if name not in by_name]
        if missing:
            raise ValueError('未知模块：' + ', '.join(missing))
        return [by_name[name] for name in dict.fromkeys(modules)], None
    if query is not None:
        folded = query.casefold()
        selected = [item for item in data['modules']
                    if item['name'].casefold() in folded
                    or any(trigger.casefold() in folded for trigger in item['triggers'])]
        return selected, None if selected else '查询未命中模块触发词'
    raise ValueError('inspect 需要 --query、--module 或 --all')


def inspect(root, data, modules=None, query=None, all_modules=False):
    selected, route_problem = select_modules(data, modules, query, all_modules)
    head = head_sha(root)
    base_ref, base = base_commit(root, data)
    cross_changes = changes(root, base, data['cross_cutting_paths'])
    cross_files = changed_files(cross_changes)
    results = []
    expand = route_problem is not None or bool(cross_files)
    for module in selected:
        missing = [path for path in module['paths'] if not tracked(root, path)]
        problems = ['Git 未跟踪关注路径（可能移动或删除）：' + ', '.join(missing)] if missing else []
        module_changes = changes(root, base, module['paths'])
        module_files = changed_files(module_changes)
        needs_expand = bool(problems or cross_files)
        expand = expand or needs_expand
        results.append({
            'name': module['name'], 'responsibility': module['responsibility'],
            'status': 'invalid' if problems else ('changed' if module_files or cross_files else 'unchanged'),
            'problems': problems, 'paths': module['paths'], 'entry_symbols': module['entry_symbols'],
            'dependencies': module['dependencies'], 'callers': module['callers'],
            'verification': module['verification'], 'changes': module_changes,
            'suggested_read_files': sorted(set(module_files + cross_files)), 'expand_scope': needs_expand,
        })
    return {'schema_version': 2, 'base': base_ref, 'merge_base': base, 'head': head, 'query': query,
            'selected_modules': [item['name'] for item in selected], 'route_problem': route_problem,
            'cross_cutting_changes': cross_changes, 'expand_scope': expand, 'modules': results}


def record(root, name, paths, triggers, responsibility='', entries=(), dependencies=(), callers=(),
           verification=(), cross_cutting=()):
    data = load_manifest(root, required=False)
    paths = [safe_path(path) for path in paths]
    cross = list(dict.fromkeys(data['cross_cutting_paths'] + [safe_path(path) for path in cross_cutting]))
    missing = [path for path in paths + cross if not tracked(root, path)]
    if missing:
        raise ValueError('Git 未跟踪关注路径：' + ', '.join(missing))
    module = {'name': name, 'responsibility': responsibility or '', 'triggers': list(triggers),
              'paths': paths, 'entry_symbols': list(entries), 'dependencies': list(dependencies),
              'callers': list(callers), 'verification': list(verification)}
    data['cross_cutting_paths'] = cross
    data['modules'] = [item for item in data['modules'] if item['name'] != name] + [module]
    write_manifest(root, data)
    return module
