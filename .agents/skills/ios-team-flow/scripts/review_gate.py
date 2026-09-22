#!/usr/bin/env python3
"""对暂存提交生成审查快照、复用已完成报告；不执行 AI 语义审查。"""
import argparse
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

CATEGORIES = ('correctness', 'standards', 'subscription', 'memory', 'analytics',
              'test_artifacts', 'security')
CORE_CATEGORIES = ('correctness', 'standards', 'security')
OPTIONAL_CATEGORIES = tuple(name for name in CATEGORIES if name not in CORE_CATEGORIES)
RECEIPTS = 'logs/reviews/'
SOURCE_SUFFIXES = ('.swift', '.m', '.mm', '.h', '.c', '.cc', '.cpp', '.hpp')
KNOWN_SUFFIXES = SOURCE_SUFFIXES + ('.md', '.txt', '.json', '.plist', '.strings', '.xcconfig',
                                    '.pbxproj', '.xcscheme', '.yaml', '.yml', '.toml', '.lock', '.py',
                                    '.sh', '.rb', '.js', '.ts', '.tsx', '.jsx', '.html', '.css', '.xml')
RISK_TERMS = {
    'subscription': ('storekit', 'subscription', 'productid', 'product_id', 'purchase', 'iap', '订阅', '购买', '商品'),
    'analytics': ('analytics', 'tracking', 'trackevent', 'event_name', '埋点', '打点'),
}


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


def review_route(root, patch, full=False, risks=()):
    """按暂存路径与内容选择审查维度；未知范围保守回退完整审查。"""
    requested = set(risks)
    if requested - set(OPTIONAL_CATEGORIES):
        raise ValueError('未知风险维度：' + ', '.join(sorted(requested - set(OPTIONAL_CATEGORIES))))
    names = [name for name in git(root, 'diff', '--cached', '--name-only', '-z', '--', '.',
                                  ':(exclude)' + RECEIPTS + '**').decode().split('\0') if name]
    required = set(CORE_CATEGORIES) | requested
    reasons = {name: '显式指定风险维度' for name in requested}
    unknown = len(names) > 50
    for name in names:
        suffix = Path(name).suffix.lower()
        if suffix not in KNOWN_SUFFIXES and suffix not in ('.png', '.jpg', '.jpeg', '.gif', '.pdf', '.xcassets'):
            unknown = True
        if suffix in SOURCE_SUFFIXES:
            required.update(('memory', 'test_artifacts'))
            reasons.setdefault('memory', '暂存范围包含运行时源码')
            reasons.setdefault('test_artifacts', '暂存范围包含生产源码')
        elif suffix in ('.py', '.sh', '.rb', '.js', '.ts', '.tsx', '.jsx', '.plist', '.xcconfig',
                        '.pbxproj', '.xcscheme', '.json'):
            required.add('test_artifacts')
            reasons.setdefault('test_artifacts', '暂存范围包含可执行脚本或运行配置')
    lowered = patch.lower()
    for category, terms in RISK_TERMS.items():
        if any(term.encode() in lowered for term in terms):
            required.add(category)
            reasons.setdefault(category, '暂存差异命中' + category + '风险信号')
    if full or unknown:
        required = set(CATEGORIES)
        reason = '显式要求完整审查' if full else '暂存范围包含未知类型或文件过多，保守执行完整审查'
        reasons.update({name: reason for name in OPTIONAL_CATEGORIES})
    return [name for name in CATEGORIES if name in required], reasons


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
    required = report.get('required_checks', list(CATEGORIES))
    if (not isinstance(required, list) or not required or len(set(required)) != len(required)
            or any(name not in CATEGORIES for name in required)
            or any(name not in required for name in CORE_CATEGORIES)):
        return errors + ['required_checks 必须包含全部核心维度且只能使用已知维度']
    for name in required:
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


