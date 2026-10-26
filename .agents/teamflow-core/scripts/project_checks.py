#!/usr/bin/env python3
"""按项目配置执行构建/测试，保存真实退出结果；不猜测 Scheme 或工具链。"""
import hashlib
import io
import json
import os
import re
import signal
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from teamflow_common import local_path
from requirement_model import ID, semantic_content

CONFIG = '.agents/project-checks.json'


def changed_paths(root, requirement=None):
    """读取相对 HEAD 的暂存/工作区差异和未跟踪文件，支持尚无提交的仓库。

    指定需求时另计入带 `Requirement: <编号>` 尾注的已提交改动，阶段提交后自动选择仍按整张卡的范围。
    """
    top = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--show-toplevel'],
                                  stderr=subprocess.PIPE).decode().strip()
    if Path(top).resolve() != root.resolve():
        raise ValueError('改动范围检查必须从项目 Git 根执行')
    head = subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', 'HEAD'],
                          capture_output=True)
    commands = [['diff', 'HEAD', '--name-only', '--no-renames', '-z']] if head.returncode == 0 else [
        ['diff', '--cached', '--name-only', '--no-renames', '-z'],
        ['diff', '--name-only', '--no-renames', '-z']]
    commands.append(['ls-files', '--others', '--exclude-standard', '-z'])
    if requirement is not None and head.returncode == 0:
        if not ID.fullmatch(requirement):
            raise ValueError('需求编号格式应为 REQ-YYYYMMDD-xxxx')
        commands.append(['log', '--format=', '--name-only', '--no-renames', '-z',
                         '--grep=^Requirement: ' + requirement + '$'])
    names = set()
    for argv in commands:
        raw = subprocess.check_output(['git', '-C', str(root), *argv])
        names.update(os.fsdecode(name).strip('\n') for name in raw.split(b'\0') if name.strip(b'\n'))
    return names


DOCUMENT_SUFFIXES = ('.md', '.rst', '.txt')


def non_document_paths(root, names):
    """人工证据与提交检查共用的白名单：除 TeamFlow 安装文件和需求卡外，只有文档/记录可人工核对。"""
    installed = installed_files(root)
    return sorted(name for name in names if name not in installed and not name.startswith('requirements/')
                  and not excluded_input(name) and Path(name).suffix.lower() not in DOCUMENT_SUFFIXES)


def _git_text(root, spec):
    shown = subprocess.run(['git', '-C', str(root), 'show', spec], capture_output=True)
    return shown.stdout.decode('utf-8', 'replace') if shown.returncode == 0 else None


def _versions(root, name):
    """HEAD、暂存区与工作区三个版本；不存在为 None。"""
    path = local_path(root, name)
    return (_git_text(root, 'HEAD:' + name), _git_text(root, ':' + name),
            path.read_text() if path.is_file() else None)


def installed_files(root):
    """TeamFlow 自身的安装文件不属于项目验证范围：与安装清单一致的核心与 Skill、入口，
    托管区块外未改动的 AGENTS，以及与原版模板一致的宿主权限文件。项目自己的规则与权限改动须由验证覆盖。"""
    import setup_project
    import upgrade
    result = set()
    agents = [None if text is None else setup_project.outside_block(text) for text in _versions(root, 'AGENTS.md')]
    if any(text is not None for text in agents) and len({(text or '').strip() for text in agents}) == 1:
        result.add('AGENTS.md')
    templates = Path(__file__).resolve().parents[1] / 'assets/permissions'
    for name, source in setup_project.PERMISSION_TEMPLATES.items():
        versions = _versions(root, name)
        if any(text is not None for text in versions) and all(
                text in (None, (templates / source).read_text()) for text in versions):
            result.add(name)
    entry = local_path(root, 'scripts/teamflow.py')
    if entry.is_file() and entry.read_text() == setup_project.ENTRY:
        result.add('scripts/teamflow.py')
    bootstrap = Path(__file__).resolve().parent / 'install_teamflow.py'
    root_bootstrap = local_path(root, 'install_teamflow.py')
    if (bootstrap.is_file() and root_bootstrap.is_file()
            and root_bootstrap.read_bytes() == bootstrap.read_bytes()):
        result.add('install_teamflow.py')
    manifest = local_path(root, upgrade.MANIFEST)
    if manifest.is_file():
        result.add(upgrade.MANIFEST)
        files = json.loads(manifest.read_text()).get('files', {})
        result.update(name for name, digest in files.items() if upgrade.current_hash(root, name) == digest)
    return result


def _effective_profiles(text):
    try:
        profiles = json.loads(text)['profiles']
        return {name: effective_config({'profiles': {name: resolve_profile(profiles, name)}}, name)
                for name in profiles}
    except (ValueError, KeyError, TypeError):
        return None


def changed_profiles(root, keep=()):
    """暂存配置相对 HEAD 改变了执行语义的 profile；本次证据实际运行的 profile 不列出。"""
    before, after = (_effective_profiles(text) if text is not None else {} for text in _versions(root, CONFIG)[:2])
    if after is None:
        return []
    before = before or {}
    return sorted(name for name in after.keys() | before.keys()
                  if name not in keep and after.get(name) != before.get(name))


