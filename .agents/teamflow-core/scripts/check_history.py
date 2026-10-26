"""本地检查历史、缓存候选与耗时估算；不执行检查。"""
import json
from teamflow_common import local_path


def recent_reports(root):
    directory = local_path(root, 'logs/project-checks')
    if not directory.is_dir():
        return []
    reports = []
    for run_dir in directory.iterdir():
        if not run_dir.is_dir():
            continue
        try:
            report = json.loads((run_dir / 'result.json').read_text())
            if isinstance(report, dict):
                reports.append((run_dir, report))
        except (OSError, ValueError):
            continue
    return sorted(reports, key=lambda entry: entry[1].get('started_at', entry[0].name), reverse=True)[:40]


def reusable_results(root, profile):
    """每项只看最近出现的结果；失败、未完成、输入变化都阻断更早的成功缓存。"""
    available, seen = {}, set()
    for run_dir, report in recent_reports(root):
        if report.get('profile') != profile:
            continue
        results = {item['name']: item for item in report.get('results', []) if 'name' in item}
        for name in report.get('selected', list(results)):
            if name in seen:
                continue
            seen.add(name)
            item = results.get(name, {})
            if (report.get('completed_at') and report.get('status') in ('通过', '失败')
                    and report.get('end_fingerprint') == report.get('source', {}).get('fingerprint')
                    and item.get('status') == '通过' and item.get('check_fingerprint')):
                available[name] = (run_dir.name, item)
    return available


def retry_results(root, profile):
    """未启用 incremental 时的失败重跑：仅当该 profile 最近一次完成的运行失败，
    复用其中通过且输入未中途变化的检查；最新一次已通过或输入变化时不复用。"""
    for run_dir, report in recent_reports(root):
        if report.get('profile') != profile or not report.get('completed_at'):
            continue
        if (report.get('status') != '失败'
                or report.get('end_fingerprint') != (report.get('source') or {}).get('fingerprint')):
            return {}
        return {item['name']: (run_dir.name, item) for item in report.get('results', [])
                if item.get('status') == '通过' and item.get('check_fingerprint')}
    return {}


def recent_duration(root, profile, name):
    """该检查最近一次实际执行（非复用）的耗时，优先取通过的运行，没有时取失败的运行。"""
    fallback = None
    for _, report in recent_reports(root):
        if report.get('profile') != profile:
            continue
        for item in report.get('results', []):
            if (item.get('name') != name or item.get('reused')
                    or not isinstance(item.get('duration_seconds'), (int, float))):
                continue
            if item.get('status') == '通过':
                return item['duration_seconds']
            if item.get('status') == '失败' and fallback is None:
                fallback = item['duration_seconds']
    return fallback


def estimate_seconds(durations, parallelism):
    if not durations:
        return 0
    total = sum(durations)
    return round(total if parallelism <= 1 else max(max(durations), total / parallelism))


def last_pass(root, profile):
    """最近通过的实际耗时，并明确是否含缓存及部分选择。"""
    for run_dir, report in recent_reports(root):
        if report.get('profile') == profile and report.get('status') == '通过':
            wall = report.get('wall_seconds')
            if wall is None:
                wall = round(sum(item.get('duration_seconds') or 0 for item in report.get('results', [])), 1)
            reused = any(item.get('reused') for item in report.get('results', []))
            partial = bool(report.get('skipped'))
            return {'wall_seconds': wall, 'completed_at': report.get('completed_at'),
                    'reused': reused, 'partial': partial,
                    'kind': 'cached' if reused else 'partial' if partial else 'full'}
    return None

