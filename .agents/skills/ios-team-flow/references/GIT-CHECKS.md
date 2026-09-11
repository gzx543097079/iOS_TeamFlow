# 可选 Hook 与明确范围的 PR 检查

本地 Hook 提供提交前提醒与拦截；CI 检查已提交的证据。二者不自动生成语义审查，也不是不可伪造的证明。审查仍由 Codex/团队完成，必要的项目构建与测试独立执行。

## 可选本地 Hook

从 Git 根目录显式执行，setup_project.py 不自动安装 Hook：

```sh
python3 .agents/skills/ios-team-flow/scripts/install_git_checks.py hook-install
python3 .agents/skills/ios-team-flow/scripts/install_git_checks.py hook-uninstall
```

每个克隆目录单独安装。工具遵守本仓库现有 core.hooksPath，不更改用户全局设置；路径在项目之外时停止，避免修改多个仓库共用 Hook。已有可执行 pre-commit 备份为同目录 teamflow-pre-commit.previous，先执行旧 Hook，再执行项目内 review_gate.py check，任一失败阻止提交。重复安装不重复串联；卸载恢复原 Hook。Hook 被团队修改后停止覆盖，由团队合并。

已有 Hook 如果会自动格式化并修改暂存内容，新的指纹可能要求重新 review，这是必要的内容复核。`git commit --no-verify` 能跳过本地 Hook，所以团队若要求合并前必须检查，应另配置 PR 必需检查；本工具不修改分支保护规则。

## 明确范围审查

CI 不调用只针对暂存区的 check。以下入口从 Git 对象读取已提交内容，即使暂存区为空也会检查：

```sh
python3 .agents/skills/ios-team-flow/scripts/range_review.py check --base 目标分支SHA --head 本次提交SHA
```

必须显式提供两个可解析的提交。差异从 base 与 head 的 merge-base 到 head，包含二进制、删除、模式变更；报告指纹绑定确切目标分支 base 及差异。head 树内的回执目录只允许普通 JSON/Markdown/patch。

线性提交优先复用每个实施提交对应的暂存审查报告，报告必须已提交并能在 head 读取。缺报告、待验证或新增未审代码会失败。已审代码不因 CI 再运行而重新生成审查意见。

合并提交、squash/rebase 改变审查基准或缺少原回执时，可生成范围报告：

```sh
python3 .agents/skills/ios-team-flow/scripts/range_review.py prepare --base 目标分支SHA --head HEAD
```

Codex 读取生成的 patch，按 REVIEW.md 填写报告；已有审查结论只对基准/差异变化及合并影响复核，并注明复用依据。提交报告后，以新的 head 再执行 check。只增加回执的提交不改变业务差异，可复用该范围报告；新增业务代码或目标 base 改变会重新校验。合并冲突解决后的最终内容必须有对应证据，不能只引用合并前报告。

## 可选 GitHub PR 检查

```sh
python3 .agents/skills/ios-team-flow/scripts/install_git_checks.py ci-install
```

生成 `.github/workflows/teamflow-pr-review.yml`，已有同名不同内容不覆盖。提交安装文件及完整 Skill 到目标分支后生效；仓库管理员按需要将 `review-evidence` 设为必需检查，并保护检查器/工作流路径的修改权限。首次安装需先合入目标分支，缺少可信检查器时 CI 明确失败，不能改用 PR 自带的检查器来绕过。

模板用 pull_request 事件提供的 base/head SHA、完整 Git 历史，从目标分支提取 range_review.py 和 review_gate.py，在隔离 Python 模式执行。它不运行 PR 分支的检查器、配置脚本或业务代码，不传入写权限或发布凭据。报告 JSON 仍由 PR 提供，只做内容范围与结构校验，不是对审查真实性的加密证明；受控分支与团队审批补足这一边界。

本地 Hook、PR 检查、业务测试是不同状态。范围门禁通过不代表 App 构建成功；没有 gh/GitHub 或未安装 CI 时，仍可本地执行明确范围检查并记录限制。