def config_changed_checks(root, profile):
    """工作区配置相对 HEAD 改变了执行语义的检查；profile 级字段变化或无法比较（如配置改动已在阶段提交中）时返回 None，表示全部。"""
    head, _, current = _versions(root, CONFIG)
    if head is None or current is None or head == current:
        return None
    before, after = _effective_profiles(head), _effective_profiles(current)
    if not before or not after or profile not in before or profile not in after:
        return None
    old, new = before[profile], after[profile]
    if {k: v for k, v in old.items() if k != 'checks'} != {k: v for k, v in new.items() if k != 'checks'}:
        return None
    previous = {check['name']: check for check in old['checks']}
    return {check['name'] for check in new['checks'] if previous.get(check['name']) != check}


def project_changes(root, names):
    """参与验证的改动：排除生成证据、需求卡与未改动的 TeamFlow 安装文件。"""
    return {name for name in names if not excluded_input(name) and not requirement_path(name)} - installed_files(root)


def requirement_path(name):
    path = Path(name)
    return path.parent == Path('requirements') and path.suffix == '.md' and bool(ID.fullmatch(path.stem))


def intersect_inputs(left, right):
    """字面路径范围交集；None 与点均表示完整项目。"""
    if left is None:
        return right
    if right is None:
        return left
    result = set()
    for a in map(lambda n: str(Path(n)), left):
        for b in map(lambda n: str(Path(n)), right):
            if a == '.' or a == b or b.startswith(a + '/'):
                result.add(b)
            elif b == '.' or a.startswith(b + '/'):
                result.add(a)
    return sorted(result)


def check_coverage(settings, name):
    return intersect_inputs(coverage_inputs(settings), settings['checks'][name].get('covers'))


def checked_names(settings, checks):
    if (not isinstance(checks, list) or not checks or any(not isinstance(n, str) for n in checks)
            or len(set(checks)) != len(checks) or set(checks) - settings['checks'].keys()):
        raise ValueError('证据 checks 必须是非空、无重复的有效检查名单')
    return [name for name in settings['checks'] if name in checks]


def evidence_inputs(root, evidence, config=None):
    config = config or load_config(root)
    settings = config['profiles'][evidence['profile']]
    if 'checks' not in evidence:
        return coverage_inputs(settings)
    names = checked_names(settings, evidence['checks'])
    scopes = [check_coverage(settings, name) for name in names]
    return None if None in scopes else sorted({path for scope in scopes for path in scope})


def execution_plan(root, config, profile, requirement=None, force=False, names=None):
    settings = config['profiles'][profile]
    triggered = any('covers' in check for check in settings['checks'].values())
    if names is None:
        try:
            names = changed_paths(root, requirement)
        except (ValueError, subprocess.CalledProcessError):
            if triggered:
                raise
            names = set()
    names = project_changes(root, names)
    # trigger: covers 时只按各项负责范围触发，inputs 仅进入证据指纹与缓存键。
    by_covers = settings.get('trigger') == 'covers'
    configured = config_changed_checks(root, profile) if triggered and CONFIG in names else None
    selected = []
    for name, check in settings['checks'].items():
        scope = check_coverage(settings, name)
        covered = input_paths(root, scope, names) if scope != [] else set()
        dependencies = set() if by_covers else input_paths(root, check.get('inputs', settings.get('inputs')), names)
        config_hit = CONFIG in names and (configured is None or name in configured)
        if force or settings.get('manual') or not triggered or config_hit or covered or dependencies:
            selected.append(name)
    covered = set()
    for name in selected:
        scope = check_coverage(settings, name)
        if scope != []:
            covered.update(input_paths(root, scope, names))
    if CONFIG in names:
        # 所选 profile 的执行语义已进入指纹；其他 profile 的变化由 git check 提示。
        covered.add(CONFIG)
    uncovered = sorted(names - covered)
    # 非规范 requirements 文件仍属于普通工程输入，不能借目录名豁免。
    engineering = [name for name in uncovered if Path(name).suffix.lower() not in DOCUMENT_SUFFIXES]
    return {'selected': selected, 'skipped': [name for name in settings['checks'] if name not in selected],
            'changed_files': sorted(names), 'covered_files': sorted(covered), 'uncovered_files': uncovered,
            'uncovered_engineering_files': engineering, 'triggered': triggered,
            # 声明了 check covers 或 profile covers（验收范围上限）时，范围外工程改动在执行前阻断；仅有 inputs 的旧配置由提交检查核对。
            'enforced': triggered or 'covers' in settings,
            'manual': bool(settings.get('manual'))}


def suggest(root, requirement=None):
    config = load_config(root)
    names = changed_paths(root, requirement)
    profiles, covered = [], set()
    for profile, settings in config['profiles'].items():
        plan = execution_plan(root, config, profile, requirement, names=names)
        if not plan['manual']:
            covered.update(plan['covered_files'])
        profiles.append({'profile': profile, **plan,
                         'covers_all_changes': bool(plan['changed_files']) and not plan['uncovered_files'],
                         'last_pass': last_pass(root, profile)})
    names = project_changes(root, names)
    covering = [item['profile'] for item in profiles if item['covers_all_changes'] and not item['manual']]
    best = min((config['profiles'][name].get('priority', 100) for name in covering), default=None)
    preferred = [name for name in covering if config['profiles'][name].get('priority', 100) == best]
    recommended = preferred[0] if len(preferred) == 1 else None
    return {'changed_files': sorted(names), 'profiles': profiles, 'recommended': recommended,
            'uncovered_files': sorted(names - covered), 'ambiguous_profiles': preferred if len(preferred) > 1 else [],
            'note': '按实际改动选择检查；manual profile 仅显式执行。'}


# 日常验证不应包含的 Release 构建：xcodebuild Release 配置与 Godot release 导出。
RELEASE_BUILD = re.compile(r'''-configuration['"\s,]+Release\b|--export-release\b''')


