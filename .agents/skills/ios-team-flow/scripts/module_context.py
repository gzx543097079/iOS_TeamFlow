#!/usr/bin/env python3
"""记录并检查大型项目模块索引，输出基于 Git 对象和工作区的增量读取范围。"""
import argparse
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
    if not isinstance(data, dict) or data.get('schema_version') != 1:
        raise ValueError('project-modules.json schema_version 必须为 1')
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
        baseline = raw.get('baseline')
        if not isinstance(baseline, str) or not re.fullmatch(r'[0-9a-f]{40,64}', baseline):
            raise ValueError(name + ' 的 baseline 必须是完整小写提交 SHA')
        responsibility = raw.get('responsibility', '')
        if not isinstance(responsibility, str):
            raise ValueError(name + ' 的 responsibility 必须是字符串')
        item = {'name': name, 'responsibility': responsibility.strip(), 'baseline': baseline}
        for field in LIST_FIELDS:
            item[field] = string_list(raw.get(field, []), name + '.' + field,
                                      allow_empty=field not in ('triggers', 'paths'))
        item['paths'] = [safe_path(path) for path in item['paths']]
        cleaned.append(item)
    return {'schema_version': 1, 'cross_cutting_paths': cross, 'modules': cleaned}


def load_manifest(root, required=True):
    path = root / MANIFEST
    if path.is_symlink():
        raise ValueError(str(MANIFEST) + ' 不能是符号链接')
    if not path.exists():
        if required:
            raise ValueError('缺少 ' + str(MANIFEST) + '；先用 record 建立模块索引')
        return {'schema_version': 1, 'cross_cutting_paths': [], 'modules': []}
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


def commit_exists(root, sha):
    try:
        resolved = git(root, 'rev-parse', '--verify', '--end-of-options', sha + '^{commit}', text=True).strip()
        return resolved == sha
    except subprocess.CalledProcessError:
        return False


def tracked_at(root, ref, path):
    output = git(root, 'ls-tree', '-r', '--name-only', '-z', ref, '--', path)
    return bool(output)


def names(root, *args):
    return sorted(item for item in git(root, *args).decode().split('\0') if item)


