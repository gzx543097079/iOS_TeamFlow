#!/usr/bin/env python3
"""以需求标记、Git 提交和可选 GitHub 只读证据生成交付概览。"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import uuid
import importlib.util
import sys
import contextlib
import io
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ID = re.compile(r'REQ-\d{8}-\d{9}Z-[0-9a-f]{8}')
CARD_V2 = '<!-- teamflow:requirement:v2 -->'
CARD_V3 = '<!-- teamflow:requirement:v3 -->'
STATES = ('❔ 待确认', '⬜ 未执行', '🔄 执行中', '🧪 待验证', '✅ 执行完成',
          '⛔ 阻塞', '⏸️ 已暂停', '🚫 已取消')


def card_state(root, requirement):
    """新版需求卡是唯一人工状态源；校验结构与一致性，不代替语义验收。"""
    text = safe_path(root, 'requirements/' + requirement + '.md').read_text()
    if CARD_V2 not in text and CARD_V3 not in text:
        return None
    def field(name):
        values = re.findall(r'^- ' + re.escape(name) + r'：(.+)$', text, re.M)
        if len(values) != 1 or not values[0].strip():
            raise ValueError(requirement + ' 必须且只能填写一处：' + name)
        return values[0].strip()
    state = field('状态')
    if state not in STATES:
        raise ValueError(requirement + ' 状态无效')
    policy = field('验收方式')
    if policy not in ('自审', '团队'):
        raise ValueError(requirement + ' 验收方式须为自审或团队')
    field('验收依据')
    next_step, blocker = field('下一步'), field('阻塞项')
    rows = []
    for line in text.splitlines():
        if re.match(r'^\|\s*AC-', line):
            cells = [c.strip() for c in line.strip().strip('|').split('|')]
            if len(cells) != 4 or not re.fullmatch(r'AC-\d+', cells[0]) or not cells[1]:
                raise ValueError(requirement + ' 验收行必须为编号、条件、结果、证据四列')
            if cells[2] not in ('通过', '失败', '未验证', '不适用'):
                raise ValueError(requirement + ' 验收结果无效')
            if cells[2] != '未验证' and (not cells[3] or cells[3] in ('待填写', '—', '无')):
                raise ValueError(requirement + ' 已判定验收项必须填写证据或不适用原因')
            rows.append(cells)
    if not rows or len({r[0] for r in rows}) != len(rows):
        raise ValueError(requirement + ' 验收项缺失或编号重复')
    if state == '✅ 执行完成':
        if any(r[2] not in ('通过', '不适用') for r in rows) or not any(r[2] == '通过' for r in rows):
            raise ValueError(requirement + ' 适用验收尚未全部通过')
        if next_step != '无' or blocker != '无':
            raise ValueError(requirement + ' 完成时下一步和阻塞项须为无')
        if policy == '团队' and field('团队确认') in ('待确认', '无', '不适用', '待填写'):
            raise ValueError(requirement + ' 缺少团队实际确认')
    if state == '⛔ 阻塞' and blocker == '无':
        raise ValueError(requirement + ' 阻塞时必须记录原因及解除条件')
    if state in ('⏸️ 已暂停', '🚫 已取消'):
        field('暂停或取消原因')
        if state == '⏸️ 已暂停' and next_step == '无':
            raise ValueError(requirement + ' 暂停时必须记录恢复条件')
    evidence = json.dumps([rows, policy, field('团队确认') if policy == '团队' else ''], ensure_ascii=False)
    return {'state': state, 'passed': sum(r[2] == '通过' for r in rows),
            'applicable': sum(r[2] != '不适用' for r in rows), 'next': next_step, 'blocker': blocker,
            'acceptance_fingerprint': hashlib.sha256(evidence.encode()).hexdigest()}


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True, stderr=subprocess.PIPE).strip()


def resolve(root, ref):
    return git(root, 'rev-parse', '--verify', '--end-of-options', ref + '^{commit}')


def contains(root, ancestor, descendant):
    return subprocess.run(['git', '-C', str(root), 'merge-base', '--is-ancestor', ancestor, descendant],
                          capture_output=True).returncode == 0


def safe_path(root, relative):
    path = root / relative
    for node in (path, *path.parents):
        if node == root:
            break
        if node.is_symlink():
            raise ValueError('交付记录路径不能包含符号链接')
    return path


def load(root, requirement):
    created_time(requirement)
    if not safe_path(root, 'requirements/' + requirement + '.md').is_file():
        raise ValueError('先创建对应需求卡')
    path = safe_path(root, 'requirements/delivery/' + requirement + '.json')
    if path.exists():
        data = json.loads(path.read_text())
        if data.get('requirement') != requirement or data.get('schema_version') != 1:
            raise ValueError('交付记录格式或编号不匹配')
    else:
        data = {'schema_version': 1, 'requirement': requirement, 'linked_commits': [],
                'prs': [], 'development': {'state': '未登记'}, 'events': []}
    return path, data


def commits_for(root, requirement):
    git(root, 'rev-parse', '--git-dir')
    try:
        resolve(root, 'HEAD')
    except subprocess.CalledProcessError:
        return []  # 新仓库尚无首次提交，需求仍需能够同步。
    raw = git(root, 'log', '--format=%H%x00%B%x00', 'HEAD').split('\0')
    result = []
    for i in range(0, len(raw) - 1, 2):
        sha, message = raw[i].strip(), raw[i + 1]
        if re.search(r'^Requirement:\s*' + re.escape(requirement) + r'\s*$', message, re.M):
            paths = git(root, 'diff-tree', '--root', '--no-commit-id', '--name-only', '-r', sha).splitlines()
            # 自动生成交付记录和审查回执的归档提交不算新的需求实施。
            if paths and any(not (p.startswith(('requirements/delivery/', 'logs/reviews/'))
                                  or p == 'requirements/DELIVERY.md') for p in paths):
                result.append(sha)
    return sorted(set(result))


def checks_module():
    spec = importlib.util.spec_from_file_location('delivery_checks', Path(__file__).with_name('project_checks.py'))
    module = importlib.util.module_from_spec(spec)
    previous = sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode = True
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def implementation_snapshot(root, inputs=None, ref=None):
    """同一选择规则用于工作区与不可变 Git 对象；归档后不比较后续需求工作区。"""
    checks = checks_module()
    entries = {}
    if ref:
        raw = subprocess.check_output(['git', '-C', str(root), 'ls-tree', '-rz', ref])
        for entry in filter(None, raw.split(b'\0')):
            metadata, name = entry.split(b'\t', 1)
            mode, kind, oid = metadata.split()
            entries[os.fsdecode(name)] = (mode, kind, oid)
    names = checks.input_paths(root, inputs, entries if ref else None)
    digest = hashlib.sha256()
    for name in sorted(names):
        if inputs is None and name.startswith('requirements/') and Path(name).suffix in ('.md', '.json'):
            continue
        if ref:
            git_mode, kind, oid = entries[name]
            if kind == b'commit':
                content, mode = oid, b'gitlink'
            else:
                content = subprocess.check_output(['git', '-C', str(root), 'cat-file', 'blob', oid])
                mode = b'link' if git_mode == b'120000' else str(int(git_mode, 8) & 0o111).encode()
        else:
            path = root / name
            if path.is_symlink():
                content, mode = os.fsencode(os.readlink(path)), b'link'
            elif path.is_file():
                content, mode = path.read_bytes(), str(path.stat().st_mode & 0o111).encode()
            elif path.is_dir():
                content, mode = git(path, 'rev-parse', 'HEAD').encode(), b'gitlink'
            else:
                continue
        digest.update(os.fsencode(name) + b'\0' + mode + b'\0' + hashlib.sha256(checks.content_for_snapshot(name, content)).digest())
    return digest.hexdigest()


def result_scope(root, results):
    checks = checks_module()
    scopes, evidence = [], []
    whole_tree = False
    for result in results:
        with contextlib.redirect_stdout(io.StringIO()):
            report = checks.verify(root, result)
        config = checks.load_config(root)
        inputs = config.get('profile_inputs', {}).get(report['profile'], config.get('inputs'))
        if inputs is None:
            whole_tree = True
        else:
            scopes.extend(inputs)
        evidence.append({'path': result, 'sha256': hashlib.sha256(checks.local_path(root, result).read_bytes()).hexdigest()})
    return (None if whole_tree else sorted(set(scopes + [checks.CONFIG]))), evidence


def validate_pr(url):
    parsed = urlparse(url)
    if parsed.scheme != 'https' or not parsed.hostname or not re.fullmatch(r'/[^/]+/[^/]+/pull/\d+', parsed.path) or parsed.query or parsed.fragment:
        raise ValueError('PR 必须是完整 HTTPS pull URL')
    return url


def gh_json(root, *args):
    return json.loads(subprocess.check_output(['gh', *args], cwd=root, text=True, stderr=subprocess.PIPE))


def remote_tag_commit(root, tag):
    output = git(root, 'ls-remote', 'origin', 'refs/tags/' + tag, 'refs/tags/' + tag + '^{}')
    refs = dict((line.split()[1], line.split()[0]) for line in output.splitlines())
    return refs.get('refs/tags/' + tag + '^{}', refs.get('refs/tags/' + tag))


def refresh(root, data, github=False, accept=False, inputs=None, results=None):
    commits = sorted(set(commits_for(root, data['requirement']) + data['linked_commits'])
                     - set(data.get('excluded_commits', [])))
    # 引用失效不能静默丢掉，否则可能把部分需求误认为全部发布。
    for sha in commits:
        resolve(root, sha)
    snapshot = {'commits': commits, 'committed': bool(commits), 'merged': '未核实',
                'releases': [], 'release_status': '未核实', 'prs': [], 'warnings': []}
    dev = data.get('development', {})
    snapshot['development'] = dev.get('state', '未登记')
    if dev.get('state') == '✅ 开发完成' and dev.get('commits') != commits:
        snapshot['development'] = '🧪 提交变化，需复核开发验收'
    card = card_state(root, data['requirement'])
    if accept and card is None:
        raise ValueError('--accept 需要结构化需求卡，请先整理本需求')
    if card is not None:
        baseline = data.get('acceptance_baseline')
        if accept and card['state'] != '✅ 执行完成':
            raise ValueError('--accept 仅用于已完成全部实际验收的需求')
        if card['state'] == '✅ 执行完成':
            scope = inputs if inputs is not None else baseline.get('inputs') if baseline else None
            evidence = baseline.get('results', []) if baseline and not accept else []
            if results:
                scope, evidence = result_scope(root, results)
            sealed = baseline and baseline.get('sealed_commits') == commits and bool(commits)
            same_evidence = baseline and baseline.get('acceptance_fingerprint') == card['acceptance_fingerprint']
            if sealed and same_evidence and not accept:
                current = baseline['implementation_fingerprint']
            else:
                current = implementation_snapshot(root, scope)
                latest = None
                if commits:
                    latest = next((sha for sha in git(root, 'rev-list', 'HEAD').splitlines() if sha in commits), None)
                committed_fingerprint = implementation_snapshot(root, scope, latest) if latest else None
                # 延后同步时，后续需求可能已经改变工作区，仍以匹配的实施对象封存。
                if not accept and same_evidence and not baseline.get('reopened') and committed_fingerprint == baseline['implementation_fingerprint']:
                    current = committed_fingerprint
                expected = {'implementation_fingerprint': current,
                            'acceptance_fingerprint': card['acceptance_fingerprint'], 'inputs': scope}
                if accept:
                    if (baseline and baseline.get('implementation_fingerprint') != current
                            and same_evidence):
                        raise ValueError('代码变化后需更新实际 AC 复核证据，不能沿用旧证据接受新代码')
                    if baseline is None or any(baseline.get(k) != v for k, v in expected.items()) or evidence != baseline.get('results', []):
                        data['acceptance_baseline'] = {**expected, 'results': evidence,
                            'accepted_at': datetime.now(timezone.utc).isoformat()}
                elif baseline is None or any(baseline.get(k) != v for k, v in expected.items()):
                    raise ValueError(data['requirement'] + ' 验收基线缺失或内容变化尚未复核；先重开需求并实际复核，再 finish --accept')
                # 只有确切实施提交包含已验收内容时才封存。未提交工作仍需核对工作区。
                if latest:
                    if committed_fingerprint == current:
                        data['acceptance_baseline'] = {**data['acceptance_baseline'],
                            'sealed_commits': commits, 'accepted_commit': latest}
            card['implementation_fingerprint'] = current
        elif baseline and baseline.get('sealed_commits'):
            data['acceptance_baseline'] = {**{k: v for k, v in baseline.items()
                                           if k not in ('sealed_commits', 'accepted_commit')}, 'reopened': True}
        snapshot['development'] = card['state']
        snapshot['card'] = card
    release_targets = set(commits)
    covered = set()
    if github:
        snapshot['github_checked_at'] = datetime.now(timezone.utc).isoformat()
        for url in data['prs']:
            try:
                info = gh_json(root, 'pr', 'view', url, '--json', 'url,state,mergedAt,mergeCommit,commits')
                observed = {'url': url, 'state': info['state'], 'merged_at': info.get('mergedAt')}
                snapshot['prs'].append(observed)
                pr_commits = {c['oid'] for c in info.get('commits', [])}
                merge_sha = (info.get('mergeCommit') or {}).get('oid')
                matched = set(commits) & pr_commits
                if merge_sha in commits:
                    matched.add(merge_sha)
                if info['state'] == 'MERGED' and info.get('mergedAt') and merge_sha and matched:
                    resolve(root, merge_sha)  # 缺本地合并对象需 fetch 后重查。
                    covered.update(matched)
                    release_targets.difference_update(matched)
                    release_targets.add(merge_sha)
            except (subprocess.CalledProcessError, OSError, ValueError, KeyError) as error:
                snapshot['warnings'].append('PR 证据获取失败：' + url + '；请核对 gh 登录、网络与 fetch 状态')
        snapshot['merged'] = '✅ 已合并' if commits and set(commits) <= covered else '未确认全部合并'
        # 本地 tag 只作为候选；没有正式 GitHub Release 不能标为已发布。
        candidate = []
        for tag in git(root, 'tag', '--list').splitlines():
            target = resolve(root, tag)
            if release_targets and all(contains(root, sha, target) for sha in release_targets):
                candidate.append((tag, target))
        failures = False
        for tag, target in candidate:
            try:
                info = gh_json(root, 'release', 'view', tag, '--json', 'url,tagName,isDraft,isPrerelease,publishedAt')
                if not info['isDraft'] and not info['isPrerelease'] and info.get('publishedAt'):
                    if remote_tag_commit(root, tag) != target:
                        failures = True
                        snapshot['warnings'].append('本地与远端标签不一致：' + tag + '；请 fetch 后核对')
                        continue
                    snapshot['releases'].append({'tag': tag, 'commit': target, 'url': info['url'],
                                                 'published_at': info['publishedAt']})
            except (subprocess.CalledProcessError, OSError, ValueError, KeyError):
                failures = True
        snapshot['release_status'] = ('✅ 已发布' if snapshot['releases'] else
                                      '未核实（无有效 Release 证据）' if failures else '未发现已发布版本')
    else:
        previous = data.get('snapshot', {})
        if (card is not None and previous.get('commits') == commits
                and previous.get('github_checked_at')):
            for key in ('merged', 'prs', 'releases', 'release_status', 'github_checked_at', 'warnings'):
                snapshot[key] = previous[key]
        else:
            snapshot['warnings'].append('未查询 GitHub；本地提交或标签不能证明 PR 已合并或 Release 已发布')
    snapshot['checked_at'] = datetime.now(timezone.utc).isoformat()
    data['snapshot'] = snapshot
    return data


def history_snapshots(data):
    previous = {}
    expanded = []
    for event in data['events']:
        if 'snapshot' in event:
            previous = event['snapshot'].copy()
        else:
            previous.update(event.get('changes', {}))
            for key in event.get('removed', []):
                previous.pop(key, None)
        expanded.append({**event, 'snapshot': previous.copy()})
    return expanded


def save(root, path, data, action):
    """保存单张交付记录；调用者完成本次写入后统一生成概览。"""
    safe_path(root, 'requirements/DELIVERY.md')
    if 'card' in data.get('snapshot', {}):
        data.pop('development', None)
    history = history_snapshots(data)
    previous = history[-1]['snapshot'] if history else {}
    current = data.get('snapshot', {})
    data['events'].append({'at': datetime.now(timezone.utc).isoformat(), 'action': action,
                          'changes': {k: v for k, v in current.items() if k not in previous or previous[k] != v},
                          'removed': [k for k in previous if k not in current]})
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    safe_path(root, str(temp.relative_to(root)))
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)


def created_time(requirement):
    if not ID.fullmatch(requirement):
        raise ValueError('需求编号格式应为 REQ-YYYYMMDD-HHMMSSmmmZ-8位随机码，不支持旧编号')
    _, date, clock, _ = requirement.split('-')
    return datetime(int(date[:4]), int(date[4:6]), int(date[6:]),
                    int(clock[:2]), int(clock[2:4]), int(clock[4:6]),
                    int(clock[6:9]) * 1000, tzinfo=timezone.utc)


def requirement_rows(root, reverse=False, warnings=None):
    """直接读取当前卡片，未 finish 的新卡也可查询；不维护第二份状态。"""
    rows = []
    for card in sorted(safe_path(root, 'requirements').glob('REQ-*.md')):
        if not ID.fullmatch(card.stem):
            continue
        try:
            created = created_time(card.stem)
            content = safe_path(root, str(card.relative_to(root))).read_text()
        except (ValueError, OSError) as error:
            warning = '已跳过异常需求卡 ' + str(card.relative_to(root)) + '：' + str(error)
            if warnings is None:
                print(warning, file=sys.stderr)
            else:
                warnings.append(warning)
            continue
        heading = next((line[2:] for line in content.splitlines() if line.startswith('# ')), card.stem)
        title = heading.removeprefix(card.stem + '：')
        state = re.search(r'^- 状态：(.+)$', content, re.M)
        rows.append({'requirement': card.stem, 'created_at': created.isoformat(timespec='milliseconds'),
                     'title': title, 'state': state.group(1).strip() if state else '未登记'})
    rows = [{**row, 'number': i} for i, row in enumerate(rows, 1)]
    return list(reversed(rows)) if reverse else rows


def table_cell(value):
    return str(value).replace('\n', ' ').replace('|', '&#124;')


def list_requirements(root, reverse=False):
    lines = ['| 序号 | 创建时间（UTC） | 需求 | 标题 | 状态 |', '| --- | --- | --- | --- | --- |']
    for row in requirement_rows(root, reverse):
        lines.append('| ' + ' | '.join(table_cell(row[key]) for key in ('number', 'created_at', 'requirement', 'title', 'state')) + ' |')
    return '\n'.join(lines)


def overview(root):
    lines = ['# 需求交付概览', '', '由 delivery.py 按创建时间升序生成；序号仅用于浏览，引用使用固定需求编号。仅收录当前编号格式，旧文件不改写。', '',
             '| 序号 | 创建时间（UTC） | 需求 | 标题 | 开发 | 提交 | PR 合并 | Release | 最近核对 |',
             '| --- | --- | --- | --- | --- | --- | --- | --- | --- |']
    warnings = []
    for row in requirement_rows(root, warnings=warnings):
        req = row['requirement']
        path = safe_path(root, 'requirements/delivery/' + req + '.json')
        data = json.loads(path.read_text()) if path.exists() else {}
        if data and data.get('requirement') != req:
            raise ValueError('交付记录编号不匹配：' + req)
        snap = data.get('snapshot', {})
        values = [row['number'], row['created_at'], '[' + req + '](' + req + '.md)', row['title'], row['state'],
                  '✅ ' + str(len(snap['commits'])) + ' 个提交' if snap.get('commits') else '⬜ 未关联',
                  snap.get('merged', '未核实'), snap.get('release_status', '未核实'), snap.get('checked_at', '—')]
        lines.append('| ' + ' | '.join(table_cell(value) for value in values) + ' |')
    if warnings:
        lines.extend(['', '以下异常需求卡未纳入概览，请修复后重新同步：', ''])
        lines.extend('- ' + table_cell(warning) for warning in warnings)
    return '\n'.join(lines) + '\n'


def finish(root, requirements, github=False, check=False, accept=False, inputs=None, results=None):
    """统一收尾：核对提交与交付记录，刷新当前卡片字段；不批准开发验收。"""
    if accept and (check or len(requirements) != 1):
        raise ValueError('--accept 只用于单项实际验收，不与 --check/--all 组合')
    if results and (not accept or inputs is not None):
        raise ValueError('--result 仅随 --accept 使用，不与 --inputs 重复指定范围')
    if inputs is not None and not accept:
        raise ValueError('--inputs 仅随 --accept 确定验收范围')
    stale = []
    unlinked = []
    # 先校验全部选中项，避免后项格式错误时先写入部分需求。
    prepared = []
    for requirement in requirements:
        path, data = load(root, requirement)
        old = data.get('snapshot', {})
        old_baseline = data.get('acceptance_baseline')
        refresh(root, data, github, accept, inputs, results)
        prepared.append((requirement, path, data, old, old_baseline))
    for requirement, path, data, old, old_baseline in prepared:
        snapshot = data['snapshot']
        if not snapshot['commits']:
            unlinked.append(requirement)
        card = safe_path(root, 'requirements/' + requirement + '.md')
        text = card.read_text()
        state = ('已提交：' + ', '.join(snapshot['commits']) if snapshot['commits'] else '未关联实施提交')
        state += '；Release：' + snapshot['release_status'] + '；详见 delivery/' + requirement + '.json'
        line = '- Git 状态：' + state
        pattern = r'^- Git 状态：.*$'
        updated = re.sub(pattern, lambda _: line, text, count=1, flags=re.M)
        if not re.search(pattern, text, re.M):
            updated = text.rstrip() + '\n\n' + line + '\n'
        if CARD_V2 in text or CARD_V3 in text:
            updated = text  # 新卡无 Git 状态副本；仅生成交付索引，不回写需求卡。
        # checked_at 本身变化不意味着记录过期；其他事实和查询范围变化需要归档。
        strip_time = lambda value: {k: v for k, v in value.items()
                                    if k not in ('checked_at', 'github_checked_at')}
        dirty = (not path.exists() or strip_time(old) != strip_time(snapshot) or updated != text
                 or old_baseline != data.get('acceptance_baseline'))
        if dirty:
            stale.append(requirement)
            if not check:
                previous = re.search(pattern, text, re.M)
                if updated != text:
                    data.setdefault('card_history', []).append({'at': datetime.now(timezone.utc).isoformat(),
                                                               'previous_git_status': previous.group(0) if previous else None})
                save(root, path, data, 'finish')
                if updated != text:
                    temporary = card.with_suffix('.md.tmp')
                    safe_path(root, str(temporary.relative_to(root)))
                    temporary.write_text(updated)
                    temporary.replace(card)
    summary = safe_path(root, 'requirements/DELIVERY.md')
    expected = overview(root)
    overview_outdated = not summary.exists() or summary.read_text() != expected
    if overview_outdated and not check:
        summary.parent.mkdir(parents=True, exist_ok=True)
        summary.write_text(expected)
    if not check:
        # 写后只读核验，不重复扫描源码、Git 历史或查询远端。
        for requirement, path, data, old, old_baseline in prepared:
            stored = json.loads(path.read_text())
            if strip_time(stored.get('snapshot', {})) != strip_time(data['snapshot']):
                raise ValueError(requirement + ' 写后快照不一致')
            if stored.get('acceptance_baseline') != data.get('acceptance_baseline'):
                raise ValueError(requirement + ' 写后验收基线不一致')
            if card_state(root, requirement) != ({k: v for k, v in data['snapshot'].get('card', {}).items()
                                                if k != 'implementation_fingerprint'} or None):
                raise ValueError(requirement + ' 收尾时需求卡变化，请重试')
        if summary.read_text() != expected:
            raise ValueError('交付索引写后不一致')
    status = git(root, 'status', '--porcelain', '--', 'requirements')
    result = {'outdated': stale if check else [], 'updated': stale if not check else [],
              'without_implementation_commit': unlinked, 'unarchived_changes': status.splitlines(),
              'github_checked': github, 'overview_outdated': overview_outdated if check else False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return (not stale and not overview_outdated) if check else True


def create(root, title, template_name="requirement"):
    # 模板名使用白名单，不允许外部路径替换项目内模板。
    if template_name not in ("requirement", "bug-fix"):
        raise ValueError("未知需求模板：" + str(template_name))
    if not title.strip() or '\n' in title or '\r' in title:
        raise ValueError('标题须为单行非空文本')
    directory = safe_path(root, 'requirements')
    directory.mkdir(parents=True, exist_ok=True)
    template = Path(__file__).resolve().parents[1] / ('references/templates/' + template_name + '.md')
    for _ in range(128):
        now = datetime.now(timezone.utc)
        requirement = 'REQ-' + now.strftime('%Y%m%d-%H%M%S') + f'{now.microsecond // 1000:03d}Z-' + uuid.uuid4().hex[:8]
        target = directory / (requirement + '.md')
        content = template.read_text().replace('REQ-YYYYMMDD-HHMMSSmmmZ-RANDOM', requirement).replace('〈需求标题〉', title.strip())
        content = content.replace('YYYY-MM-DDTHH:MM:SS+08:00', now.isoformat(timespec='seconds'))
        try:
            with target.open('x') as stream:
                stream.write(content)
        except FileExistsError:
            continue
        print(json.dumps({'requirement': requirement, 'card': str(target)}, ensure_ascii=False))
        return target
    raise ValueError('需求编号连续冲突，请检查随机源后重试')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('.'))
    parser.add_argument('--requirement')
    sub = parser.add_subparsers(dest='command', required=True)
    listing = sub.add_parser('list', help='按创建时间列出当前需求，序号不用于引用')
    listing.add_argument('--reverse', action='store_true', help='最新需求在前，保留升序序号')
    listing.add_argument('--json', action='store_true', help='输出结构化列表')
    status = sub.add_parser('status')
    status.add_argument('--history', action='store_true', help='按需展开完整历史事件')
    creator = sub.add_parser('create')
    creator.add_argument('--title', required=True)
    creator.add_argument('--template', choices=('requirement', 'bug-fix'), default='requirement',
                         help='普通需求或含复现与处理历史的 Bug Fix 模板')
    finishing = sub.add_parser('finish')
    finishing.add_argument('--all', action='store_true', help='处理所有需求卡')
    finishing.add_argument('--github', action='store_true')
    finishing.add_argument('--check', action='store_true', help='只核对，不更新文件；过期返回非零')
    finishing.add_argument('--accept', action='store_true', help='实际验收完成后显式绑定证据和代码范围')
    finishing.add_argument('--result', action='append', help='引用实际通过的 project_checks 结果；可重复，无需手填范围')
    finishing.add_argument('--inputs', nargs='+', help='验收涉及的项目相对文件/目录，默认沿用基线范围或全工作区')
    dev = sub.add_parser('development')
    dev.add_argument('--state', choices=('未执行', '执行中', '待验证', '开发完成'), required=True)
    dev.add_argument('--evidence', required=True)
    pr = sub.add_parser('link-pr')
    pr.add_argument('--url', required=True)
    commit = sub.add_parser('link-commit')
    commit.add_argument('--commit', required=True)
    exclude = sub.add_parser('exclude-commit')
    exclude.add_argument('--commit', required=True)
    exclude.add_argument('--reason', required=True)
    check = sub.add_parser('refresh')
    check.add_argument('--github', action='store_true')
    args = parser.parse_args()
    try:
        root = args.project.resolve()
        if args.command == 'create':
            if args.requirement:
                raise ValueError('create 自动分配编号，不接收 --requirement')
            create(root, args.title, args.template)
            return 0
        if args.command == 'list':
            if args.requirement:
                raise ValueError('list 不接收 --requirement')
            print(json.dumps(requirement_rows(root, args.reverse), ensure_ascii=False, indent=2)
                  if args.json else list_requirements(root, args.reverse))
            return 0
        if Path(git(root, 'rev-parse', '--show-toplevel')).resolve() != root:
            raise ValueError('请指定 Git 根目录')
        if args.command == 'finish':
            if args.all and args.accept:
                raise ValueError('--accept 不允许批量验收')
            if bool(args.requirement) == args.all:
                raise ValueError('finish 指定 --requirement 或 --all，二选一')
            selected = ([args.requirement] if args.requirement else
                        sorted(p.stem for p in (root / 'requirements').glob('REQ-*.md')
                               if ID.fullmatch(p.stem) and CARD_V3 in p.read_text()))
            return 0 if finish(root, selected, args.github, args.check, args.accept, args.inputs, args.result) else 1
        if not args.requirement:
            raise ValueError('该命令需要 --requirement')
        path, data = load(root, args.requirement)
        if args.command == 'status':
            print(json.dumps({**data, 'events': history_snapshots(data)} if args.history else data.get('snapshot', {}), ensure_ascii=False, indent=2))
            return 0
        if args.command == 'development':
            if card_state(root, args.requirement) is not None:
                raise ValueError('新版需求仅在需求卡维护状态与验收，然后 finish；无需 development 重复登记')
            if not args.evidence.strip():
                raise ValueError('验收/状态证据不能为空')
            state = {'未执行': '⬜ 未执行', '执行中': '🔄 执行中', '待验证': '🧪 待验证', '开发完成': '✅ 开发完成'}[args.state]
            data['development'] = {'state': state, 'evidence': args.evidence,
                                   'commits': sorted(set(commits_for(root, args.requirement) + data['linked_commits']))}
        elif args.command == 'link-pr':
            url = validate_pr(args.url)
            if url not in data['prs']:
                data['prs'].append(url)
        elif args.command == 'link-commit':
            sha = resolve(root, args.commit)
            if sha in data.get('excluded_commits', []):
                data['excluded_commits'].remove(sha)
            if sha not in data['linked_commits']:
                data['linked_commits'].append(sha)
        elif args.command == 'exclude-commit':
            if not args.reason.strip():
                raise ValueError('排除错归提交必须记录原因')
            sha = resolve(root, args.commit)
            if sha not in data.setdefault('excluded_commits', []):
                data['excluded_commits'].append(sha)
                data.setdefault('association_corrections', []).append({
                    'commit': sha, 'reason': args.reason, 'at': datetime.now(timezone.utc).isoformat()})
        refresh(root, data, getattr(args, 'github', False))
        save(root, path, data, args.command)
        safe_path(root, 'requirements/DELIVERY.md').write_text(overview(root))
        print(json.dumps(data['snapshot'], ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(2, '交付追踪失败：' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