INTERPRETER = re.compile(r'(python[\d.]*|sh|bash|zsh|node|ruby|swift)')


def executed_script(argv):
    """实际执行的脚本：命令本身，或解释器后的首个非选项参数；`-m`/`-c` 不执行脚本文件（如 py_compile 只做语法检查）。"""
    if not INTERPRETER.fullmatch(Path(argv[0]).name):
        return argv[0]
    for arg in argv[1:]:
        if arg in ('-m', '-c'):
            return None
        if not arg.startswith('-'):
            return arg
    return None


def check_text(root, check):
    """检查命令及其实际执行的项目内脚本文本；只用于识别旧形态，不执行。"""
    parts = [' '.join(check['argv'])]
    script = executed_script(check['argv'])
    try:
        path = local_path(root, str(Path(check.get('cwd', '.')) / script)) if script else None
        if path and path.is_file() and path.stat().st_size < 1_000_000:
            parts.append(path.read_text(errors='replace'))
    except (ValueError, OSError):
        pass
    return '\n'.join(parts)


LONG_CHECK_SECONDS = 180


def legacy_layout(root, config):
    """升级后需迁移的旧形态：日常（非 manual）profile 含 Release 构建为需处理；
    未声明 check covers 时每次改动整组执行、日常检查最近实际耗时过长，仅提示由 Agent 判断是否拆分。"""
    releases = {profile: [name for name, check in settings['checks'].items()
                          if RELEASE_BUILD.search(check_text(root, check))]
                for profile, settings in config['profiles'].items()}
    issues = []
    for profile, settings in config['profiles'].items():
        if settings.get('manual'):
            continue
        others = [name for name in releases if name != profile and releases[name]]
        for name in releases[profile]:
            issues.append(('需处理', f'日常 profile {profile} 的检查 {name} 含 Release 构建，应移入 manual profile'
                           + (f"（{'、'.join(others)} 也含 Release 构建，核对是否重复）" if others else '')))
        for name in settings['checks']:
            seconds = recent_duration(root, profile, name)
            if seconds is not None and seconds > LONG_CHECK_SECONDS:
                issues.append(('提示', f'日常 profile {profile} 的检查 {name} 最近实际执行 {round(seconds)} 秒，'
                               '命中即整项执行；按模块拆分，全套测试移入 manual profile'))
        if not any('covers' in check for check in settings['checks'].values()):
            issues.append(('提示', f'profile {profile} 未声明 check covers，每次改动整组执行'
                           + ('，失败后无法只重跑失败项' if len(settings['checks']) == 1 else '')))
    return [{'status': status, 'detail': detail} for status, detail in issues]


def coverage_inputs(settings):
    """covers 表示可验收的改动；inputs 表示会令证据失效的依赖。旧配置兼容。"""
    return settings.get('covers', settings.get('inputs'))


def resolve_profile(profiles, name, seen=()):
    """extends 继承范围、优先级与检查；自身字段覆盖，checks 追加或同名覆盖。"""
    if name in seen:
        raise ValueError('profile extends 存在循环：' + ' → '.join(seen + (name,)))
    if name not in profiles:
        raise ValueError('extends 指向不存在的 profile：' + name)
    settings = dict(profiles[name])
    parent = settings.pop('extends', None)
    if parent is None:
        return settings
    if not isinstance(parent, str):
        raise ValueError('extends 必须是 profile 名：' + name)
    base = resolve_profile(profiles, parent, seen + (name,))
    own_checks = settings.get('checks', {})
    if not isinstance(own_checks, dict):
        raise ValueError('checks 必须为对象：' + name)
    resolved = {**base, **settings, 'checks': {**base.get('checks', {}), **own_checks}}
    return {key: value for key, value in resolved.items() if value is not None}


def select_profile(root, requirement=None):
    """按适用范围与显式优先级选择；没有唯一候选时不猜测。指定需求时计入其已提交的阶段改动。"""
    report = suggest(root, requirement)
    if not report['changed_files']:
        raise ValueError('相对 HEAD 及本需求的提交都没有改动，无法自动选择验证；请用 --profile 指定')
    if report['recommended'] is None:
        if report['ambiguous_profiles']:
            raise ValueError('多个 profile 优先级相同：' + '、'.join(report['ambiguous_profiles'])
                             + '；请配置 priority 或用 --profile 指定')
        if report['uncovered_files']:
            raise ValueError('以下改动不在任何 profile 输入内：' + '、'.join(report['uncovered_files'][:10])
                             + '；请配置覆盖范围或用 --profile 指定')
        raise ValueError('改动分属多个 profile，没有单个 profile 全部覆盖；请配置覆盖整个改动的 profile 或用 --profile 指定')
    return report['recommended']