def changes(root, baseline, paths):
    if not paths:
        return {'committed': [], 'staged': [], 'unstaged': [], 'untracked': []}
    return {
        'committed': names(root, 'diff', '--name-only', '--no-renames', '-z', baseline, 'HEAD', '--', *paths),
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
    results = []
    expand = route_problem is not None
    for module in selected:
        problems = []
        baseline = module['baseline']
        if not commit_exists(root, baseline):
            problems.append('baseline 无法解析')
            can_compare = False
        else:
            can_compare = True
            baseline_missing = [path for path in module['paths'] if not tracked_at(root, baseline, path)]
            head_missing = [path for path in module['paths'] if not tracked_at(root, head, path)]
            if baseline_missing:
                problems.append('baseline 未覆盖关注路径：' + ', '.join(baseline_missing))
            if head_missing:
                problems.append('HEAD 未覆盖关注路径（可能移动或删除）：' + ', '.join(head_missing))
        if not can_compare:
            module_changes = {'committed': [], 'staged': [], 'unstaged': [], 'untracked': []}
            cross_changes = {'committed': [], 'staged': [], 'unstaged': [], 'untracked': []}
        else:
            module_changes = changes(root, baseline, module['paths'])
            cross_changes = changes(root, baseline, data['cross_cutting_paths'])
        module_files = changed_files(module_changes)
        cross_files = changed_files(cross_changes)
        needs_expand = bool(problems or cross_files)
        expand = expand or needs_expand
        results.append({
            'name': module['name'], 'responsibility': module['responsibility'],
            'baseline': baseline, 'head': head,
            'status': 'invalid' if problems else ('changed' if module_files or cross_files else 'unchanged'),
            'problems': problems, 'paths': module['paths'], 'entry_symbols': module['entry_symbols'],
            'dependencies': module['dependencies'], 'callers': module['callers'],
            'verification': module['verification'], 'changes': module_changes,
            'cross_cutting_changes': cross_changes, 'suggested_read_files': sorted(set(module_files + cross_files)),
            'expand_scope': needs_expand,
        })
    return {'schema_version': 1, 'head': head, 'query': query,
            'selected_modules': [item['name'] for item in selected],
            'route_problem': route_problem, 'expand_scope': expand, 'modules': results}


def require_clean_paths(root, paths):
    dirty = changes(root, 'HEAD', paths)
    files = changed_files(dirty)
    if files:
        raise ValueError('关注路径存在未提交变化，不能记录或前移基准：' + ', '.join(files))


def record(root, args):
    data = load_manifest(root, required=False)
    paths = [safe_path(path) for path in args.path]
    cross = list(dict.fromkeys(data['cross_cutting_paths'] +
                              [safe_path(path) for path in args.cross_cutting]))
    head = head_sha(root)
    missing = [path for path in paths + cross if not tracked_at(root, head, path)]
    if missing:
        raise ValueError('HEAD 未跟踪关注路径：' + ', '.join(missing))
    require_clean_paths(root, paths + cross)
    module = {
        'name': args.name, 'responsibility': args.responsibility or '',
        'triggers': args.trigger, 'paths': paths, 'entry_symbols': args.entry,
        'dependencies': args.dependency, 'callers': args.caller,
        'verification': args.verification, 'baseline': head,
    }
    data['cross_cutting_paths'] = cross
    data['modules'] = [item for item in data['modules'] if item['name'] != args.name] + [module]
    write_manifest(root, data)
    return module


def refresh(root, module_name, accepted):
    if not accepted:
        raise ValueError('前移基准前必须显式提供 --accept-reviewed-changes')
    data = load_manifest(root)
    selected, _ = select_modules(data, [module_name])
    module = selected[0]
    watched = module['paths'] + data['cross_cutting_paths']
    require_clean_paths(root, watched)
    head = head_sha(root)
    missing = [path for path in module['paths'] if not tracked_at(root, head, path)]
    if missing:
        raise ValueError('HEAD 未覆盖关注路径，先修正模块索引：' + ', '.join(missing))
    module['baseline'] = head
    write_manifest(root, data)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('.'))
    commands = parser.add_subparsers(dest='command', required=True)
    check = commands.add_parser('inspect', help='只读路由并检查模块增量')
    group = check.add_mutually_exclusive_group(required=True)
    group.add_argument('--query')
    group.add_argument('--module', action='append')
    group.add_argument('--all', action='store_true')
    add = commands.add_parser('record', help='记录或更新一个模块并绑定当前 HEAD')
    add.add_argument('--name', required=True)
    add.add_argument('--responsibility')
    add.add_argument('--trigger', action='append', required=True)
    add.add_argument('--path', action='append', required=True)
    add.add_argument('--entry', action='append', default=[])
    add.add_argument('--dependency', action='append', default=[])
    add.add_argument('--caller', action='append', default=[])
    add.add_argument('--verification', action='append', default=[])
    add.add_argument('--cross-cutting', action='append', default=[])
    update = commands.add_parser('refresh', help='复核并提交后前移模块基准')
    update.add_argument('--module', required=True)
    update.add_argument('--accept-reviewed-changes', action='store_true')
    commands.add_parser('validate', help='验证索引格式和所有模块状态')
    args = parser.parse_args()
    try:
        root = project_root(args.project)
        if args.command == 'record':
            output = {'recorded': record(root, args)}
        elif args.command == 'refresh':
            output = {'refreshed': refresh(root, args.module, args.accept_reviewed_changes)}
        else:
            data = load_manifest(root)
            output = inspect(root, data, modules=getattr(args, 'module', None),
                             query=getattr(args, 'query', None), all_modules=args.command == 'validate' or getattr(args, 'all', False))
        print(json.dumps(output, ensure_ascii=False, indent=2))
        if args.command == 'validate' and any(item['status'] == 'invalid' for item in output['modules']):
            return 1
        return 0
    except (ValueError, OSError, UnicodeError, subprocess.CalledProcessError) as error:
        parser.exit(1, str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
