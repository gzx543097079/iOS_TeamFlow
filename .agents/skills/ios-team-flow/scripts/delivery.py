#!/usr/bin/env python3
"""以需求标记、Git 提交和可选 GitHub 只读证据生成交付概览。"""
import argparse
import hashlib
import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ID = re.compile(r'REQ-\d{8}-\d{3,}')
CARD_V2 = '<!-- teamflow:requirement:v2 -->'
STATES = ('❔ 待确认', '⬜ 未执行', '🔄 执行中', '🧪 待验证', '✅ 执行完成',
          '⛔ 阻塞', '⏸️ 已暂停', '🚫 已取消')


def card_state(root, requirement):
    """新版需求卡是唯一人工状态源；校验结构与一致性，不代替语义验收。"""
    text = safe_path(root, 'requirements/' + requirement + '.md').read_text()
    if CARD_V2 not in text:
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
    if not ID.fullmatch(requirement):
        raise ValueError('需求编号格式应为 REQ-YYYYMMDD-NNN')
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


def implementation_snapshot(root):
    """工作区内容绑定，区分正常提交已验收内容与提交后的额外修改。"""
    raw = subprocess.check_output(['git', '-C', str(root), 'ls-files', '--cached', '--others',
                                   '--exclude-standard', '-z'], stderr=subprocess.PIPE)
    digest = hashlib.sha256()
    for name in sorted(set(os.fsdecode(p) for p in raw.split(b'\0') if p)):
        if (name.startswith(('logs/reviews/', 'logs/project-checks/', '.agents/teamflow-backups/'))
                or name.startswith('requirements/') and Path(name).suffix in ('.md', '.json')):
            continue
        path = root / name
        if path.is_symlink():
            content, mode = os.fsencode(os.readlink(path)), b'link'
        elif path.is_file():
            content, mode = path.read_bytes(), str(path.stat().st_mode & 0o111).encode()
        elif path.is_dir():
            # 已有 submodule 用其实际 HEAD；不遍历外部目录。
            content, mode = git(path, 'rev-parse', 'HEAD').encode(), b'gitlink'
        else:
            continue  # 已删除文件与暂存删除后的树一致。
        digest.update(os.fsencode(name) + b'\0' + mode + b'\0' + hashlib.sha256(content).digest())
    return digest.hexdigest()


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


def refresh(root, data, github=False):
    commits = sorted(set(commits_for(root, data['requirement']) + data['linked_commits']))
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
    if card is not None:
        previous = data.get('snapshot', {})
        old_card = previous.get('card', {})
        if card['state'] == '✅ 执行完成':
            card['implementation_fingerprint'] = implementation_snapshot(root)
        if (card['state'] == '✅ 执行完成' and old_card.get('state') == '✅ 执行完成'
                and previous.get('commits') != commits
                and old_card.get('acceptance_fingerprint') == card['acceptance_fingerprint']
                and old_card.get('implementation_fingerprint') != card['implementation_fingerprint']):
            raise ValueError(data['requirement'] + ' 新实施提交尚未复核；重开需求或更新实际验收证据')
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


def save(root, path, data, action):
    safe_path(root, 'requirements/DELIVERY.md')
    if 'card' in data.get('snapshot', {}):
        data.pop('development', None)
    data['events'].append({'at': datetime.now(timezone.utc).isoformat(), 'action': action, 'snapshot': data.get('snapshot', {})})
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    safe_path(root, str(temp.relative_to(root)))
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
    temp.replace(path)
    safe_path(root, 'requirements/DELIVERY.md').write_text(overview(root))


def overview(root):
    lines = ['# 需求交付概览', '', '由 delivery.py 生成；新版需求状态来自需求卡，旧记录保留。提交、合并与发布独立核对。', '',
             '| 需求 | 开发 | 提交 | PR 合并 | Release | 最近核对 |', '| --- | --- | --- | --- | --- | --- |']
    for item in sorted(safe_path(root, 'requirements/delivery').glob('REQ-*.json')):
        if item.is_symlink():
            continue
        row = json.loads(item.read_text())
        snap = row.get('snapshot', {})
        req = row['requirement']
        lines.append('| [' + req + '](' + req + '.md) | ' + snap.get('development', row.get('development', {}).get('state', '未登记'))
                     + ' | ' + ('✅ ' + str(len(snap['commits'])) + ' 个提交' if snap.get('commits') else '⬜ 未关联')
                     + ' | ' + snap.get('merged', '未核实') + ' | ' + snap.get('release_status', '未核实')
                     + ' | ' + snap.get('checked_at', '—') + ' |')
    return '\n'.join(lines) + '\n'


