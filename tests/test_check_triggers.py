"""按 check 触发、覆盖证据以及执行/缓存边界的真实进程回归。"""
import json
import sys
import unittest

import test_teamflow

flow = test_teamflow.flow
R = 'REQ-20260101-0001'


class CheckTriggerTests(unittest.TestCase):
    setUp = test_teamflow.TeamFlowTests.setUp
    git = test_teamflow.TeamFlowTests.git
    configure_checks = test_teamflow.TeamFlowTests.configure_checks
    baseline = test_teamflow.TeamFlowTests.baseline

    def setup_checks(self, **options):
        (self.root / 'a.py').write_text('a = 1\n')
        (self.root / 'b.py').write_text('b = 1\n')
        (self.root / 'shared.py').write_text('shared = 1\n')
        settings = {'inputs': ['a.py', 'b.py', 'shared.py'], 'covers': ['a.py', 'b.py'], 'checks': {
            'a': {'argv': [sys.executable, '-c', "print('a')"], 'covers': ['a.py'], 'inputs': ['a.py', 'shared.py']},
            'b': {'argv': [sys.executable, '-c', "print('b')"], 'covers': ['b.py'], 'inputs': ['b.py', 'shared.py']}}}
        settings.update(options)
        self.write_config({'p': settings})
        self.baseline()
        return flow.checks_module()

    def write_config(self, profiles):
        (self.root / '.agents/project-checks.json').write_text(json.dumps({'schema_version': 2, 'profiles': profiles}))

    def plan(self, module, **kwargs):
        return module.execution_plan(self.root, module.load_config(self.root), 'p', **kwargs)

    def test_one_check_skips_other_and_summary_cannot_claim_other(self):
        m = self.setup_checks()
        (self.root / 'requirements').mkdir()
        (self.root / 'requirements' / (R + '.md')).write_text(
            f'---\nid: {R}\nstate: 进行中\n---\n\n# Test\n\n## 范围\n\nImplement a\n\n## 验收条件\n\n- [ ] AC-01：a works\n')
        (self.root / 'a.py').write_text('a = 2\n')
        self.assertEqual(['a'], self.plan(m)['selected'])
        result, passed = m.run(self.root, 'p', R)
        self.assertTrue(passed)
        report = json.loads(result.read_text())
        self.assertEqual(['a'], report['checks'])
        self.assertEqual(['b'], report['skipped'])
        summary = m.summarize(self.root, result)
        self.assertEqual(['a.py'], m.evidence_inputs(self.root, summary))
        m.verify_summary(self.root, R, summary)
        for checks in (['a', 'b'], ['b'], []):
            with self.assertRaises(ValueError):
                m.verify_summary(self.root, R, {**summary, 'checks': checks})
        (self.root / 'b.py').write_text('b = 2\n')
        with self.assertRaisesRegex(ValueError, '缺少当前触发检查'):
            m.verify_summary(self.root, R, summary)

    def test_no_changes_or_only_canonical_requirement_produces_no_evidence(self):
        m = self.setup_checks()
        (self.root / 'requirements').mkdir()
        (self.root / 'requirements' / (R + '.md')).write_text('# metadata\n')
        result, passed = m.run(self.root, 'p')
        self.assertFalse(passed)
        report = json.loads(result.read_text())
        self.assertEqual('无需检查', report['status'])
        self.assertEqual([], report['checks'])
        self.assertIn('未触发', m.describe_run(self.root, result))
        with self.assertRaises(ValueError):
            m.verify(self.root, str(result.relative_to(self.root)))
        with self.assertRaises(ValueError):
            m.summarize(self.root, result)

    def test_shared_inputs_trigger_both_and_scope_cap_is_enforced(self):
        m = self.setup_checks()
        self.assertEqual(['a', 'b'], self.plan(m, names={'shared.py'})['selected'])
        plan = self.plan(m, names={'shared.py'})
        self.assertEqual(['shared.py'], plan['uncovered_engineering_files'])
        self.assertEqual(['a.py', 'b.py'], m.evidence_inputs(self.root, {'profile': 'p', 'checks': ['a', 'b']}))
        self.assertEqual([], m.intersect_inputs(['src'], ['tests']))
        self.assertEqual(['src/a.py'], m.intersect_inputs(['src'], ['src/a.py']))

    def test_omitted_check_inputs_inherit_profile_dependencies(self):
        m = self.setup_checks(checks={
            'a': {'argv': ['true'], 'covers': ['a.py']},
            'b': {'argv': ['true'], 'covers': ['b.py']}})
        self.assertEqual(['a', 'b'], self.plan(m, names={'shared.py'})['selected'])
        config = m.load_config(self.root)
        before = m.check_snapshot(self.root, config, 'p', 'a')
        config['profiles']['p']['checks']['a']['covers'] = ['b.py']
        self.assertNotEqual(before, m.check_snapshot(self.root, config, 'p', 'a'))

    def test_uncovered_engineering_rejected_before_command(self):
        m = self.setup_checks()
        (self.root / 'unknown.py').write_text('bad = 1\n')
        with self.assertRaisesRegex(ValueError, '未被检查覆盖'):
            m.run(self.root, 'p', rerun=True)
        self.assertFalse((self.root / 'logs/project-checks').exists())

    def test_manual_only_explicit_and_explicit_runs_all(self):
        m = self.setup_checks()
        data = m.load_config(self.root)
        data['profiles']['release'] = {**data['profiles']['p'], 'manual': True, 'priority': 0}
        self.write_config(data['profiles'])
        self.git('add', '-A'); self.git('commit', '-qm', 'manual')
        (self.root / 'a.py').write_text('a = 2\n')
        self.assertEqual('p', m.select_profile(self.root))
        result, passed = m.run(self.root, 'release')
        self.assertTrue(passed)
        self.assertEqual(['a', 'b'], json.loads(result.read_text())['checks'])

    def test_force_and_prior_selected_merge_new_triggers(self):
        m = self.setup_checks(incremental=True)
        result, passed = m.run(self.root, 'p', rerun=True)
        self.assertTrue(passed)
        self.assertEqual(['a', 'b'], json.loads(result.read_text())['checks'])
        (self.root / 'b.py').write_text('b = 2\n')
        result, passed = m.run(self.root, 'p', selected=['a'])
        self.assertTrue(passed)
        report = json.loads(result.read_text())
        self.assertEqual(['a', 'b'], report['checks'])
        self.assertFalse(any(r.get('reused') for r in report['results']))
        result, passed = m.run(self.root, 'p', rerun=True)
        self.assertTrue(passed)
        self.assertFalse(any(r.get('reused') for r in json.loads(result.read_text())['results']))

    def test_requirement_commit_paths_remain_selected(self):
        m = self.setup_checks()
        (self.root / 'a.py').write_text('a = 2\n')
        self.git('add', '-A'); self.git('commit', '-qm', 'stage\n\nRequirement: ' + R)
        self.assertEqual(['a'], self.plan(m, requirement=R)['selected'])
        self.assertEqual([], self.plan(m)['selected'])

    def test_added_deleted_and_renamed_paths(self):
        m = self.setup_checks()
        self.assertEqual(['a', 'b'], self.plan(m, names={'a.py', 'b.py'})['selected'])
        (self.root / 'a.py').unlink()
        result, passed = m.run(self.root, 'p')
        self.assertTrue(passed)
        self.assertEqual(['a'], json.loads(result.read_text())['checks'])

    def test_external_check_dependencies_are_bound_and_historical_snapshot_works(self):
        m = self.setup_checks(inputs=['a.py', 'b.py'])
        (self.root / 'a.py').write_text('a = 2\n')
        result, passed = m.run(self.root, 'p')
        self.assertTrue(passed)
        report = json.loads(result.read_text())
        self.assertIn('shared.py', report['source']['files'])
        self.git('add', '-A'); self.git('commit', '-qm', 'validated')
        commit = self.git('rev-parse', 'HEAD')
        snapshot = m.source_snapshot(self.root, m.load_config(self.root), 'p', commit=commit, checks=['a'])
        self.assertEqual(report['source'], snapshot)
        (self.root / 'shared.py').write_text('shared = 2\n')
        with self.assertRaises(ValueError):
            m.verify(self.root, str(result.relative_to(self.root)))
        self.assertEqual(snapshot, m.source_snapshot(self.root, m.load_config(self.root), 'p', commit=commit, checks=['a']))

    def test_default_sequential_preserves_artifact_dependency(self):
        m = self.setup_checks(checks={
            'build': {'argv': [sys.executable, '-c', "import time; from pathlib import Path; time.sleep(.3); Path('build.out').write_text('done')"]},
            'inspect': {'argv': [sys.executable, '-c', "from pathlib import Path; assert Path('build.out').read_text() == 'done'"]}})
        result, passed = m.run(self.root, 'p')
        self.assertTrue(passed)
        self.assertEqual(['build', 'inspect'], json.loads(result.read_text())['checks'])

    def test_later_short_timeout_does_not_wait_for_first_check(self):
        m = self.setup_checks(parallelism=2, checks={
            'long': {'argv': [sys.executable, '-c', 'import time; time.sleep(2.3)']},
            'short': {'argv': [sys.executable, '-c', "import time; from pathlib import Path; time.sleep(1.6); Path('escaped').touch()"], 'timeout_seconds': 1}})
        result, passed = m.run(self.root, 'p')
        self.assertFalse(passed)
        self.assertFalse((self.root / 'escaped').exists())
        report = json.loads(result.read_text())
        self.assertEqual('超时', report['results'][1]['status'])
        self.assertLess(report['results'][1]['duration_seconds'], 1.6)

    def test_cache_chmod_timeout_and_latest_failure_barrier(self):
        argv = [sys.executable, '-c', "from pathlib import Path; p=Path('calls'); p.write_text(p.read_text()+'x' if p.exists() else 'x'); assert not Path('fail').exists()"]
        m = self.setup_checks(incremental=True, checks={'a': {'argv': argv, 'inputs': ['a.py']}})
        def run(**kwargs):
            target, ok = m.run(self.root, 'p', **kwargs)
            return ok, json.loads(target.read_text())
        self.assertTrue(run()[0])
        ok, report = run()
        self.assertTrue(report['results'][0]['reused'])
        self.assertTrue(m.last_pass(self.root, 'p')['reused'])
        (self.root / 'a.py').chmod(0o755)
        ok, report = run()
        self.assertTrue(ok)
        self.assertNotIn('reused', report['results'][0])
        data = m.load_config(self.root)
        data['profiles']['p']['checks']['a']['timeout_seconds'] = 901
        self.write_config(data['profiles'])
        ok, report = run()
        self.assertTrue(ok)
        self.assertNotIn('reused', report['results'][0])
        (self.root / 'fail').touch()
        self.assertFalse(run(rerun=True)[0])
        (self.root / 'fail').unlink()
        ok, report = run()
        self.assertTrue(ok)
        self.assertNotIn('reused', report['results'][0])
        self.assertEqual('xxxxx', (self.root / 'calls').read_text())

    def test_cache_false_runs_artifact_producer_every_time(self):
        m = self.setup_checks(incremental=True, checks={'a': {'cache': False, 'inputs': ['a.py'],
            'argv': [sys.executable, '-c', "from pathlib import Path; Path('artifact').touch()"]}})
        self.assertTrue(m.run(self.root, 'p')[1])
        (self.root / 'artifact').unlink()
        self.assertTrue(m.run(self.root, 'p')[1])
        self.assertTrue((self.root / 'artifact').exists())

    def test_timeout_blocks_old_pass_and_input_mutation_blocks_reuse(self):
        argv = [sys.executable, '-c', "import time; from pathlib import Path; time.sleep(2) if Path('hang').exists() else None"]
        m = self.setup_checks(incremental=True, checks={'a': {'argv': argv, 'inputs': ['a.py'], 'timeout_seconds': 1}})
        self.assertTrue(m.run(self.root, 'p')[1])
        (self.root / 'hang').touch()
        target, passed = m.run(self.root, 'p', rerun=True)
        self.assertFalse(passed)
        self.assertEqual('超时', json.loads(target.read_text())['results'][0]['status'])
        (self.root / 'hang').unlink()
        target, passed = m.run(self.root, 'p')
        self.assertTrue(passed)
        self.assertNotIn('reused', json.loads(target.read_text())['results'][0])
        data = m.load_config(self.root)
        data['profiles']['p']['checks']['a']['argv'] = [sys.executable, '-c',
            "from pathlib import Path; p=Path('a.py'); p.write_text(p.read_text()+'# changed\\n')"]
        self.write_config(data['profiles'])
        target, passed = m.run(self.root, 'p')
        self.assertFalse(passed)
        self.assertEqual('输入已变化，需重测', json.loads(target.read_text())['status'])
        self.assertNotIn('a', m.reusable_results(self.root, 'p'))

    def test_partial_last_pass_and_legacy_evidence_range(self):
        m = self.setup_checks()
        (self.root / 'a.py').write_text('a = 2\n')
        self.assertTrue(m.run(self.root, 'p')[1])
        timing = m.last_pass(self.root, 'p')
        self.assertTrue(timing['partial'])
        self.assertFalse(timing['reused'])
        self.assertEqual('partial', timing['kind'])
        self.assertEqual(['a.py', 'b.py'], m.evidence_inputs(self.root, {'profile': 'p'}))

    def test_literal_bracket_filename_is_supported(self):
        m = self.setup_checks()
        self.assertEqual({'[Model].py'}, m.input_paths(self.root, ['[Model].py'], {'[Model].py', 'M.py'}))

    def test_invalid_glob_parallelism_manual_cache_and_missing_dependency(self):
        m = self.setup_checks()
        data = m.load_config(self.root)
        for key, value in [('parallelism', 0), ('parallelism', True), ('manual', 'yes')]:
            with self.subTest(key=key, value=value):
                self.write_config({'p': {**data['profiles']['p'], key: value}})
                with self.assertRaises(ValueError):
                    m.load_config(self.root)
        for check in ({'covers': ['*.py']}, {'covers': ['shared.py']},
                      {'covers': ['a.py'], 'inputs': ['b.py']},
                      {'cache': 'yes'}, {'inputs': ['missing.py']}):
            self.write_config({'p': {**data['profiles']['p'], 'checks': {'a': {'argv': ['true'], **check}}}})
            with self.assertRaises(ValueError):
                m.run(self.root, 'p', rerun=True)


if __name__ == '__main__':
    unittest.main()