def load_config(root):
    config = json.loads(local_path(root, CONFIG).read_text())
    if not isinstance(config, dict) or config.get('schema_version') != 2:
        raise ValueError('配置 schema_version 必须为 2')
    profiles = config.get('profiles')
    if not isinstance(profiles, dict) or any(not isinstance(v, dict) for v in profiles.values()):
        raise ValueError('profiles 必须为对象')
    config['profiles'] = profiles = {name: resolve_profile(profiles, name) for name in profiles}
    for profile, settings in profiles.items():
        if type(settings.get('priority', 100)) is not int or settings.get('priority', 100) < 0:
            raise ValueError('priority 必须为非负整数：' + profile)
        for field in ('inputs', 'covers'):
            if field in settings:
                if settings[field] is None:
                    raise ValueError(field + ' 必须是非空项目相对文件/目录列表')
                input_paths(root, settings[field], set())
        if 'covers' in settings and settings.get('inputs') is not None:
            covers = {str(Path(name)) for name in settings['covers']}
            if input_paths(root, settings['inputs'], covers) != covers:
                raise ValueError('covers 必须包含在 inputs 依赖范围内：' + profile)
        if type(settings.get('parallelism', 1)) is not int or settings.get('parallelism', 1) < 1:
            raise ValueError('parallelism 必须为正整数：' + profile)
        if 'manual' in settings and not isinstance(settings['manual'], bool):
            raise ValueError('manual 必须为布尔值：' + profile)
        if 'incremental' in settings and not isinstance(settings['incremental'], bool):
            raise ValueError('incremental 必须为布尔值：' + profile)
        if settings.get('trigger', 'inputs') not in ('inputs', 'covers'):
            raise ValueError('trigger 必须为 inputs 或 covers：' + profile)
        if not isinstance(settings.get('checks'), dict) or not settings['checks']:
            raise ValueError('profile 必须包含非空 checks 对象：' + profile)
        for name, check in settings['checks'].items():
            if not re.fullmatch(r'[a-zA-Z0-9_-]+', name) or not isinstance(check, dict):
                raise ValueError('检查名称或配置无效')
            argv = check.get('argv')
            if (not isinstance(argv, list) or not argv
                    or any(not isinstance(arg, str) or not arg or '\0' in arg for arg in argv)):
                raise ValueError(name + ' 的 argv 必须为非空字符串数组')
            for field in ('inputs', 'covers'):
                if field in check:
                    if check[field] is None:
                        raise ValueError(field + ' 必须是非空项目相对文件/目录列表')
                    input_paths(root, check[field], set())
            if 'covers' in check:
                covers = {str(Path(path)) for path in check['covers']}
                if input_paths(root, coverage_inputs(settings), covers) != covers:
                    raise ValueError('check covers 必须包含在 profile covers 范围内：' + name)
            if 'cache' in check and not isinstance(check['cache'], bool):
                raise ValueError('cache 必须为布尔值：' + name)
            timeout = check.get('timeout_seconds', 900)
            if type(timeout) is not int or not 1 <= timeout <= 86400:
                raise ValueError(name + ' 的 timeout_seconds 必须为 1–86400')
            cwd = local_path(root, check.get('cwd', '.'))
            if not cwd.is_dir():
                raise ValueError(name + ' 的工作目录不存在')
    return config


# 自动生成的证据不参与源码指纹，避免报告写入令自身失效。
EVIDENCE_DIRS = ('logs/project-checks/',)


def excluded_input(name):
    parts = Path(name).parts
    return (name.startswith(EVIDENCE_DIRS) or any(p in ('.git', '__pycache__', '.build', 'DerivedData')
            or p.endswith('.xcresult') for p in parts) or Path(name).suffix in ('.pyc', '.pyo'))


def input_paths(root, inputs=None, candidates=None):
    """测试和验收共享输入选择；目录使用 Git 可见文件，排除忽略的生成物。"""
    if inputs is not None:
        if not isinstance(inputs, list) or not inputs or any(not isinstance(n, str) or not n for n in inputs):
            raise ValueError('inputs 必须是非空项目相对文件/目录列表')
        for name in inputs:
            if any(c in name for c in '*?'):
                raise ValueError('inputs/covers 仅支持字面文件或目录，不支持 glob：' + name)
            local_path(root, name)
        inputs = [str(Path(n)) for n in inputs]
    validate_inputs = candidates is None
    if candidates is None:
        try:
            top = subprocess.check_output(['git', '-C', str(root), 'rev-parse', '--show-toplevel'],
                                          stderr=subprocess.PIPE).decode().strip()
            if Path(top).resolve() != root.resolve():
                # 嵌套普通目录不能借用外层仓库的忽略规则或文件清单。
                raise subprocess.CalledProcessError(1, ['git', 'rev-parse'])
            raw = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--cached', '--others',
                                           '--exclude-standard', '-z'], stderr=subprocess.PIPE)
            candidates = {os.fsdecode(n) for n in raw.split(b'\0') if n}
        except subprocess.CalledProcessError:
            if inputs is None:
                raise ValueError('非 Git 项目必须显式配置 inputs')
            candidates = {str(p.relative_to(root)) for n in inputs for p in
                          ([local_path(root, n)] if not local_path(root, n).is_dir() else local_path(root, n).rglob('*'))
                          if p.is_file() or p.is_symlink()}
    if validate_inputs and inputs is not None:
        for item in inputs:
            if any(not excluded_input(n) and (item == '.' or n == item or n.startswith(item + '/')) for n in candidates):
                continue
            # 允许本次删除及后续复核已跟踪的删除路径，但不能静默接受拼错/空目录。
            history = subprocess.run(['git', '-C', str(root), 'log', '-1', '--format=%H', '--', item],
                                     capture_output=True, text=True)
            if history.returncode != 0 or not history.stdout.strip():
                raise ValueError('验证输入无有效文件且无跟踪历史：' + item)
    return {n for n in candidates if not excluded_input(n) and (inputs is None or any(
        item == '.' or n == item or n.startswith(item.rstrip('/') + '/') for item in inputs))}


def content_for_snapshot(name, content):
    path = Path(name)
    if path.parent == Path('requirements') and path.suffix == '.md' and ID.fullmatch(path.stem):
        return semantic_content(content.decode('utf-8'), path.stem)
    return content


