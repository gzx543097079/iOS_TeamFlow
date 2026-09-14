# 2.0.1 验证摘要

时间：2026-09-14T09:06:03+08:00

- `python3.12 scripts/run_workflow_checks.py --full`：Ran 109 tests in 34.843s，全部通过，退出码 0。包含时间编号、碰撞重试、列表排序/倒序/JSON/只读、旧编号拒绝、跨分支建卡、验收门禁、CI 选择、真实 ZIP 接入消费与升级。
- 原始日志 /tmp/teamflow-2.0.1-full.log，SHA256：09f4455822e4eff10928467ee8e354272084e6f5699dfd7541e8ba7a88536af3。
- `python3.12 scripts/package_release.py`：完整分发包、独立 Skill 包及各自 SHA256 生成成功；VERSION、teamflow.json、README 下载链接和 CHANGELOG 对齐 2.0.1。`git diff --check` 通过。
- 本次为工作流工具改动，无 iOS App；ios-demo profile 不适用。边界与实现核对见 validation-requirement-order.md；旧编号不兼容、原件不迁移，序号只供浏览。正式发布与远端附件结果由交付索引另行核实。
