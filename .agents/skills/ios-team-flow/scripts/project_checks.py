#!/usr/bin/env python3
"""按项目配置执行构建/测试，保存真实退出结果；不猜测 Scheme 或工具链。"""
import hashlib
import json
import os
import re
import signal
import subprocess
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from teamflow_common import local_path

CONFIG = '.agents/project-checks.json'


def load_config(root):
    config = json.loads(local_path(root, CONFIG).read_text())
    if not isinstance(config, dict) or config.get('schema_version') != 1:
        raise ValueError('配置 schema_version 必须为 1')
    checks, profiles = config.get('checks'), config.get('profiles')
    if not isinstance(checks, dict) or not isinstance(profiles, dict):
        raise ValueError('checks 和 profiles 必须为对象')
    for name, check in checks.items():
        if not re.fullmatch(r'[a-zA-Z0-9_-]+', name) or not isinstance(check, dict):
            raise ValueError('检查名称或配置无效')
        argv = check.get('argv')
        if (not isinstance(argv, list) or not argv
                or any(not isinstance(arg, str) or not arg or '\0' in arg for arg in argv)):
            raise ValueError(name + ' 的 argv 必须为非空字符串数组')
        timeout = check.get('timeout_seconds', 900)
        if type(timeout) is not int or not 1 <= timeout <= 86400:
            raise ValueError(name + ' 的 timeout_seconds 必须为 1–86400')
        cwd = local_path(root, check.get('cwd', '.'))
        if not cwd.is_dir():
            raise ValueError(name + ' 的工作目录不存在')
    for name, selected in profiles.items():
        if (not isinstance(selected, list) or not selected
                or any(not isinstance(n, str) or n not in checks for n in selected)
                or len(selected) != len(set(selected))):
            raise ValueError('profile 必须包含不重复的有效检查：' + name)
    return config


# 自动生成的证据不参与源码指纹，避免报告写入令自身失效。
EVIDENCE_DIRS = ('logs/project-checks/', '.agents/teamflow-backups/', 'releases/')


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
            local_path(root, name)
        inputs = [str(Path(n)) for n in inputs]
    validate_inputs = candidates is None
    if candidates is None:
        try:
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
    """需求卡只绑定范围和 AC；状态、验证与异常记录不令既有测试自失效。"""
    if not (name.startswith('requirements/REQ-') and name.endswith('.md')):
        return content
    text = content.decode('utf-8')
    if '<!-- teamflow:requirement:vnext -->' not in text:
        return content
    lines = []
    ignored_section = False
    for line in text.splitlines():
        if line.startswith('## '):
            ignored_section = line in ('## 验证', '## 决策与异常')
        if ignored_section or re.match(r'^- 状态：', line):
            continue
        match = re.match(r'^- (?:⚪|✅) (AC-\d+：.+)$', line)
        if match:
            line = '- ' + match.group(1)
        lines.append(line)
    return ('\n'.join(lines) + '\n').encode('utf-8')


def effective_config(config, profile):
    """仅绑定所选检查的执行语义，其他 profile 和 JSON 排版不影响证据。"""
    selected = config['profiles'][profile]
    return {'inputs': config.get('profile_inputs', {}).get(profile, config.get('inputs')),
            'checks': [{'name': name, 'argv': config['checks'][name]['argv'],
                        'cwd': config['checks'][name].get('cwd', '.'),
                        'timeout_seconds': config['checks'][name].get('timeout_seconds', 900)}
                       for name in selected]}


def source_snapshot(root, config, profile=None, staged=False, requirement=None):
    overrides = config.get('profile_inputs', {})
    if not isinstance(overrides, dict) or any(k not in config['profiles'] for k in overrides):
        raise ValueError('profile_inputs 必须引用已配置的 profile')
    inputs = overrides.get(profile, config.get('inputs'))
    index = {}
    if staged:
        raw = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--stage', '-z'],
                                      stderr=subprocess.PIPE)
        for entry in filter(None, raw.split(b'\0')):
            metadata, name = entry.split(b'\t', 1)
            mode, oid, stage = metadata.split()
            if stage != b'0':
                raise ValueError('暂存区有未解决冲突')
            index[os.fsdecode(name)] = (mode, oid)

    paths = input_paths(root, inputs)
    if staged:
        paths.update(input_paths(root, inputs, index))
    paths.add(CONFIG)
    if requirement is not None:
        if not re.fullmatch(r'REQ-\d{4}', requirement):
            raise ValueError('需求编号格式应为 REQ-0001')
        card = 'requirements/' + requirement + '.md'
        if not local_path(root, card).is_file():
            raise ValueError('需求不存在：' + requirement)
        paths.add(card)
    files = {}
    for name in sorted(paths):
        if excluded_input(name):
            continue
        # 绑定需求时仅排除其他卡片；显式选择的稳定工程现状仍是验证输入。
        if (requirement is not None and name.startswith('requirements/REQ-')
                and name.endswith('.md') and name != card):
            continue
        if inputs is None and requirement is None and name.startswith('requirements/') and Path(name).suffix == '.md':
            continue
        path = local_path(root, name)
        if staged:
            entry = index.get(name)
            if entry is None:
                continue
            else:
                mode, oid = entry
                if mode not in (b'100644', b'100755'):
                    raise ValueError('暂存输入不是普通文件：' + name)
                content = subprocess.check_output(['git', '-C', str(root), 'cat-file', 'blob', oid.decode()],
                                                  stderr=subprocess.PIPE)
                if name == CONFIG:
                    try:
                        content = json.dumps(effective_config(json.loads(content), profile), sort_keys=True).encode()
                    except (ValueError, KeyError, TypeError) as error:
                        raise ValueError('暂存配置缺少有效的所选 profile') from error
                files[name] = {'sha256': hashlib.sha256(content_for_snapshot(name, content)).hexdigest(), 'executable': mode == b'100755'}
            continue
        if not path.exists():
            continue
        elif path.is_file():
            content = (json.dumps(effective_config(config, profile), sort_keys=True).encode()
                       if name == CONFIG else path.read_bytes())
            files[name] = {'sha256': hashlib.sha256(content_for_snapshot(name, content)).hexdigest(),
                           'executable': bool(path.stat().st_mode & 0o111)}
        else:
            raise ValueError('输入不是普通文件（目录输入需展开，子模块需显式指定文件）：' + name)
    encoded = json.dumps(files, sort_keys=True, ensure_ascii=True).encode()
    return {'algorithm': 'sha256-files-v4', 'fingerprint': hashlib.sha256(encoded).hexdigest(), 'files': files}


