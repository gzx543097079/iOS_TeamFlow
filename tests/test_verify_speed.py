"""验证提速的回归：检查并行执行、incremental 按检查级指纹复用与 suggest 耗时提示。"""
import json
import sys
import time
import unittest
import test_teamflow

flow = test_teamflow.flow

MARK = "import sys; open(sys.argv[1], 'a').write('x')"


class VerifySpeedTests(unittest.TestCase):
    setUp = test_teamflow.TeamFlowTests.setUp
    git = test_teamflow.TeamFlowTests.git
    configure_checks = test_teamflow.TeamFlowTests.configure_checks
    baseline = test_teamflow.TeamFlowTests.baseline

    def set_profiles(self, profiles):
        (self.root / '.agents/project-checks.json').write_text(
            json.dumps({'schema_version': 2, 'profiles': profiles}))

    def counts(self, name):
        path = self.root / name
        return len(path.read_text()) if path.exists() else 0

    # 1. 多项检查并行执行：两个 2 秒检查的总耗时应接近 2 秒而非 4 秒
    def test_checks_run_in_parallel(self):
        self.baseline()
        self.set_profiles({'p': {'inputs': ['source.txt'], 'parallelism': 2, 'checks': {
            'slow-a': {'argv': [sys.executable, '-c', 'import time; time.sleep(2)']},
            'slow-b': {'argv': [sys.executable, '-c', 'import time; time.sleep(2)']}}}})
        module = flow.checks_module()
        target, ok = module.run(self.root, 'p')
        self.assertTrue(ok)
        report = json.loads(target.read_text())
        self.assertLess(report['wall_seconds'], 3.5)
        self.assertEqual(['slow-a', 'slow-b'], [r['name'] for r in report['results']])

    def test_timeout_is_per_check_and_kills_only_the_hanging_one(self):
        self.baseline()
        self.set_profiles({'p': {'inputs': ['source.txt'], 'checks': {
            'hanging': {'argv': [sys.executable, '-c', 'import time; time.sleep(30)'],
                        'timeout_seconds': 1},
            'quick': {'argv': [sys.executable, '-c', 'pass']}}}})
        start = time.monotonic()
        target, ok = flow.checks_module().run(self.root, 'p')
        self.assertLess(time.monotonic() - start, 5)
        self.assertFalse(ok)
        results = {r['name']: r for r in json.loads(target.read_text())['results']}
        self.assertEqual('超时', results['hanging']['status'])
        self.assertEqual('通过', results['quick']['status'])

    # 2. incremental：检查级指纹一致时复用最近一次通过结果
    def test_incremental_reuses_unchanged_checks_only(self):
        self.baseline()
        (self.root / 'a.txt').write_text('a')
        (self.root / 'b.txt').write_text('b')
        self.git('add', '-A')
        self.git('commit', '-qm', 'inputs')
        self.set_profiles({'inc': {'inputs': ['a.txt', 'b.txt'], 'priority': 1, 'incremental': True,
                                   'checks': {
                                       'ca': {'argv': [sys.executable, '-c', MARK, 'ca.count'],
                                              'inputs': ['a.txt']},
                                       'cb': {'argv': [sys.executable, '-c', MARK, 'cb.count'],
                                              'inputs': ['b.txt']}}}})
        module = flow.checks_module()
        target, ok = module.run(self.root, 'inc')
        self.assertTrue(ok)
        self.assertEqual((1, 1), (self.counts('ca.count'), self.counts('cb.count')))
        # 无任何改动：两项全部复用，不再执行
        target, ok = module.run(self.root, 'inc')
        self.assertTrue(ok)
        report = json.loads(target.read_text())
        results = {r['name']: r for r in report['results']}
        self.assertTrue(results['ca'].get('reused') and results['cb'].get('reused'))
        self.assertEqual((1, 1), (self.counts('ca.count'), self.counts('cb.count')))
        self.assertTrue((target.parent / results['ca']['log']).is_file())
        self.assertTrue(results['ca']['reused_from'])
        self.assertLess(report['wall_seconds'], 2)
        # 只改 b 的输入：仅 cb 重跑，ca 仍复用
        (self.root / 'b.txt').write_text('b2')
        target, ok = module.run(self.root, 'inc')
        self.assertTrue(ok)
        results = {r['name']: r for r in json.loads(target.read_text())['results']}
        self.assertTrue(results['ca'].get('reused'))
        self.assertNotIn('reused', results['cb'])
        self.assertEqual((1, 2), (self.counts('ca.count'), self.counts('cb.count')))
        # 改命令同样使复用失效
        config = json.loads((self.root / '.agents/project-checks.json').read_text())
        config['profiles']['inc']['checks']['ca']['argv'] = [sys.executable, '-c', MARK, 'ca2.count']
        (self.root / '.agents/project-checks.json').write_text(json.dumps(config))
        target, ok = module.run(self.root, 'inc')
        self.assertTrue(ok)
        self.assertEqual(1, self.counts('ca2.count'))

    def test_incremental_does_not_reuse_failures_but_reuses_passing_siblings(self):
        self.baseline()
        (self.root / 'a.txt').write_text('a')
        (self.root / 'b.txt').write_text('b')
        self.git('add', '-A')
        self.git('commit', '-qm', 'inputs')
        broken = 'import sys; sys.exit(1)'
        profiles = {'inc': {'inputs': ['a.txt', 'b.txt'], 'incremental': True, 'checks': {
            'ca': {'argv': [sys.executable, '-c', broken], 'inputs': ['a.txt']},
            'cb': {'argv': [sys.executable, '-c', MARK, 'cb.count'], 'inputs': ['b.txt']}}}}
        self.set_profiles(profiles)
        module = flow.checks_module()
        target, ok = module.run(self.root, 'inc')
        self.assertFalse(ok)
        # 修复 ca：ca 必须重跑；cb 虽来自整体失败的运行，其通过结果仍可复用
        profiles['inc']['checks']['ca']['argv'] = [sys.executable, '-c', MARK, 'ca.count']
        (self.root / '.agents/project-checks.json').write_text(json.dumps({'schema_version': 2,
                                                                           'profiles': profiles}))
        target, ok = module.run(self.root, 'inc')
        self.assertTrue(ok)
        results = {r['name']: r for r in json.loads(target.read_text())['results']}
        self.assertNotIn('reused', results['ca'])
        self.assertTrue(results['cb'].get('reused'))
        self.assertEqual((1, 1), (self.counts('ca.count'), self.counts('cb.count')))

    def test_without_incremental_every_check_runs_every_time(self):
        self.baseline()
        self.set_profiles({'p': {'inputs': ['source.txt'], 'checks': {
            'ca': {'argv': [sys.executable, '-c', MARK, 'ca.count']},
            'cb': {'argv': [sys.executable, '-c', MARK, 'cb.count']}}}})
        module = flow.checks_module()
        for _ in range(2):
            target, ok = module.run(self.root, 'p')
            self.assertTrue(ok)
        self.assertEqual((2, 2), (self.counts('ca.count'), self.counts('cb.count')))

    # 3. 未启用 incremental 的 profile 证据指纹保持不变
    def test_effective_config_unchanged_for_legacy_profiles(self):
        self.baseline()
        config = flow.checks_module().load_config(self.root)
        legacy = flow.checks_module().effective_config(config, 'change')
        self.assertEqual({'inputs', 'checks'}, set(legacy))
        self.assertEqual({'name', 'argv', 'cwd', 'timeout_seconds'}, set(legacy['checks'][0]))
        self.set_profiles({'inc': {'inputs': ['source.txt'], 'incremental': True, 'checks': {
            'c': {'argv': ['true'], 'inputs': ['source.txt']}}}})
        config = flow.checks_module().load_config(self.root)
        enabled = flow.checks_module().effective_config(config, 'inc')
        self.assertIs(True, enabled.get('incremental'))
        self.assertEqual(['source.txt'], enabled['checks'][0].get('inputs'))

    def test_config_rejects_invalid_incremental_and_check_inputs(self):
        self.baseline()
        self.set_profiles({'bad': {'inputs': ['source.txt'], 'incremental': 'yes',
                                   'checks': {'c': {'argv': ['true']}}}})
        with self.assertRaisesRegex(ValueError, 'incremental'):
            flow.checks_module().load_config(self.root)
        self.set_profiles({'bad': {'inputs': ['source.txt'], 'checks': {
            'c': {'argv': ['true'], 'inputs': []}}}})
        with self.assertRaisesRegex(ValueError, 'inputs'):
            flow.checks_module().load_config(self.root)

    # 4. verify suggest 显示最近一次通过耗时
    def test_suggest_reports_last_pass_duration(self):
        self.baseline()
        (self.root / 'a.txt').write_text('a')
        self.git('add', '-A')
        self.git('commit', '-qm', 'inputs')
        self.set_profiles({'inc': {'inputs': ['a.txt'], 'checks': {
            'c': {'argv': ['true']}}}})
        module = flow.checks_module()
        target, ok = module.run(self.root, 'inc')
        self.assertTrue(ok)
        report = module.suggest(self.root)
        entry = next(p for p in report['profiles'] if p['profile'] == 'inc')
        self.assertGreaterEqual(entry['last_pass']['wall_seconds'], 0)
        self.assertIn('秒', flow.render('suggest', report))


if __name__ == '__main__':
    unittest.main()