def finish(root, requirements, github=False, check=False):
    """统一收尾：核对提交与交付记录，刷新当前卡片字段；不批准开发验收。"""
    stale = []
    unlinked = []
    # 先校验全部选中项，避免后项格式错误时先写入部分需求。
    prepared = []
    for requirement in requirements:
        path, data = load(root, requirement)
        old = data.get('snapshot', {})
        refresh(root, data, github)
        prepared.append((requirement, path, data, old))
    for requirement, path, data, old in prepared:
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
        if CARD_V2 in text:
            updated = text  # 新卡无 Git 状态副本；仅生成交付索引，不回写需求卡。
        # checked_at 本身变化不意味着记录过期；其他事实和查询范围变化需要归档。
        strip_time = lambda value: {k: v for k, v in value.items()
                                    if k not in ('checked_at', 'github_checked_at')}
        dirty = not path.exists() or strip_time(old) != strip_time(snapshot) or updated != text
        if dirty:
            stale.append(requirement)
            if not check:
                previous = re.search(pattern, text, re.M)
                if updated != text:
                    data.setdefault('card_history', []).append({'at': datetime.now(timezone.utc).isoformat(),
                                                               'previous_git_status': previous.group(0) if previous else None})
                save(root, path, data, 'finish')
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
    status = git(root, 'status', '--porcelain', '--', 'requirements')
    result = {'outdated': stale if check else [], 'updated': stale if not check else [],
              'without_implementation_commit': unlinked, 'unarchived_changes': status.splitlines(),
              'github_checked': github, 'overview_outdated': overview_outdated if check else False}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return (not stale and not overview_outdated) if check else True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('.'))
    parser.add_argument('--requirement')
    sub = parser.add_subparsers(dest='command', required=True)
    finishing = sub.add_parser('finish')
    finishing.add_argument('--all', action='store_true', help='处理所有需求卡')
    finishing.add_argument('--github', action='store_true')
    finishing.add_argument('--check', action='store_true', help='只核对，不更新文件；过期返回非零')
    dev = sub.add_parser('development')
    dev.add_argument('--state', choices=('未执行', '执行中', '待验证', '开发完成'), required=True)
    dev.add_argument('--evidence', required=True)
    pr = sub.add_parser('link-pr')
    pr.add_argument('--url', required=True)
    commit = sub.add_parser('link-commit')
    commit.add_argument('--commit', required=True)
    check = sub.add_parser('refresh')
    check.add_argument('--github', action='store_true')
    args = parser.parse_args()
    try:
        root = args.project.resolve()
        if Path(git(root, 'rev-parse', '--show-toplevel')).resolve() != root:
            raise ValueError('请指定 Git 根目录')
        if args.command == 'finish':
            if bool(args.requirement) == args.all:
                raise ValueError('finish 指定 --requirement 或 --all，二选一')
            selected = ([args.requirement] if args.requirement else
                        sorted(p.stem for p in (root / 'requirements').glob('REQ-*.md')
                               if ID.fullmatch(p.stem) and CARD_V2 in p.read_text()))
            return 0 if finish(root, selected, args.github, args.check) else 1
        if not args.requirement:
            raise ValueError('该命令需要 --requirement')
        path, data = load(root, args.requirement)
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
            if sha not in data['linked_commits']:
                data['linked_commits'].append(sha)
        refresh(root, data, getattr(args, 'github', False))
        save(root, path, data, args.command)
        print(json.dumps(data['snapshot'], ensure_ascii=False, indent=2))
    except (ValueError, OSError, KeyError, TypeError, subprocess.CalledProcessError) as error:
        parser.exit(2, '交付追踪失败：' + str(error) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
