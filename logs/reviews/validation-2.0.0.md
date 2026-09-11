# 2.0.0 验证摘要

时间：2026-09-11T20:51:26+08:00

- `python3.12 scripts/run_workflow_checks.py --full`：106 项通过，33.772 秒，退出码 0；包含文档校验、选择器、升级、门禁与真实 ZIP 消费测试。
- 原始日志 /tmp/teamflow-2.0.0-full.log，SHA256：9c32d42288bf3a22a43aca22f436617d53df10fae2ccdb62010a354006ea3915。
- 双包及 SHA256 生成通过；对照 1.10.2 ZIP，文件清单完全相同，只有 references/VERSION、CHANGELOG 及完整包 README 内容变化，全部功能文件一致。
- README、VERSION、teamflow.json 为 2.0.0，CHANGELOG 明确重新发布现有功能；git diff --check 通过。
- 本次仅版本维护，不适用 ios-demo profile；按 RELEASE 完整验证工作流，不声明 App 验收。旧版本保留，线上发布由交付索引另行核实。