def continue_review(root, report, previous, tree):
    """携带同一 HEAD 下的前次审查材料；所有维度仍须确认，不能继承批准。"""
    if len(previous) != 64 or any(c not in '0123456789abcdef' for c in previous):
        raise ValueError('continue-from 必须是完整审查指纹')
    source = root / RECEIPTS / (previous + '.json')
    prior = json.loads(source.read_text())
    if not isinstance(prior, dict) or prior.get('base') != report['base']:
        raise ValueError('续审要求相同 HEAD；基准变化后重新审查')
    old_tree = prior.get('snapshot_tree', '')
    if not isinstance(old_tree, str) or len(old_tree) not in (40, 64) or any(c not in '0123456789abcdef' for c in old_tree):
        raise ValueError('前次报告缺少有效暂存树快照，不能续审')
    diff_args = ('diff', '--binary', '--full-index', '--no-ext-diff', '--no-textconv', '--no-renames')
    scope = ('--', '.', ':(exclude)logs/reviews/**')
    prior_patch = git(root, *diff_args, report['base'], old_tree, *scope)
    if (prior.get('fingerprint') != previous
            or hashlib.sha256(report['base'].encode() + b'\0' + prior_patch).hexdigest() != previous):
        raise ValueError('前次暂存树与审查快照不匹配')
    checks = prior.get('checks')
    prior_required = prior.get('required_checks', list(CATEGORIES))
    if (not isinstance(checks, dict)
            or any(not isinstance(checks.get(name), dict) for name in prior_required)):
        raise ValueError('前次报告缺少所需审查材料')
    for key in ('requirements', 'validation_results', 'findings', 'blockers'):
        if not isinstance(prior.get(key), list):
            raise ValueError('前次报告缺少列表：' + key)
        report[key] = copy.deepcopy(prior[key])
    for name in report['required_checks']:
        old = checks.get(name, {})
        report['checks'][name] = {'status': '未验证', 'evidence': old.get('evidence', ''),
                                  'previous_status': old.get('status', '未验证')}
    report['previous_review'] = previous
    report['previous_tree'] = old_tree


