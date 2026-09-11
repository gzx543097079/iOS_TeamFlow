#!/usr/bin/env python3
"""校验明确 Git 提交范围的审查证据，不读取本地暂存区。"""
import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
import importlib.util

_spec = importlib.util.spec_from_file_location('teamflow_trusted_gate', Path(__file__).with_name('review_gate.py'))
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def resolve(root, ref):
    return gate.git(root, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}').decode().strip()


def diff(root, base, head):
    return gate.git(root, 'diff', '--binary', '--full-index', '--no-ext-diff', '--no-textconv',
                    '--no-renames', base, head, '--', '.', ':(exclude)logs/reviews/**')


def scope(root, base_ref, head_ref):
    base, head = resolve(root, base_ref), resolve(root, head_ref)
    common = gate.git(root, 'merge-base', base, head).decode().strip()
    patch = diff(root, common, head)
    fingerprint = hashlib.sha256(b'range-v1\0' + base.encode() + b'\0' + common.encode() + b'\0' + patch).hexdigest()
    return base, head, common, patch, fingerprint


def validate_receipts(root, head):
    entries = gate.git(root, 'ls-tree', '-r', '-z', head, '--', gate.RECEIPTS).split(b'\0')
    for entry in filter(None, entries):
        metadata, raw_name = entry.split(b'\t', 1)
        mode, kind, _ = metadata.split()
        if mode != b'100644' or kind != b'blob' or Path(raw_name.decode()).suffix not in ('.json', '.md', '.patch'):
            raise ValueError('提交范围的回执目录包含非回执文件：' + raw_name.decode())


def read_report(root, head, fingerprint):
    try:
        raw = gate.git(root, 'show', head + ':' + gate.RECEIPTS + fingerprint + '.json')
    except subprocess.CalledProcessError:
        return None
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError('审查报告必须为 JSON 对象')
    return value


def check(root, base_ref, head_ref):
    base, head, common, patch, fingerprint = scope(root, base_ref, head_ref)
    validate_receipts(root, head)
    if not patch:
        print('明确提交范围没有净业务/规则改动；回执边界已检查')
        return
    aggregate = read_report(root, head, fingerprint)
    if aggregate is not None:
        errors = gate.report_errors(aggregate, base, fingerprint)
        if aggregate.get('scope') != 'range' or aggregate.get('diff_base') != common:
            errors.append('范围报告的 scope/diff_base 不匹配')
        reviewed = aggregate.get('reviewed_head')
        try:
            reviewed = resolve(root, reviewed) if isinstance(reviewed, str) else ''
            if not reviewed or subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', reviewed, head],
                                               capture_output=True).returncode != 0:
                errors.append('已审 head 不是当前 head 的祖先')
            elif diff(root, common, reviewed) != patch:
                errors.append('报告生成后业务内容发生变化')
        except subprocess.CalledProcessError:
            errors.append('已审 head 不可解析')
        if errors:
            raise ValueError('；'.join(errors))
        print('范围审查通过，复用报告：' + fingerprint)
        return
    # 线性提交可复用已提交的逐次暂存审查，不要求重复审查同一改动。
    for commit in gate.git(root, 'rev-list', '--reverse', '--topo-order', common + '..' + head).decode().splitlines():
        ancestry = gate.git(root, 'rev-list', '--parents', '-n', '1', commit).decode().split()
        if len(ancestry) < 2:
            raise ValueError('范围包含无父提交，需生成明确范围审查')
        parent = ancestry[1]
        delta = diff(root, parent, commit)
        if not delta:
            continue
        if len(ancestry) != 2:
            raise ValueError('范围包含合并提交，请 prepare 生成范围审查并记录合并影响：' + commit)
        commit_fingerprint = hashlib.sha256(parent.encode() + b'\0' + delta).hexdigest()
        report = read_report(root, head, commit_fingerprint)
        if report is None:
            raise ValueError('缺少提交审查：' + commit + '；请提交原回执或生成范围审查')
        errors = gate.report_errors(report, parent, commit_fingerprint)
        if report.get('scope') != 'staged':
            errors.append('逐提交报告 scope 必须为 staged')
        if errors:
            raise ValueError(commit + '：' + '；'.join(errors))
    print('范围审查通过：已复用每个实施提交的审查报告；base=' + base + ' head=' + head)


def prepare(root, base_ref, head_ref):
    base, head, common, patch, fingerprint = scope(root, base_ref, head_ref)
    validate_receipts(root, head)
    directory = root / gate.RECEIPTS
    for node in (directory, directory.parent):
        if node.is_symlink():
            raise ValueError('回执目录不能为符号链接')
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (fingerprint + '.json')
    snapshot = directory / (fingerprint + '.patch')
    if target.is_symlink() or snapshot.is_symlink():
        raise ValueError('回执文件不能为符号链接')
    if not target.exists():
        report = {'fingerprint': fingerprint, 'base': base, 'scope': 'range', 'diff_base': common,
                  'reviewed_head': head, 'created_at': datetime.now(timezone.utc).isoformat(),
                  'reviewer': '', 'completed_at': '', 'summary': '', 'previous_review': None,
                  'checks': {name: {'status': '未验证', 'evidence': ''} for name in gate.CATEGORIES},
                  'findings': [], 'blockers': []}
        with target.open('x') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    snapshot.write_bytes(patch)
    print('范围报告：' + str(target) + '；审查完成后提交回执，再以新 head 执行 check')
    return target


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'check'))
    parser.add_argument('--base', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--project', type=Path, default=Path('.'))
    args = parser.parse_args()
    try:
        root = args.project.resolve()
        (prepare if args.command == 'prepare' else check)(root, args.base, args.head)
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, '范围审查失败：' + str(error) + '\n')


if __name__ == '__main__':
    main()
