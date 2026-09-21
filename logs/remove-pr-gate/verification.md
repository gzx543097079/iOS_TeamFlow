# 移除 PR 门禁模块验证记录

- 验证范围：删除 PR 审查 workflow、PR 模板、range review 工具、PR 安装资产、PR 触发和分支保护/必需检查说明；保留可选本地提交 Hook。
- 专项测试：`python3 -m unittest -v test_git_checks test_check_selection test_workflow.WorkflowTests.test_repository_documents test_consumer_release test_setup_recovery`，20 项通过。
- 完整回归：`python3 scripts/run_workflow_checks.py --full`，加入发布顺序回归后 107 项通过。
- 分发包：运行 `python3 scripts/package_release.py`，检查两种 2.3.1 分发包，均不包含 `pull_request_template`、`teamflow-pr-review`、`range_review` 或 `pr-review`。
- 命令入口：`install_git_checks.py --help` 只保留 `hook-install`、`hook-uninstall`。
- 接入诊断：`setup_project.py --doctor` 不再报告 PR 检查或分支保护项；其 Python 3.9.6 低于文档建议 3.10 的提示为既有环境问题，与本次变更无关。
- 引用检查：在工作流源文件、测试、README 与 GitHub 配置中检索 `branch protection`、`分支保护`、`必需检查`、`required check`、`range_review`、`ci-install`、`teamflow-pr-review`、`pull_request_template`、`pull_request:`，无残留结果。
- 兼容边界：delivery 的 `link-pr` 和 PR/合并事实字段继续作为历史交付事实记录，不承担审查门禁或远端强制职责。