def prepare(root, previous=None, continue_from=None, full=False, risks=()):
    if previous and continue_from:
        raise ValueError('归档继承与修复续审不能同时使用')
    base, patch, fingerprint = snapshot(root)
    required, routing = review_route(root, patch, full, risks)
    directory = root / RECEIPTS
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (fingerprint + '.json')
    if target.exists():
        report = json.loads(target.read_text())
        missing = [name for name in required if name not in report.get('required_checks', list(CATEGORIES))]
        if missing:
            report['required_checks'] = [name for name in CATEGORIES
                                         if name in set(report.get('required_checks', list(CATEGORIES))) | set(required)]
            report.setdefault('checks', {}).update({name: {'status': '未验证', 'evidence': ''} for name in missing})
            report.setdefault('routing_reasons', {}).update(routing)
            target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        print('复用已完成审查' if not report_errors(report, base, fingerprint) else '继续未完成审查')
    else:
        report = {
            'fingerprint': fingerprint, 'base': base, 'scope': 'staged',
            'snapshot_tree': git(root, 'write-tree').decode().strip(),
            'created_at': datetime.now(timezone.utc).isoformat(),
            'reviewer': '', 'completed_at': '', 'summary': '', 'previous_review': None,
            'required_checks': required, 'routing_reasons': routing,
            'checks': {name: {'status': '未验证', 'evidence': ''} for name in required},
            'findings': [], 'blockers': [], 'requirements': [], 'validation_results': []
        }
        if continue_from:
            continue_review(root, report, continue_from, report['snapshot_tree'])
        if previous:
            if len(previous) != 64 or any(c not in '0123456789abcdef' for c in previous):
                raise ValueError('previous 必须是完整审查指纹')
            names = git(root, 'diff', '--cached', '--name-only', '-z').decode().split('\0')
            if any(n and not (n.startswith(('requirements/delivery/', RECEIPTS)) or n == 'requirements/DELIVERY.md') for n in names):
                raise ValueError('自动继承仅用于生成交付记录归档，实施变化须重新审查')
            prior = json.loads(git(root, 'show', 'HEAD:' + RECEIPTS + previous + '.json'))
            if report_errors(prior, prior.get('base'), previous):
                raise ValueError('前次报告未完成，不能继承')
            reviewed_patch = git(root, 'diff', '--binary', '--full-index', '--no-ext-diff', '--no-textconv',
                                 '--no-renames', prior['base'], 'HEAD', '--', '.', ':(exclude)logs/reviews/**')
            if hashlib.sha256(prior['base'].encode() + b'\0' + reviewed_patch).hexdigest() != previous:
                raise ValueError('前次报告不覆盖当前 HEAD，不能自动继承')
            report['previous_review'] = previous
            report['requirements'] = prior.get('requirements', [])
            for category in report['required_checks']:
                if category not in CORE_CATEGORIES:
                    old = prior.get('checks', {}).get(category)
                    if old:
                        report['checks'][category] = {'status': old['status'],
                            'evidence': '复用 ' + previous + ' 的 ' + category + '；仅生成记录归档，无业务变化。'}
        # 不覆盖已有报告；并发创建同一指纹时由后续调用续接。
        with target.open('x') as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
        print('需要 Codex 审查并填写报告')
    unstaged = bool(git(root, 'diff', '--name-only', '-z'))
    untracked = len(list(filter(None, git(root, 'ls-files', '--others', '--exclude-standard', '-z').split(b'\0'))))
    print(json.dumps({'fingerprint': fingerprint, 'report': str(target),
                      'snapshot_tree': report.get('snapshot_tree'), 'required_checks': report.get('required_checks'),
                      'diff_command': 'git diff --cached --binary -- . ":(exclude)logs/reviews/**"',
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
    expected, _ = review_route(root, patch)
    reported = report.get('required_checks', list(CATEGORIES))
    if isinstance(reported, list) and not set(expected) <= set(reported):
        errors.append('报告缺少自动风险路由维度：' + ', '.join(name for name in expected if name not in reported))
    if report.get('scope') != 'staged':
        errors.append('提交报告 scope 必须为 staged')
    if errors:
        raise ValueError('；'.join(errors))
    if report.get('validation_results'):
        spec = importlib.util.spec_from_file_location('teamflow_project_checks',
                                                      Path(__file__).with_name('project_checks.py'))
        checks = importlib.util.module_from_spec(spec)
        previous_bytecode = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = True
            spec.loader.exec_module(checks)
        finally:
            sys.dont_write_bytecode = previous_bytecode
        for result in report['validation_results']:
            path = checks.local_path(root, result)
            if git(root, 'show', ':' + result) != path.read_bytes():
                raise ValueError('验证报告暂存版本与工作区不一致：' + result)
            checks.verify(root, result, staged=True)
    print('审查门禁通过，复用指纹：' + fingerprint)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'check'))
    continuation = parser.add_mutually_exclusive_group()
    continuation.add_argument('--previous', help='仅归档记录时复用已提交的完成报告')
    continuation.add_argument('--continue-from', help='修复后携带同一 HEAD 下的前次材料并生成差量；需要重新确认')
    parser.add_argument('--full', action='store_true', help='prepare 时显式执行完整七维审查')
    parser.add_argument('--risk', action='append', choices=OPTIONAL_CATEGORIES, default=[],
                        help='prepare 时显式增加风险维度；可重复')
    args = parser.parse_args()
    try:
        if args.command == 'prepare':
            prepare(repo_root(), args.previous, args.continue_from, args.full, args.risk)
        elif args.previous or args.continue_from or args.full or args.risk:
            raise ValueError('--previous / --continue-from / --full / --risk 仅用于 prepare')
        else:
            check(repo_root())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        parser.exit(1, '审查门禁：' + str(error) + '\n')


if __name__ == '__main__':
    main()
