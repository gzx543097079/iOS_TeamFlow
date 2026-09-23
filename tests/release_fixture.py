"""同一次测试运行共用分发产物，各测试仍独立解压和验证。"""
import contextlib
import io
import sys
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import package_release


@cache
def skill_archive():
    with contextlib.redirect_stdout(io.StringIO()):
        return package_release.package_skill(ROOT)