def effective_config(config, profile):
    """仅绑定所选检查的执行语义，其他 profile 和 JSON 排版不影响证据。
    新字段只在显式配置时写入，保证未启用 incremental 的 profile 指纹不变。"""
    settings = config['profiles'][profile]
    return {**({'covers': settings['covers']} if 'covers' in settings else {}),
            'inputs': settings.get('inputs'),
            **{key: settings[key] for key in ('manual', 'parallelism', 'trigger') if key in settings},
            **({'incremental': True} if settings.get('incremental') else {}),
            'checks': [{'name': name, 'argv': check['argv'],
                        'cwd': check.get('cwd', '.'),
                        'timeout_seconds': check.get('timeout_seconds', 900),
                        **({'inputs': check['inputs']} if check.get('inputs') is not None else {}),
                        **{key: check[key] for key in ('covers', 'cache') if key in check}}
                       for name, check in settings['checks'].items()]}


def read_blobs(root, object_ids):
    """一次 Git 调用读取所选对象；按字节长度解析，支持任意二进制内容。"""
    object_ids = list(dict.fromkeys(object_ids))
    if not object_ids:
        return {}
    output = subprocess.run(['git', '-C', str(root), 'cat-file', '--batch'],
                            input=b'\n'.join(object_ids) + b'\n',
                            check=True, capture_output=True).stdout
    stream = io.BytesIO(output)
    blobs = {}
    for oid in object_ids:
        header = stream.readline().split()
        if len(header) != 3 or header[:2] != [oid, b'blob']:
            raise ValueError('暂存对象不是有效 blob：' + oid.decode())
        size = int(header[2])
        content = stream.read(size)
        if len(content) != size or stream.read(1) != b'\n':
            raise ValueError('暂存对象内容不完整：' + oid.decode())
        blobs[oid] = content
    if stream.read():
        raise ValueError('暂存对象响应包含额外数据')
    return blobs


def check_inputs(settings, name):
    check = settings['checks'][name]
    inputs = check.get('inputs', settings.get('inputs'))
    if inputs is None:
        return None
    return sorted(set(inputs + check.get('covers', [])))


def source_snapshot(root, config, profile, staged=False, requirement=None, raw_config=False, commit=None, checks=None,
                    algorithm=None):
    """commit 指定时只读取该提交的文件树和配置，用于复核已交付需求，不受后续工作区变化影响。"""
    index = {}
    if commit is not None:
        raw = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-r', '-z', '--full-tree', commit],
                                      stderr=subprocess.PIPE)
        for entry in filter(None, raw.split(b'\0')):
            metadata, name = entry.split(b'\t', 1)
            mode, kind, oid = metadata.split()
            if kind == b'blob':
                index[os.fsdecode(name)] = (mode, oid)
        if CONFIG not in index:
            raise ValueError('交付提交缺少验证配置')
        committed = json.loads(read_blobs(root, [index[CONFIG][1]])[index[CONFIG][1]])
        profiles = committed.get('profiles') if isinstance(committed, dict) else None
        if not isinstance(profiles, dict) or profile not in profiles:
            raise ValueError('交付提交的配置缺少所选 profile：' + str(profile))
        config = {'profiles': {profile: resolve_profile(profiles, profile)}}
    inputs = config['profiles'][profile].get('inputs')
    if checks is not None:
        settings = config['profiles'][profile]
        checks = checked_names(settings, checks)
        scopes = ([inputs] if algorithm == 'sha256-files-v5' else []) + [check_inputs(settings, name) for name in checks]
        inputs = None if None in scopes else sorted({path for scope in scopes for path in scope})
    if staged:
        raw = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--stage', '-z'],
                                      stderr=subprocess.PIPE)
        for entry in filter(None, raw.split(b'\0')):
            metadata, name = entry.split(b'\t', 1)
            mode, oid, stage = metadata.split()
            if stage != b'0':
                raise ValueError('暂存区有未解决冲突')
            index[os.fsdecode(name)] = (mode, oid)

    paths = input_paths(root, inputs, set(index)) if commit is not None else input_paths(root, inputs)
    if staged:
        paths.update(input_paths(root, inputs, index))
    if not raw_config:
        paths.add(CONFIG)
    if requirement is not None:
        if not ID.fullmatch(requirement):
            raise ValueError('需求编号格式应为 REQ-YYYYMMDD-xxxx')
        card = 'requirements/' + requirement + '.md'
        if not (card in index if commit is not None else local_path(root, card).is_file()):
            raise ValueError('需求不存在：' + requirement)
        paths.add(card)
    paths = {name for name in paths if not excluded_input(name)
             and not (requirement is not None and name.startswith('requirements/REQ-')
                      and name.endswith('.md') and name != card)
             and not (inputs is None and requirement is None
                      and name.startswith('requirements/') and Path(name).suffix == '.md')}
    blobs = read_blobs(root, [index[name][1] for name in sorted(paths & index.keys())
                             if index[name][0] in (b'100644', b'100755')]) if index else {}
    files = {}
    for name in sorted(paths):
        path = local_path(root, name)
        if staged or commit is not None:
            entry = index.get(name)
            if entry is None:
                continue
            else:
                mode, oid = entry
                if mode not in (b'100644', b'100755'):
                    raise ValueError('暂存输入不是普通文件：' + name)
                content = blobs[oid]
                if name == CONFIG and not raw_config:
                    try:
                        staged_config = json.loads(content)
                        # 与工作区一致地展开 extends，否则继承的 profile 指纹永远不匹配。
                        staged_config['profiles'] = {name: resolve_profile(staged_config['profiles'], name)
                                                     for name in staged_config['profiles']}
                        content = json.dumps(effective_config(staged_config, profile), sort_keys=True).encode()
                    except (ValueError, KeyError, TypeError) as error:
                        raise ValueError('暂存配置缺少有效的所选 profile') from error
                files[name] = {'sha256': hashlib.sha256(content_for_snapshot(name, content)).hexdigest(), 'executable': mode == b'100755'}
            continue
        if not path.exists():
            continue
        elif path.is_file():
            content = (json.dumps(effective_config(config, profile), sort_keys=True).encode()
                       if name == CONFIG and not raw_config else path.read_bytes())
            files[name] = {'sha256': hashlib.sha256(content_for_snapshot(name, content)).hexdigest(),
                           'executable': bool(path.stat().st_mode & 0o111)}
        else:
            raise ValueError('输入不是普通文件（目录输入需展开，子模块需显式指定文件）：' + name)
    payload = files if checks is None else {'files': files, 'checks': checks}
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True).encode()
    return {'algorithm': 'sha256-files-v4' if checks is None else (algorithm or 'sha256-files-v6'), 'fingerprint': hashlib.sha256(encoded).hexdigest(), 'files': files}


