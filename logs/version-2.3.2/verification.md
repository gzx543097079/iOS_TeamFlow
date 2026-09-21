# 2.3.2 验证记录

- 工具专项：`python3 -m unittest -v test_module_context`，6 项通过；覆盖模块记录与完整 HEAD 基准、查询路由、未命中、提交/暂存/未暂存/未跟踪变化、横切变化、路径删除失效、不安全/脏路径拒绝及显式刷新。
- 消费链路专项：从实际独立 Skill ZIP 执行模块记录和查询，确认输出不包含源码正文；模块工具、测试选择、文档和打包专项通过。
- 完整回归：`python3 scripts/run_workflow_checks.py --full`，114 项通过。
- 原生检查：`python3 scripts/check_logging.py` 通过 Swift Debug/Release 与 Objective-C/Objective-C++ Debug/Release 的运行及 iOS SDK 编译检查。
- 版本一致性：VERSION、`.agents/teamflow.json`、CHANGELOG 与 README 均为源码版本 2.3.2；README 保留 2.3.0 正式附件入口并明确本轮不发布 Release。
- 可重复打包：连续两次生成的完整包 SHA256 均为 `6e913aa597f30835c60b4bc3b6d630b9b50e11e6601b33ef890f8ca0a285e00e`；独立 Skill 包均为 `a0ab66e728367c461050f8311ea6b99b0eedeb102e9ff33228d83b41a37e4e58`。
- 包内容：完整包包含 `module_context.py`、`MODULE-CONTEXT.md` 和 `test_module_context.py`；独立 Skill 包包含工具与说明，不包含项目自身 `.agents/project-modules.json` 数据。
- 安全边界：工具只执行固定 Git 子命令参数列表，不使用 shell；路径拒绝绝对路径、`..`、反斜杠和 Git 魔法 pathspec；索引符号链接、未跟踪关注路径和相关脏工作区被拒绝。查询只返回元数据与文件名，不读取源码正文。
- 远端边界：本轮只提交并推送源码，不创建或推送 `teamflow-v2.3.2` 标签，因此不会触发 Release workflow；提交和推送事实在成功后归档。
