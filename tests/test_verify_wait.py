"""失败后只重跑失败项、开始前提示预计耗时的回归（依据颜见会话固定 sleep 等待与整套重跑的实测）。"""
import json
import sys
import unittest
import test_teamflow

flow = test_teamflow.flow
COUNT = "import sys; open(sys.argv[1], 'a').write('x')"
# b.txt 内容为 good 才通过，模拟修复失败项。
CHECK_B = "import sys; open(sys.argv[1], 'a').write('x'); sys.exit(open('b.txt').read() != 'good')"


class VerifyWaitTests(unittest.TestCase):
    setUp = test_teamflow.TeamFlowTests.setUp
    git = test_teamflow.TeamFlowTests.git
    configure_checks = test_teamflow.TeamFlowTests.configure_checks
    baseline = test_teamflow.TeamFlowTests.baseline
    create = test_teamflow.TeamFlowTests.create
    fill = test_teamflow.TeamFlowTests.fill
    card_path = test_teamflow.TeamFlowTests.card_path

    def setup_profile(self, **check_a):
        (self.root / 'a.txt').write_text('a')
        (self.root / 'b.txt').write_text('bad')
        checks = {'a': {'argv': [sys.executable, '-c', COUNT, 'a.count'], 'inputs': ['a.txt'], **check_a},
                  'b': {'argv': [sys.executable, '-c', CHECK_B, 'b.count'], 'inputs': ['b.txt']}}
        (self.root / '.agents/project-checks.json').write_text(json.dumps({'schema_version': 2, 'profiles': {
            'p': {'inputs': ['a.txt', 'b.txt'], 'checks': checks}}}))
        self.baseline()
        return flow.checks_module()

    def count(self, name):
        path = self.root / name
        return len(path.read_text()) if path.exists() else 0

    def run_p(self, module, **kwargs):
        target, ok = module.run(self.root, 'p', **kwargs)
        return ok, json.loads(target.read_text()), target

    def test_retry_after_failure_runs_only_failed_checks(self):
        m = self.setup_profile()
        ok, _, target = self.run_p(m)
        self.assertFalse(ok)
        self.assertIn('只重跑失败项', m.describe_run(self.root, target))
        (self.root / 'b.txt').write_text('good')
        ok, report, _ = self.run_p(m)
        self.assertTrue(ok)
        results = {r['name']: r for r in report['results']}
        self.assertTrue(results['a'].get('reused'))
        self.assertNotIn('reused', results['b'])
        self.assertEqual((1, 2), (self.count('a.count'), self.count('b.count')))
        # 最新一次已通过：不再复用，按原语义全部执行。
        ok, report, _ = self.run_p(m)
        self.assertTrue(ok)
        self.assertEqual((2, 3), (self.count('a.count'), self.count('b.count')))

    def test_retry_does_not_reuse_changed_forced_or_uncached_checks(self):
        m = self.setup_profile()
        self.assertFalse(self.run_p(m)[0])
        (self.root / 'a.txt').write_text('a2')
        self.assertFalse(self.run_p(m)[0])
        self.assertEqual(2, self.count('a.count'))
        self.assertFalse(self.run_p(m, rerun=True)[0])
        self.assertEqual(3, self.count('a.count'))

    def test_cache_false_check_always_reruns_after_failure(self):
        m = self.setup_profile(cache=False)
        self.assertFalse(self.run_p(m)[0])
        (self.root / 'b.txt').write_text('good')
        self.assertTrue(self.run_p(m)[0])
        self.assertEqual(2, self.count('a.count'))

    def test_announces_plan_estimate_and_result_path_before_running(self):
        m = self.setup_profile()
        messages = []
        _, report, target = self.run_p(m, announce=messages.append)
        self.assertEqual(1, len(messages))
        self.assertIn('执行 a、b', messages[0])
        self.assertIn('无历史', messages[0])
        self.assertIsNone(report['estimated_seconds'])
        self.assertIn(str(target.relative_to(self.root)), messages[0])
        self.assertIn('不用固定时长 sleep', messages[0])
        (self.root / 'b.txt').write_text('good')
        messages.clear()
        _, report, _ = self.run_p(m, announce=messages.append)
        self.assertIn('复用上次通过 a', messages[0])
        self.assertIn('预计约', messages[0])
        self.assertIsInstance(report['estimated_seconds'], (int, float))

    def test_complete_forwards_announcement(self):
        m = self.setup_profile()
        (self.root / 'b.txt').write_text('good')
        req = self.create(); self.fill(req)
        messages = []
        flow.complete(self.root, req, profile='p', announce=messages.append)
        self.assertTrue(messages and messages[0].startswith('开始验证（p）'))


if __name__ == '__main__':
    unittest.main()
