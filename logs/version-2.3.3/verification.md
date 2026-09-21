# 2.3.3 源码版本验证

- `python3 scripts/run_workflow_checks.py --full`：通过，114 项测试全部成功。
- `python3 scripts/package_release.py`：连续执行两次成功，两次 SHA-256 完全一致。
- 完整包：`0ecceab4afe94a8f9952be892dbf5d7697997401086ea422a5e46e3517b33228`（`iOS-TeamFlow-v2.3.3.zip`）。
- 独立 Skill 包：`553ea59d27d9c1b0e4253eb093ff2010a5cabc137d2704d274268b13fe0f544e`（`ios-team-flow-skill-v2.3.3.zip`）。
- VERSION、`.agents/teamflow.json`、CHANGELOG 与 README 均指向源码版本 2.3.3；正式附件仍为 2.3.0 Release，本次不创建标签或 Release。
- TeamFlowDemo 增量模块验证见 `logs/demo-module-context/verification.md`。Demo 工程检查因 Xcode 27 不支持既有 iOS 14 / Pods iOS 6 部署目标而在测试前失败，`source_unchanged=true`；本次未修改工程部署配置。
