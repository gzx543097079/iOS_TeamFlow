#!/usr/bin/env python3
"""从项目内 Skill 加载 TeamFlow 唯一实现。"""
import runpy
import sys
from pathlib import Path

# 工具运行不向业务仓库写入字节码缓存，也不改变子进程的 Python 配置。
sys.dont_write_bytecode = True
_source = Path(__file__).resolve().parents[1] / '.agents/teamflow-core/scripts/teamflow.py'
sys.path.insert(0, str(_source.parent))
globals().update(runpy.run_path(str(_source), run_name=__name__))
