#!/usr/bin/env python3
"""从项目内 Skill 加载审查门禁，唯一实现维护在 Skill 内。"""
import runpy
from pathlib import Path

_source = Path(__file__).resolve().parents[1] / '.agents/skills/ios-team-flow/scripts/review_gate.py'
globals().update(runpy.run_path(str(_source), run_name=__name__))