def verify(root, result, staged=False):
    root = root.resolve()
    result = local_path(root, result)
    report = json.loads(result.read_text())
    if not isinstance(report, dict):
        raise ValueError('验证报告必须为 JSON 对象')
    if report.get('status') != '通过' or not report.get('source_unchanged') or not report.get('completed_at'):
        raise ValueError('测试未通过或没有源码绑定证据；请重新执行')
    config = load_config(root)
    if report.get('profile') not in config['profiles']:
        raise ValueError('验证报告缺少有效 profile')
    current = source_snapshot(root, config, report['profile'], requirement=report.get('requirement'))
    if report.get('source_before') != current or report.get('source_after') != current:
        raise ValueError('测试后源码或配置已变化，旧结果不能用于当前代码')
    if staged and source_snapshot(root, config, report['profile'], staged=True,
                                  requirement=report.get('requirement')) != current:
        raise ValueError('暂存内容与已测试工作区不一致；请暂存正确版本或测试暂存快照')
    print('验证结果与当前源码/配置' + ('及暂存区' if staged else '') + '一致：' + str(result))
    return report


def run(root, profile, requirement=None):
    root = root.resolve()
    config = load_config(root)
    if profile not in config['profiles']:
        raise ValueError('未配置所选 profile：' + profile)
    source_before = source_snapshot(root, config, profile, requirement=requirement)
    directory = local_path(root, 'logs/project-checks')
    directory.mkdir(parents=True, exist_ok=True)
    run_dir = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8])
    run_dir.mkdir()
    head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                          capture_output=True, text=True)
    report = {'schema_version': 1, 'profile': profile, 'requirement': requirement,
              'started_at': datetime.now(timezone.utc).isoformat(),
              'head': head.stdout.strip() if head.returncode == 0 else None,
              'scope': 'working-tree', 'source_before': source_before, 'results': [], 'status': '未验证'}
    # 配置和命令属于团队明确选定的可执行代码；不使用 shell，不代入需求中的任意文本。
    for name in config['profiles'][profile]:
        check = config['checks'][name]
        start = time.monotonic()
        result = {'name': name, 'argv': check['argv'], 'cwd': check.get('cwd', '.'),
                  'log': name + '.log', 'status': '未验证', 'exit_code': None}
        with (run_dir / result['log']).open('wb') as stream:
            try:
                process = subprocess.Popen(check['argv'], cwd=local_path(root, result['cwd']),
                                           stdin=subprocess.DEVNULL, stdout=stream,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                try:
                    result['exit_code'] = process.wait(timeout=check.get('timeout_seconds', 900))
                    result['status'] = '通过' if result['exit_code'] == 0 else '失败'
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                    result['status'] = '超时'
            except OSError as error:
                result.update(status='无法执行', error=str(error))
        result['duration_seconds'] = round(time.monotonic() - start, 3)
        report['results'].append(result)
        print(name + '：' + result['status'])
        # 每个所选检查都是本次必跑项；失败后仍收集其余检查结果。
        (run_dir / 'result.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    report['status'] = '通过' if all(r['status'] == '通过' for r in report['results']) else '失败'
    try:
        report['source_after'] = source_snapshot(root, load_config(root), profile, requirement=requirement)
        report['source_unchanged'] = report['source_after'] == source_before
    except (OSError, ValueError, KeyError, TypeError) as error:
        report['source_unchanged'] = False
        report['source_error'] = str(error)
    if not report['source_unchanged']:
        report['status'] = '输入已变化，需重测'
    report['completed_at'] = datetime.now(timezone.utc).isoformat()
    target = run_dir / 'result.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('验证证据：' + str(target))
    return target, report['status'] == '通过'
