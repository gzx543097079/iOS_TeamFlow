# 命令参考

证据机制见 [CHECKS](CHECKS.md)，主流程见 [WORKFLOW](WORKFLOW.md)。

## 验证与完成

`req complete REQ-20260101-a3f9 --profile change` 优先复用同 profile 的有效证据，否则运行并绑定摘要；`--rerun` 与 `--profile` 一起显式重跑。`--result logs/project-checks/运行编号/result.json` 绑定已用 `verify run --requirement` 生成的结果，不重跑。`verify run` 本身始终运行，不是证据复核命令。不传证据参数时先复核摘要；缺失或失效时按 covers 与 priority 选择覆盖全部改动的唯一候选，存在歧义或无覆盖则报错且不改卡片。输出区分“复用验证，未运行测试”和重新验证原因。`--profile`、`--result`、`--evidence` 互斥。

`--confirm-ac AC-01` 可重复；`--user-confirmed AC-01` 同样勾选，并把编号记入头部 `user_confirmed`，`req status` 与 `req pr` 标注“用户确认”。未知编号、证据无效或验证失败均不更改卡片，未指定的条件保留原状态。`--wait-user` 与恢复规则见 [WORKFLOW](WORKFLOW.md#实施与验收)，恢复命令见下方「状态」。

## 可选宿主审批

`permissions --mode strict|default [--plan]` 显式启用严格模板或移除未改动的旧模板；自定义内容不覆盖，默认安装不激活。迁移边界见 [安装说明](INSTALL.md#宿主权限)。

## 输出

所有命令默认输出几行简短摘要：验证只报“通过/失败”，失败时附失败项、本地日志路径和每项最多 8 条关键错误行，通常无需再打开完整日志；需求命令报告状态、进度、剩余 AC 和下一步。追加 `--json` 输出完整结构，供脚本或诊断使用。

## 状态

```sh
python3 scripts/teamflow.py req state REQ-20260101-a3f9 --state 阻塞 --blocked 待确认 --reason "等待选择登录方式"
python3 scripts/teamflow.py req state REQ-20260101-a3f9 --state 进行中 --reason "用户已选择短信登录"
```

`--blocked` 取值 `待确认`、`外部`、`暂停`，只用于阻塞。恢复时清除阻塞类型、原因和排队标记，并在“决策与异常”追加记录。

## 人工证据

仅在适用自动检查不存在且实际人工核对足够时使用：

```sh
python3 scripts/teamflow.py req complete REQ-20260101-a3f9 \
  --evidence "实际核对结论及可定位证据" --evidence-input docs --confirm-ac AC-01
```

`--evidence-input` 可重复，只允许项目相对文件/目录；省略时绑定整个项目的 Git 可见输入。始终额外绑定本需求语义（规则见 [CHECKS](CHECKS.md#证据)）；目录内新增文件也使证据失效，忽略生成证据和其他需求记录。显式文件范围外的变化不会使证据失效，因此范围必须覆盖实际影响面。

需求语义或文件快照变化、旧证据缺少源码绑定时，不迁移旧结论，重新实际核对并提供新的 `--evidence`。项目已配置检查且人工范围内存在代码变更时，使用自动证据并通过 `--confirm-ac` 确认人工条件；人工文字不能替代必要自动验证。

`git check` 的人工证据仅支持 `.md`、`.rst`、`.txt` 文档/记录，仍核对文件范围和暂存快照；这些扩展名不是语义证明，脚本或业务数据即使使用文本扩展名也必须执行实际适用检查。

## 升级与提交前检查

```sh
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v1.2.1.zip --plan
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v1.2.1.zip
python3 scripts/teamflow.py setup --git-hook change
python3 scripts/teamflow.py setup --no-git-hook
```

- `upgrade` 按安装清单替换当前模式的核心与 Skill，移除新版不再包含的旧文件。有本地改动或包不含当前模式时拒绝；`--force` 覆盖本地改动，`--mode` 同时切换模式。不触碰 `.agents/team/`、需求卡和项目配置。
- `setup --git-hook` 为本机安装 pre-commit，提交前通过 `git hook --profile <名>` 复核覆盖暂存内容且仍有效的需求证据；缺失或失效直接报错，不自动跑测试；`--no-git-hook` 只移除 TeamFlow 管理的 Hook。规则见 [INSTALL](INSTALL.md#提交前检查可选)。

## 只读辅助

```sh
python3 scripts/teamflow.py doctor
python3 scripts/teamflow.py verify suggest
python3 scripts/teamflow.py req status REQ-20260101-a3f9
```

- `doctor` 汇总接入、验证配置与输入、占位卡片、失效证据及已启用模块索引，默认每项一行，`--json` 输出完整结构。已完成需求的自动证据与交付提交（卡片记录该证据的提交）输入一致时视为交付时有效，之后的代码演进不再提示；已提交但对不上的列为历史提示，不计入需处理；完成后未提交即失效的计入需处理。`req complete` 与 `git check` 仍按当前内容校验。Git 跟踪文件达到 1000 个且未启用模块索引时给出提示。发现需处理项退出 1，不执行修复或项目检查；不因工具仓库缺少 Xcode 强制阻塞。
- `verify suggest` 列出相对 HEAD 的暂存、未暂存和未跟踪改动、各 profile 覆盖和遗漏路径，以及 `req complete` 会自动选用的 profile。只按路径建议，不能判断某项测试足以验证业务语义；不执行检查。
- `req pr` 由需求卡生成 PR 标题与正文，`git ci --base <基线>` 供 CI 核对基线之后改动的完成卡证据，用法见 [REVIEW](REVIEW.md)。
- `req status` 汇总状态、进度、证据有效性与问题、剩余 AC 和下一步，`--json` 另含范围、AC 与决策记录。不修改状态，不自动恢复阻塞或取消，不为已完成需求扩张交付。

这些命令按需使用，不成为每个需求的强制前置。历史提示只说明旧证据不能复用，不自动重开已交付需求。
