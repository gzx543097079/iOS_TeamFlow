# 2.3.1 验证记录

- 版本一致性：`.agents/skills/ios-team-flow/references/VERSION`、`.agents/teamflow.json`、CHANGELOG 与 README 均标记源码版本 2.3.1；README 保留 2.3.0 正式附件入口并明确本次不发布 Release。
- 原生检查：`python3 scripts/check_logging.py` 通过 Swift Debug/Release 与 Objective-C/Objective-C++ Debug/Release 的运行及 iOS SDK 编译检查。
- 完整回归：`python3 scripts/run_workflow_checks.py --full`，107 项通过；新增回归确认 workflow 仅由 `teamflow-v*` 标签触发，验证、artifact 和发布任务依赖顺序正确。
- 发布边界：原生检查和打包任务只有 `contents: read`；最终 `publish` 任务依赖 `package`、不检出仓库或执行仓库脚本，独占 `contents: write` 并使用 `--verify-tag`。
- 分发包：连续两次运行 `python3 scripts/package_release.py`，完整包 SHA256 均为 `fdce4e0de354c0ce6bcd35bf243a2e96f7389a4fda209830ceaae76f381dfcea`，独立 Skill 包均为 `9e40cc4ab1ccde2d67cebebb7552d1edfe2639fc50a84b75ad01fde3f2ab7bc3`。
- 包内容：完整包包含新的 `.github/workflows/teamflow-release.yml`，不包含已删除的 PR workflow、PR 模板或范围审查工具。
- 外部依据：GitHub Actions 官方语法支持按 push tag 过滤；GitHub CLI 官方说明 `gh release create` 附带资源时先创建草稿、上传资源，最后才发布，并支持 `--verify-tag` 验证远端标签存在。
- 远端边界：本轮只提交并推送源码，不创建或推送 `teamflow-v2.3.1` 标签，因此不会触发 Release workflow；推送事实在提交成功后归档。