def verify_plan(root, config, profile, requirement, checks):
    settings = config['profiles'][profile]
    if checks is None:
        # 无 checks 的历史证据保持旧算法；新触发配置不得把它升级为全组覆盖。
        if any('covers' in check for check in settings['checks'].values()):
            raise ValueError('触发配置的证据缺少 checks；请重新执行')
        return
    checks = checked_names(settings, checks)
    plan = execution_plan(root, config, profile, requirement)
    if plan['enforced'] and plan['uncovered_engineering_files']:
        raise ValueError('工程改动未被检查覆盖：' + '、'.join(plan['uncovered_engineering_files']))
    missing = set(plan['selected']) - set(checks)
    if missing:
        raise ValueError('验证证据缺少当前触发检查：' + '、'.join(sorted(missing)))


def verify(root, result, staged=False):
    root = root.resolve()
    result = local_path(root, result)
    report = json.loads(result.read_text())
    if not isinstance(report, dict):
        raise ValueError('验证报告必须为 JSON 对象')
    if (report.get('schema_version') != 2 or report.get('status') != '通过'
            or not report.get('completed_at') or not report.get('end_fingerprint')):
        raise ValueError('测试未通过或没有源码绑定证据；请重新执行')
    algorithm = report.get('source', {}).get('algorithm')
    config = load_config(root)
    if report.get('profile') not in config['profiles']:
        raise ValueError('验证报告缺少有效 profile')
    verify_plan(root, config, report['profile'], report.get('requirement'), report.get('checks'))
    if 'checks' in report and report['checks'] != [item['name'] for item in report.get('results', [])
                                                 if item.get('status') == '通过']:
        raise ValueError('报告 checks 与实际通过结果不一致')
    current = source_snapshot(root, config, report['profile'], requirement=report.get('requirement'), checks=report.get('checks'), algorithm=algorithm)
    if report.get('source') != current or report['end_fingerprint'] != current['fingerprint']:
        raise ValueError('测试后源码或配置已变化，旧结果不能用于当前代码')
    if staged and source_snapshot(root, config, report['profile'], staged=True,
                                  requirement=report.get('requirement'), checks=report.get('checks'), algorithm=algorithm) != current:
        raise ValueError('暂存内容与已测试工作区不一致；请暂存正确版本或测试暂存快照')
    return report


def recent_valid_result(root, profile, requirement, required_checks=()):
    """只复用本需求当前仍有效的最近一次运行；失败或缺项不回退更早的通过结果。"""
    config = load_config(root)
    settings = config['profiles'][profile]
    if any(not settings['checks'][name].get('cache', True) for name in required_checks):
        return None
    for run_dir, report in recent_reports(root):
        if report.get('profile') != profile or report.get('requirement') != requirement:
            continue
        if report.get('status') != '通过' or not set(required_checks).issubset(report.get('checks') or []):
            return None
        target = run_dir / 'result.json'
        try:
            verify(root, str(target.relative_to(root.resolve())))
        except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError):
            return None
        return target
    return None


def check_snapshot(root, config, profile, name, requirement=None):
    """缓存键包含执行语义、依赖范围/内容/可执行位以及需求语义。"""
    settings = config['profiles'][profile]
    check = settings['checks'][name]
    inputs = check_inputs(settings, name)
    paths = input_paths(root, inputs)
    if requirement is not None:
        paths.add('requirements/' + requirement + '.md')
    files = {}
    for item in sorted(paths):
        path = local_path(root, item)
        if path.is_file():
            files[item] = {'sha256': hashlib.sha256(content_for_snapshot(item, path.read_bytes())).hexdigest(),
                           'executable': bool(path.stat().st_mode & 0o111)}
        elif path.exists():
            raise ValueError('检查输入不是普通文件：' + item)
    identity = {'version': 2, 'name': name, 'argv': check['argv'], 'cwd': check.get('cwd', '.'),
                'timeout_seconds': check.get('timeout_seconds', 900), 'inputs': inputs,
                'covers': check_coverage(settings, name), 'cache': check.get('cache', True),
                'files': files, 'requirement': requirement}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=True).encode()).hexdigest()


from check_history import (recent_reports, reusable_results, retry_results, recent_duration,
                           estimate_seconds, last_pass)


