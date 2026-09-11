#!/usr/bin/env python3
"""按项目配置执行构建/测试，保存真实退出结果；不猜测 Scheme 或工具链。"""
import argparse
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

CONFIG = '.agents/project-checks.json'


def local_path(root, name):
    path = root / name
    if Path(name).is_absolute() or '..' in Path(name).parts:
        raise ValueError('路径必须位于项目内：' + name)
    for node in (path, *path.parents):
        if node == root:
            break
        if node.is_symlink():
            raise ValueError('路径不能含符号链接：' + name)
    return path


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
EVIDENCE_DIRS = ('logs/project-checks/', 'logs/reviews/', '.agents/teamflow-backups/')


def source_snapshot(root, config, profile=None, staged=False):
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

    paths = set()
    if inputs is not None:
        if not isinstance(inputs, list) or not inputs or any(not isinstance(n, str) or not n for n in inputs):
            raise ValueError('inputs 必须是非空项目相对文件/目录列表')
        inputs = [str(Path(name)) for name in inputs]
        for name in inputs:
            path = local_path(root, name)
            if path.is_dir():
                paths.update(str(p.relative_to(root)) for p in path.rglob('*') if not p.is_dir() or p.is_symlink())
            else:
                paths.add(str(path.relative_to(root)))
    else:
        try:
            raw = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--cached', '--others',
                                           '--exclude-standard', '-z'], stderr=subprocess.PIPE)
            paths.update(os.fsdecode(n) for n in raw.split(b'\0') if n)
        except subprocess.CalledProcessError:
            raise ValueError('非 Git 项目必须显式配置 inputs，避免把构建产物作为源码')
    if staged:
        paths.update(name for name in index if inputs is None or any(
            name == item.rstrip('/') or name.startswith(item.rstrip('/') + '/') or item == '.'
            for item in inputs))
    paths.add(CONFIG)  # profile、命令或输入范围变化也必须令旧证据失效。
    files = {}
    for name in sorted(paths):
        if name.startswith(EVIDENCE_DIRS) or '__pycache__' in Path(name).parts or Path(name).suffix in ('.pyc', '.pyo'):
            continue
        # 默认业务验证忽略需求管理记录；文档验证可通过 inputs 显式纳入。
        if inputs is None and name.startswith('requirements/') and Path(name).suffix in ('.md', '.json'):
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
                files[name] = {'sha256': hashlib.sha256(content).hexdigest(), 'executable': mode == b'100755'}
            continue
        if not path.exists():
            continue
        elif path.is_file():
            files[name] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                           'executable': bool(path.stat().st_mode & 0o111)}
        else:
            raise ValueError('输入不是普通文件（目录输入需展开，子模块需显式指定文件）：' + name)
    encoded = json.dumps(files, sort_keys=True, ensure_ascii=True).encode()
    return {'algorithm': 'sha256-files-v2', 'fingerprint': hashlib.sha256(encoded).hexdigest(), 'files': files}


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
    current = source_snapshot(root, config, report['profile'])
    if report.get('source_before') != current or report.get('source_after') != current:
        raise ValueError('测试后源码或配置已变化，旧结果不能用于当前代码')
    if staged and source_snapshot(root, config, report['profile'], staged=True) != current:
        raise ValueError('暂存内容与已测试工作区不一致；请暂存正确版本或测试暂存快照')
    print('验证结果与当前源码/配置' + ('及暂存区' if staged else '') + '一致：' + str(result))
    return report


def run(root, profile):
    root = root.resolve()
    config = load_config(root)
    if profile not in config['profiles']:
        raise ValueError('未配置所选 profile：' + profile)
    source_before = source_snapshot(root, config, profile)
    directory = local_path(root, 'logs/project-checks')
    directory.mkdir(parents=True, exist_ok=True)
    run_dir = directory / (datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ-') + uuid.uuid4().hex[:8])
    run_dir.mkdir()
    head = subprocess.run(['git', '-C', str(root), 'rev-parse', 'HEAD'],
                          capture_output=True, text=True)
    report = {'schema_version': 1, 'profile': profile,
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
        report['source_after'] = source_snapshot(root, load_config(root), profile)
        report['source_unchanged'] = report['source_after'] == source_before
    except (OSError, ValueError) as error:
        report['source_unchanged'] = False
        report['source_error'] = str(error)
    if not report['source_unchanged']:
        report['status'] = '输入已变化，需重测'
    report['completed_at'] = datetime.now(timezone.utc).isoformat()
    target = run_dir / 'result.json'
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('验证证据：' + str(target))
    return target, report['status'] == '通过'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('.'))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('init')
    sub.add_parser('list')
    verifier = sub.add_parser('verify')
    verifier.add_argument('--result', required=True, help='项目相对 result.json 路径')
    verifier.add_argument('--staged', action='store_true', help='同时核对暂存对象；提交前必须使用')
    runner = sub.add_parser('run')
    runner.add_argument('--profile', required=True)
    args = parser.parse_args()
    try:
        root = args.project.resolve()
        if args.command == 'init':
            path = local_path(root, CONFIG)
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open('x') as stream:
                json.dump({'schema_version': 1, 'checks': {}, 'profiles': {}}, stream, indent=2)
                stream.write('\n')
            print('已创建空配置，请填写实际命令；空配置不能执行成功：' + str(path))
        elif args.command == 'verify':
            verify(root, args.result, args.staged)
        elif args.command == 'list':
            print(json.dumps(load_config(root), ensure_ascii=False, indent=2))
        else:
            _, passed = run(root, args.profile)
            return 0 if passed else 1
    except (ValueError, OSError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(2, str(error) + '\n')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
