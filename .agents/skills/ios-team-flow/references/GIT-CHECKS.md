# 可选本地提交 Hook

本地 Hook 提供提交前提醒与拦截。它不自动生成语义审查，也不是不可绕过的证明；审查仍由 Codex/团队完成，必要的项目构建与测试独立执行。

## 可选本地 Hook

从 Git 根目录显式执行，setup_project.py 不自动安装 Hook：

```sh
python3 .agents/skills/ios-team-flow/scripts/install_git_checks.py hook-install
python3 .agents/skills/ios-team-flow/scripts/install_git_checks.py hook-uninstall
```

每个克隆目录单独安装。工具遵守本仓库现有 core.hooksPath，不更改用户全局设置；路径在项目之外时停止，避免修改多个仓库共用 Hook。已有可执行 pre-commit 备份为同目录 teamflow-pre-commit.previous，先执行旧 Hook，再执行项目内 review_gate.py check，任一失败阻止提交。重复安装不重复串联；卸载恢复原 Hook。Hook 被团队修改后停止覆盖，由团队合并。

已有 Hook 如果会自动格式化并修改暂存内容，新的指纹可能要求重新 review，这是必要的内容复核。`git commit --no-verify` 能跳过本地 Hook，因此它只作为本机辅助，不宣称为远端强制门禁。业务测试与提交审查仍是不同状态；Hook 通过不代表 App 构建或验收通过。