def run(root, profile, requirement=None, rerun=False, selected=None, announce=None):
    """announce 在启动命令前接收一行计划提示（执行/复用、预计耗时、结果路径）。"""
    root = root.resolve()
    config = load_config(root)
    if profile not in config['profiles']:
        raise ValueError('未配置所选 profile：' + profile)
    settings = config['profiles'][profile]
    plan = execution_plan(root, config, profile, requirement, force=rerun)
    forced = set(checked_names(settings, selected)) if selected is not None else set()
    names = [name for name in settings['checks'] if name in plan['selected'] or name in forced]
    plan.update(selected=names, skipped=[name for name in settings['checks'] if name not in names])
    if plan['enforced'] and plan['uncovered_engineering_files']:
        raise ValueError('工程改动未被检查覆盖：' + '、'.join(plan['uncovered_engineering_files']))
    incremental = bool(settings.get('incremental'))
    source_before = source_snapshot(root, config, profile, requirement=requirement, checks=names) if names else None
    directory = local_path(root, 'logs/project-checks')
    directory.mkdir(parents=True, exist_ok=True)
    ignore = local_path(root, 'logs/project-checks/.gitignore')
    if not ignore.exists():
        ignore.write_text('*\n')
    run_dir = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S.%fZ-') + uuid.uuid4().hex[:8])
    run_dir.mkdir()
    head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'], capture_output=True, text=True)
    report = {'schema_version': 2, 'profile': profile, 'requirement': requirement,
              'started_at': datetime.now(timezone.utc).isoformat(),
              'head': head.stdout.strip() if head.returncode == 0 else None,
              'scope': 'working-tree', 'source': source_before, 'results': [], 'checks': [],
              'status': '未验证', **plan, **({'incremental': True} if incremental else {})}
    results = {}

    def save():
        report['results'] = [results[name] for name in names if name in results]
        report['checks'] = [name for name in names if results.get(name, {}).get('status') == '通过']
        (run_dir / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')

    # incremental 按指纹复用历史通过；未启用时仅在上次失败后复用其通过项，失败项与变化项重跑。
    reuse = {} if rerun else reusable_results(root, profile) if incremental else retry_results(root, profile)
    fingerprints = {name: check_snapshot(root, config, profile, name, requirement) for name in names}

    def previous_log(name):
        check = settings['checks'][name]
        origin = reuse.get(name) if check.get('cache', True) and name not in forced else None
        if not origin or origin[1]['check_fingerprint'] != fingerprints[name]:
            return None
        previous_dir, previous = origin
        # 新报告始终有自己的日志副本；兼容旧报告跨目录的相对引用。
        path = directory / previous_dir / previous['log']
        if not path.is_file():
            path = directory / previous['log']
        return path if path.is_file() else None

    reused_names = [name for name in names if previous_log(name)]
    executed = [name for name in names if name not in reused_names]
    durations = {name: recent_duration(root, profile, name) for name in executed}
    unknown = [name for name, value in durations.items() if value is None]
    report['estimated_seconds'] = (None if unknown else
                                   estimate_seconds(list(durations.values()), settings.get('parallelism', 1)))
    if announce and names:
        line = f"开始验证（{profile}）：执行 {'、'.join(executed) or '无'}"
        if reused_names:
            line += '；复用上次通过 ' + '、'.join(reused_names)
        known = [value for value in durations.values() if value is not None]
        if report['estimated_seconds'] is not None:
            line += f"；预计约 {report['estimated_seconds']} 秒（按最近实际执行）"
        elif known:
            line += (f"；预计至少 {estimate_seconds(known, settings.get('parallelism', 1))} 秒"
                     f"（{'、'.join(unknown)} 无历史）")
        else:
            line += '；预计耗时未知（无历史执行记录）'
        line += (f"。结果：{(run_dir / 'result.json').relative_to(root)}。"
                 '耗时较长时后台运行并等待完成通知，不用固定时长 sleep 轮询')
        announce(line)
    started = time.monotonic()
    save()

    def execute(name):
        check = settings['checks'][name]
        result = {'name': name, 'argv': check['argv'], 'cwd': check.get('cwd', '.'),
                  'log': name + '.log', 'status': '未验证', 'exit_code': None}
        result['check_fingerprint'] = fingerprints[name]
        if name in reused_names:
            previous_dir, previous = reuse[name]
            shutil.copyfile(previous_log(name), run_dir / result['log'])
            result.update(status='通过', exit_code=0, duration_seconds=0.0,
                          original_duration_seconds=previous.get('original_duration_seconds', previous.get('duration_seconds')),
                          reused=True, reused_from=previous.get('reused_from', previous_dir))
            return result
        item_started = time.monotonic()
        try:
            with (run_dir / result['log']).open('wb') as stream:
                process = subprocess.Popen(check['argv'], cwd=local_path(root, result['cwd']),
                                           stdin=subprocess.DEVNULL, stdout=stream,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    result['exit_code'] = process.wait(timeout=check.get('timeout_seconds', 900))
                    result['status'] = '通过' if result['exit_code'] == 0 else '失败'
                except subprocess.TimeoutExpired:
                    try:
                        os.killpg(process.pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
                    process.wait()
                    result['status'] = '超时'
        except OSError as error:
            result.update(status='无法执行', error=str(error))
        result['duration_seconds'] = round(time.monotonic() - item_started, 3)
        return result

    # 默认一个 worker 保留旧顺序；各 worker 独立等待自身进程的超时。
    with ThreadPoolExecutor(max_workers=settings.get('parallelism', 1)) as executor:
        futures = {executor.submit(execute, name): name for name in names}
        for future in as_completed(futures):
            name = futures[future]
            try:
                results[name] = future.result()
            except (OSError, ValueError, KeyError, TypeError) as error:
                results[name] = {'name': name, 'status': '无法执行', 'error': str(error), 'log': name + '.log'}
            save()
    report['status'] = '通过' if names and all(r['status'] == '通过' for r in report['results']) else '失败'
    report['wall_seconds'] = round(time.monotonic() - started, 3)
    if not names:
        report['status'] = '无需检查'
    else:
        unchanged = False
        try:
            source_after = source_snapshot(root, load_config(root), profile, requirement=requirement, checks=names)
            report['end_fingerprint'] = source_after['fingerprint']
            unchanged = source_after == source_before
            if not unchanged:
                before, after = source_before['files'], source_after['files']
                report['source_changes'] = {
                    'added': {n: after[n] for n in sorted(after.keys() - before.keys())},
                    'removed': sorted(before.keys() - after.keys()),
                    'modified': {n: after[n] for n in sorted(before.keys() & after.keys()) if before[n] != after[n]},
                }
        except (OSError, ValueError, KeyError, TypeError) as error:
            report['source_error'] = str(error)
        if not unchanged:
            report['status'] = '输入已变化，需重测'
    report['completed_at'] = datetime.now(timezone.utc).isoformat()
    save()
    return run_dir / 'result.json', report['status'] == '通过'


FAILURE_LINE = re.compile(r'error|fail|fatal|exception|traceback|assert|panic|错误|失败', re.I)


def key_lines(path, limit=8, width=200):
    """失败日志的关键行：优先匹配错误特征的最后几行，否则取末尾几行，省去再次打开完整日志。"""
    try:
        lines = [line.rstrip() for line in path.read_text(errors='replace').splitlines() if line.strip()]
    except OSError:
        return []
    matched = [line for line in lines if FAILURE_LINE.search(line)]
    return [line[:width] for line in (matched or lines)[-limit:]]


def describe_run(root, target):
    """一次运行的简短结论；失败时列出失败项、本地日志及关键错误行。"""
    report = json.loads(target.read_text())
    relative = target.parent.relative_to(root.resolve())
    line = f"验证：{report['status']}（{report['profile']}）"
    failed = [r for r in report['results'] if r['status'] != '通过']
    if failed:
        line += '：' + '、'.join(f"{r['name']} {r['status']}（{relative / r['log']}）" for r in failed)
        for result in failed:
            excerpt = key_lines(target.parent / result['log'])
            if excerpt:
                line += '\n' + result['name'] + ' 关键行：\n' + '\n'.join('  ' + item for item in excerpt)
    elif report['status'] == '无需检查':
        line += '：当前改动未触发项目检查，不生成通过证据'
    elif report['status'] != '通过':
        line += '：运行期间输入变化，请重新验证'
    if failed and any(r['status'] == '通过' for r in report['results']):
        line += '\n修复后再次运行只重跑失败项与输入变化项，本次通过项复用（--rerun 强制全部执行）'
    reused = [r['name'] for r in report['results'] if r.get('reused')]
    if reused:
        line += '\n复用上次通过（未重跑）：' + '、'.join(reused)
    if report.get('skipped'):
        line += '\n未触发：' + '、'.join(report['skipped'])
    return line


def summarize(root, target):
    """写入需求卡的证据摘要：日志留在本地，卡片只保存可复核的指纹。"""
    report = json.loads(target.read_text())
    if report.get('status') != '通过':
        raise ValueError('只有通过结果可生成证据摘要')
    requirement = report.get('requirement')
    card = local_path(root, 'requirements/' + requirement + '.md').read_text()
    summary = {'algorithm': report['source']['algorithm'], **({'checks': report['checks']} if 'checks' in report else {}), 'kind': 'result', 'profile': report['profile'], 'status': report['status'],
            'fingerprint': 'sha256:' + report['end_fingerprint'],
            'requirement': 'sha256:' + hashlib.sha256(semantic_content(card, requirement)).hexdigest(),
            'head': (report.get('head') or '')[:12] or None,
            'at': datetime.now().astimezone().isoformat(timespec='seconds'),
            'log': str(target.relative_to(root.resolve()))}
    return {key: value for key, value in summary.items() if value is not None}


def verify_summary(root, requirement, evidence, staged=False):
    """按卡片摘要重新计算当前（及暂存）输入指纹，不读取日志文件。"""
    root = root.resolve()
    if evidence.get('status') != '通过':
        raise ValueError('已绑定的验证未通过；请重新执行')
    config = load_config(root)
    profile = evidence.get('profile')
    if profile not in config['profiles']:
        raise ValueError('证据中的 profile 已不存在：' + str(profile))
    verify_plan(root, config, profile, requirement, evidence.get('checks'))
    algorithm = evidence.get('algorithm', 'sha256-files-v5')
    current = source_snapshot(root, config, profile, requirement=requirement, checks=evidence.get('checks'), algorithm=algorithm)
    if evidence.get('fingerprint') != 'sha256:' + current['fingerprint']:
        raise ValueError('测试后源码或配置已变化，旧结果不能用于当前代码')
    if staged and source_snapshot(root, config, profile, staged=True,
                                  requirement=requirement, checks=evidence.get('checks'), algorithm=algorithm)['fingerprint'] != current['fingerprint']:
        raise ValueError('暂存内容与已验证工作区不一致；请暂存同一内容或重新验证')
    return current
