"""iOS 导出脚本：前置条件一次报全，引擎错误与缺失产物判失败，按模板真实架构构建。"""
import importlib.util
import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / '.agents/skills/Godot/scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('export_ios', SCRIPTS / 'export_ios.py')
export_ios = importlib.util.module_from_spec(spec)
spec.loader.exec_module(export_ios)

PROJECT = '''config_version=5
[application]
config/name="Drop Game"
config/icon="res://icon.svg"
[rendering]
textures/vram_compression/import_etc2_astc=true
'''
PRESETS = '''[preset.0]
name="Web"
platform="Web"
[preset.0.options]
[preset.1]
name="iOS"
platform="iOS"
[preset.1.options]
application/app_store_team_id="TEAMIDTEST"
application/bundle_identifier="com.example.drop"
application/export_project_only=true
custom_template/debug="/templates/ios.zip"
'''


def fake_tool(path, body):
    path.write_text('#!' + sys.executable + '\n' + textwrap.dedent(body))
    path.chmod(0o755)
    return str(path)


class ExportIOSTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.game = self.base / 'game'
        self.game.mkdir()
        (self.game / 'project.godot').write_text(PROJECT)
        (self.game / 'export_presets.cfg').write_text(PRESETS)

    def test_preflight_reports_every_missing_prerequisite(self):
        self.assertEqual([], export_ios.preflight(self.game, 'iOS', '4.7.2.stable.official.abc'))
        (self.game / 'project.godot').write_text('config_version=5\n')
        presets = PRESETS.replace('TEAMIDTEST', '').replace('export_project_only=true', 'export_project_only=false')
        (self.game / 'export_presets.cfg').write_text(presets)
        problems = '\n'.join(export_ios.preflight(self.game, 'iOS', '4.7.2.stable.official.abc'))
        for expected in ('app_store_team_id', 'export_project_only', '图标', 'import_etc2_astc'):
            self.assertIn(expected, problems)
        self.assertIn('没有名为 "Android"', export_ios.preflight(self.game, 'Android', '4.7.2.stable')[0])

    def test_export_builds_with_template_arch_and_rejects_engine_errors(self):
        godot = fake_tool(self.base / 'godot', '''
            import sys
            from pathlib import Path
            if sys.argv[1] == '--version':
                print('4.7.2.stable.official.abc'); sys.exit(0)
            ipa = Path(sys.argv[-1])
            (ipa.parent / (ipa.stem + '.xcodeproj')).mkdir()
            library = ipa.parent / (ipa.stem + '.xcframework/ios-arm64_x86_64-simulator')
            library.mkdir(parents=True)
            (library / 'libgodot.a').write_text('')
        ''')
        xcodebuild = fake_tool(self.base / 'xcodebuild', '''
            import sys
            from pathlib import Path
            derived = Path(sys.argv[sys.argv.index('-derivedDataPath') + 1])
            (derived / 'Build/Products/Debug-iphonesimulator/DropGame.app').mkdir(parents=True)
            print(' '.join(sys.argv))
        ''')
        with patch.object(export_ios, 'simulator_archs', return_value=['x86_64']), \
                patch.object(export_ios.platform, 'machine', return_value='arm64'):
            result = export_ios.export(self.game, output=self.base / 'out', godot=godot, xcodebuild=xcodebuild)
        self.assertTrue(result['app'].endswith('DropGame.app'))
        self.assertEqual('x86_64', result['arch'])
        self.assertIn('缺少本机 arm64', result['notes'][0])
        broken = fake_tool(self.base / 'broken', '''
            import sys
            print('4.7.2.stable' if sys.argv[1] == '--version' else 'ERROR: Cannot export project')
        ''')
        with self.assertRaisesRegex(ValueError, '失败'):
            export_ios.export(self.game, output=self.base / 'out', godot=broken, xcodebuild=xcodebuild)


if __name__ == '__main__':
    unittest.main()
