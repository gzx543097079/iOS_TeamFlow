# 2.4.0 流程精简验证

- 时间：2026-09-22T10:22:00+08:00
- 发布候选复核：2026-09-22T10:44:08+08:00
- `python3 scripts/check_logging.py`：Swift、Objective-C/Objective-C++ 的 Debug/Release 运行及 iOS SDK 编译通过。
- `python3 -B scripts/run_workflow_checks.py --full`：退出码 0；122 项完整回归通过，覆盖分发 ZIP、消费项目、交付工具、风险路由、续审、Hook、模块索引及代表性订阅场景。
- `python3 scripts/package_release.py`：生成 `iOS-TeamFlow-v2.4.0.zip` 与 `ios-team-flow-skill-v2.4.0.zip`；SHA-256 分别为 `75fe6a1ce06a3987d60c0aea72bd10646a766ff5d06f9110353057172c4baccf`、`e34c0c7cfe9ecfc21c72fc507560237bfbc4aa14a3b6b0ff62cd21c0d8116b73`。
- `python3 -B scripts/validate_workflow.py`：通过，版本、分发清单、Skill 元数据和内部链接一致。
- `git diff --check`：通过。
- 当前树 `logs/reviews/*.patch`：0；历史 97 个 patch 已从当前树移除，JSON 回执保留，Git 历史可恢复旧 patch。
- 当前树 `requirements/DELIVERY.md`：不存在；`delivery.py list --delivery` 由当前卡片、Requirement trailer 和外部事实记录只读生成。
- 风险路由回归证明：文档只要求核心三维；Swift 源码增加 memory/test_artifacts；订阅信号增加 subscription；`--full` 扩到七维；check 拒绝手工删除自动路由维度。
- 轻量卡回归证明：`create --template lightweight` 可创建和筛选，且不生成 delivery 记录；完整卡验收绑定仍使用 finish --accept。
