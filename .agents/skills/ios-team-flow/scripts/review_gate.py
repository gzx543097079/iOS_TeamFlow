#!/usr/bin/env python3
"""对暂存提交生成审查快照、复用已完成报告；不执行 AI 语义审查。"""
import argparse
import hashlib
import importlib.util
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = ('correctness', 'standards', 'subscription', 'memory', 'analytics',
              'test_artifacts', 'security')
RECEIPTS = 'logs/reviews/'


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.PIPE)


def repo_root():
    return Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip())


def snapshot(root):
    try:
        base = git(root, 'rev-parse', '--verify', 'HEAD').decode().strip()
    except subprocess.CalledProcessError:
        base = subprocess.check_output(['git', '-C', str(root), 'hash-object', '-t', 'tree', '--stdin'],
                                       input=b'').decode().strip()
    # 拒绝把可执行/业务文件藏进排除目录；NUL 分隔兼容空格和换行文件名。
    entries = git(root, 'ls-files', '--stage', '-z', '--', RECEIPTS).split(b'\0')
    for entry in filter(None, entries):
        metadata, name = entry.split(b'\t', 1)
        path = Path(name.decode())
        mode = metadata.split()[0]
        if path.suffix not in ('.json', '.patch', '.md') or mode != b'100644':
            raise ValueError('审查回执目录只能存放普通 JSON、patch、Markdown 文件：' + str(path))
    patch = git(root, 'diff', '--cached', '--binary', '--full-index', '--no-ext-diff',
                '--no-textconv', '--no-renames', base, '--', '.', ':(exclude)logs/reviews/**')
    fingerprint = hashlib.sha256(base.encode() + b'\0' + patch).hexdigest()
    return base, patch, fingerprint


def report_errors(report, base, fingerprint):
    if not isinstance(report, dict):
        return ['报告必须为 JSON 对象']
    errors = []
    if report.get('fingerprint') != fingerprint or report.get('base') != base:
        errors.append('报告不匹配当前 HEAD / 暂存内容')
    for key in ('reviewer', 'completed_at', 'summary'):
        if not isinstance(report.get(key), str) or not report[key].strip():
            errors.append('缺少字段：' + key)
    checks = report.get('checks', {})
    if not isinstance(checks, dict):
        return errors + ['checks 必须为对象']
    for name in CATEGORIES:
        item = checks.get(name, {})
        if not isinstance(item, dict):
            errors.append(name + ' 格式错误')
            continue
        if item.get('status') not in ('通过', '不适用'):
            errors.append(name + ' 尚未通过')
        if not isinstance(item.get('evidence'), str) or not item['evidence'].strip():
            errors.append(name + ' 缺少证据/不适用理由')
    if report.get('blockers') != []:
        errors.append('存在阻塞项或缺少 blockers 列表')
    findings = report.get('findings')
    if not isinstance(findings, list):
        errors.append('findings 必须为列表')
    else:
        for item in findings:
            if not isinstance(item, dict) or item.get('status') not in ('fixed', 'accepted'):
                errors.append('存在未关闭问题或问题格式错误')
            elif item['status'] == 'accepted' and not (item.get('reason') and item.get('accepted_by')):
                errors.append('接受的问题缺少原因/确认人')
    for key in ('requirements', 'validation_results'):
        values = report.get(key, [])  # 旧回执兼容；新回执由 prepare 初始化。
        if not isinstance(values, list) or any(not isinstance(v, str) or not v.strip() for v in values):
            errors.append(key + ' 必须为非空字符串组成的数组')
    return errors


def prepare(root):
    base, patch, fingerprint = snapshot(root)
    directory = root / RECEIPTS
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (fingerprint + '.json')
    if target.exists():
        report = json.loads(target.read_text())
        print('复用已完成审查' if not report_errors(report, base, fingerprint) else '继续未完成审查')
    else:
        report = {
            'fingerprint': fingerprint, 'base': base, 'scope': 'staged',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'reviewer': '', 'completed_at': '', 'summary': '', 'previous_review': None,
            'checks': {name: {'status': '未验证', 'evidence': ''} for name in CATEGORIES},
            'findings': [], 'blockers': [], 'requirements': [], 'validation_results': []
        }
        # 不覆盖已有报告；并发创建同一指纹时由后续调用续接。
        with target.open('x') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        print('需要 Codex 审查并填写报告')
    (directory / (fingerprint + '.patch')).write_bytes(patch)
    unstaged = bool(git(root, 'diff', '--name-only', '-z'))
    untracked = len(list(filter(None, git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0'))))
    print(json.dumps({'fingerprint': fingerprint, 'report': str(target),
                      'patch': str(directory / (fingerprint + '.patch')),
                      'unstaged_changes': unstaged, 'untracked_count': untracked}, ensure_ascii=False))
    return target


def check(root):
    base, patch, fingerprint = snapshot(root)
    # 只有回执改动时不让回执审查自身；依旧执行上面的格式边界检查。
    if not patch:
        print('没有待审业务/规则改动；仅回执或空暂存区')
        return
    name = RECEIPTS + fingerprint + '.json'
    try:
        report = json.loads(git(root, 'show', ':' + name))
    except subprocess.CalledProcessError as error:
        raise ValueError('缺少已暂存的审查报告；完成报告后 git add ' + name) from error
    errors = report_errors(report, base, fingerprint)
    if report.get('scope') != 'staged':
        errors.append('提交报告 scope 必须为 staged')
    if errors:
        raise ValueError('；'.join(errors))
    if report.get('validation_results'):
        spec = importlib.util.spec_from_file_location('teamflow_project_checks',
                                                      Path(__file__).with_name('project_checks.py'))
        checks = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checks)
        for result in report['validation_results']:
            path = checks.local_path(root, result)
            if git(root, 'show', ':' + result) != path.read_bytes():
                raise ValueError('验证报告暂存版本与工作区不一致：' + result)
            checks.verify(root, result, staged=True)
    print('审查门禁通过，复用指纹：' + fingerprint)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'check'))
    args = parser.parse_args()
    try:
        (prepare if args.command == 'prepare' else check)(repo_root())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, '审查门禁：' + str(error) + '\n')


if __name__ == '__main__':
    main()
