"""同一次测试运行共用分发产物，写入临时目录而非仓库 dist/；各测试仍独立解压和验证。"""
import atexit
import contextlib
import io
import shutil
import sys
import tempfile
from functools import cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import package_release

OUTPUT = Path(tempfile.mkdtemp(prefix='teamflow-dist-'))
atexit.register(shutil.rmtree, OUTPUT, ignore_errors=True)


@cache
def archive(mode):
    with contextlib.redirect_stdout(io.StringIO()):
        return package_release.package_mode(ROOT, mode, OUTPUT)


def skill_archive():
    return archive('ios')
