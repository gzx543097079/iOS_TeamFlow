#!/usr/bin/env python3
"""从安装包 ZIP 一键接入当前项目，无需人工整包解压到项目根。

用法（在业务项目 Git 根）：
  python3 install_teamflow.py ~/Downloads/teamflow-ios-v1.6.4.zip --mode ios
  unzip -p ~/Downloads/teamflow-ios-v1.6.4.zip install_teamflow.py | python3 - ~/Downloads/teamflow-ios-v1.6.4.zip --mode ios

已安装项目请用：python3 scripts/teamflow.py upgrade <包>
"""
from __future__ import annotations

import argparse
import sys
import tempfile
import zipfile
from pathlib import Path


def _extract_scripts(package: Path, destination: Path) -> Path:
    with zipfile.ZipFile(package) as stream:
        names = [name for name in stream.namelist()
                 if name.startswith('.agents/teamflow-core/scripts/') and name.endswith('.py')]
        if not names:
            raise SystemExit('安装包缺少 .agents/teamflow-core/scripts/')
        for name in names:
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(stream.read(name))
    return destination / '.agents/teamflow-core/scripts'


def main(argv=None):
    parser = argparse.ArgumentParser(description='一键将 TeamFlow 安装包接入当前项目')
    parser.add_argument('package', type=Path, help='teamflow-*-vX.Y.Z.zip')
    parser.add_argument('--mode', choices=['ios', 'godot', 'godot-ios'], default='ios')
    parser.add_argument('--project', type=Path, default=Path('.'))
    parser.add_argument('--plan', action='store_true', help='只读预览')
    parser.add_argument('--force', action='store_true', help='覆盖已安装的核心与 Skill 文件')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    package = args.package.expanduser().resolve()
    if not package.is_file():
        raise SystemExit('安装包不存在：' + str(package))
    root = args.project.expanduser().resolve()
    with tempfile.TemporaryDirectory(prefix='teamflow-install-') as tmp:
        scripts = _extract_scripts(package, Path(tmp))
        sys.path.insert(0, str(scripts))
        import upgrade
        result = upgrade.install(root, package, mode=args.mode, dry_run=args.plan, force=args.force)
        if args.json:
            import json
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(upgrade.describe(result, args.plan))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
