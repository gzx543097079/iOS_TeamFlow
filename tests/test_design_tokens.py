import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / '.agents/skills/iOS/scripts/check_design_tokens.py'


class DesignTokenTests(unittest.TestCase):
    """模块外的字体、圆角、颜色、间距字面量失败；模块内、语义引用、0 与注释放行；基线只放行存量。"""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / 'App/Theme').mkdir(parents=True)
        (self.root / 'App/Features').mkdir(parents=True)
        (self.root / 'App/Theme/Theme.swift').write_text(
            'enum Theme { static let card: CGFloat = 12\n static let title = Font.system(size: 17)\n'
            ' static let accent = Color(red: 1, green: 0, blue: 0) }\n')
        self.configure()

    def configure(self, **extra):
        config = {'sources': ['App'], 'modules': ['App/Theme'], 'baseline': '.agents/design-tokens-baseline.json'}
        config.update(extra)
        (self.root / '.agents').mkdir(exist_ok=True)
        (self.root / '.agents/design-tokens.json').write_text(json.dumps(config))

    def page(self, text, name='Home.swift'):
        (self.root / 'App/Features' / name).write_text(text)

    def run_check(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), '--root', str(self.root), *args],
                              capture_output=True, text=True)

    def test_literals_outside_module_fail(self):
        self.page('view.cornerRadius(12)\nText("a").font(.system(size: 17))\n'
                  'let f = UIFont.systemFont(ofSize: 15)\nlet c = Color(red: 0.1, green: 0.2, blue: 0.3)\n'
                  'v.padding(16)\nlayer.cornerRadius = 8\n')
        (self.root / 'App/Features/Legacy.m').write_text('[UIFont systemFontOfSize:14];\n')
        result = self.run_check()
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        for expected in ('App/Features/Home.swift:1: [corner-radius]', 'Home.swift:2: [font]', 'Home.swift:3: [font]',
                         'Home.swift:4: [color]', 'Home.swift:5: [spacing]', 'Home.swift:6: [corner-radius]',
                         'Legacy.m:1: [font]'):
            self.assertIn(expected, result.stdout)
        self.assertIn('新增违规 7', result.stdout)

    def test_module_tokens_zero_and_comments_pass(self):
        self.page('view.cornerRadius(Theme.card)\nText("a").font(Theme.title)\nv.padding(0)\n'
                  'RoundedRectangle(cornerRadius: 0)\n// view.cornerRadius(12)\nlet x = 1 // .padding(8)\n')
        result = self.run_check()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn('通过', result.stdout)

    def test_baseline_allows_existing_only(self):
        self.page('view.cornerRadius(12)\n')
        self.assertEqual(0, self.run_check('--update-baseline').returncode)
        baseline = json.loads((self.root / '.agents/design-tokens-baseline.json').read_text())
        self.assertEqual(['corner-radius'], [e['rule'] for e in baseline['entries']])
        result = self.run_check()
        self.assertEqual(0, result.returncode, result.stdout)
        self.assertIn('基线放行 1', result.stdout)
        self.page('view.cornerRadius(12)\nview.cornerRadius(12)\n')  # 同一写法新增一处仍失败
        result = self.run_check()
        self.assertEqual(1, result.returncode)
        self.assertIn('Home.swift:2: [corner-radius]', result.stdout)
        self.page('view.cornerRadius(Theme.card)\n')
        result = self.run_check()
        self.assertEqual(0, result.returncode)
        self.assertIn('基线中 1 条已不存在', result.stdout)

    def test_rule_subset_and_custom_rule(self):
        self.configure(rules=['font'], custom_rules={'shadow': r'shadowRadius\s*[:=]\s*\d'})
        self.page('view.cornerRadius(12)\nlayer.shadowRadius = 4\n')
        result = self.run_check()
        self.assertEqual(1, result.returncode)
        self.assertIn('[shadow]', result.stdout)
        self.assertNotIn('[corner-radius]', result.stdout)
        self.configure(rules=['unknown'])
        self.assertEqual(2, self.run_check().returncode)

    def test_missing_config_or_no_sources_is_an_error(self):
        (self.root / '.agents/design-tokens.json').unlink()
        result = self.run_check()
        self.assertEqual(2, result.returncode)
        self.assertIn('缺少配置', result.stderr)
        self.configure(sources=['App/Theme'])
        result = self.run_check()
        self.assertEqual(2, result.returncode)
        self.assertIn('未扫描到任何源文件', result.stderr)


if __name__ == '__main__':
    unittest.main()
