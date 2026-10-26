# 命令参考

证据机制见 [CHECKS](CHECKS.md)，主流程见 [WORKFLOW](WORKFLOW.md)。

## 验证与完成

原则与双模式见 [WORKFLOW](WORKFLOW.md#实施与验收)；触发与证据见 [CHECKS](CHECKS.md)。

- `verify run --profile <名> [--requirement <编号>]`：按 covers 只跑触发项；`--rerun` 强制全项。
- `req complete … --profile <名>`：优先复用卡上有效摘要，其次本需求最近有效完整结果，否则跑必要检查。`--result` / `--evidence` 与 `--profile` 互斥；`--rerun` 须带 `--profile`。
- 确认：`--confirm-ac` / `--user-confirmed` / `--waive-human`（免除须同时勾选）可重复；`--wait-user` 输出勾选表。AC 文字变则旧确认失效。
- `req pr`：默认仅完整交付；阶段交付加 `--allow-stage`。
- `git check` / hook：进行中可阶段提交；待用户验证，或完成但人工 AC 未确认/未免除则拒绝。

## 可选宿主审批

`permissions --mode strict|default [--plan]` 显式启用严格模板或移除未改动的旧模板；自定义内容不覆盖，默认安装不激活。迁移边界见 [安装说明](INSTALL.md#宿主权限)。

## 输出

`verify run` 与需运行检查的 `req complete` 开始前向 stderr 输出执行计划、预计耗时与结果路径，`--json` 输出不受影响；失败时提示再次运行只重跑失败项。所有命令默认输出几行简短摘要：验证区分通过、失败、复用与未触发，失败时附失败项、本地日志路径和每项最多 8 条关键错误行，通常无需再打开完整日志；需求命令报告状态、进度、剩余 AC 和下一步。追加 `--json` 输出完整结构，供脚本或诊断使用。

## 状态

```sh
python3 scripts/teamflow.py req state REQ-20260101-a3f9 --state 阻塞 --blocked 待确认 --reason "等待选择登录方式"
python3 scripts/teamflow.py req state REQ-20260101-a3f9 --state 进行中 --reason "用户已选择短信登录"
python3 scripts/teamflow.py req state REQ-20260101-a3f9 --state 进行中 --reopen-ac AC-01 --reason "同一缺陷复发"
```

`--blocked` 取值 `待确认`、`外部`、`暂停`，只用于阻塞。恢复时清除阻塞类型、原因和排队标记，并在“决策与异常”追加记录。重开完成的需求必须用可重复的 `--reopen-ac` 取消需重新验收的 AC（同时移出 `user_confirmed` 与 `human_waived`），否则下一次 `req complete` 会复用证据直接判回完成。

## 人工证据

仅在适用自动检查不存在且实际人工核对足够时使用。项目已配置检查时，人工范围内（及本需求已提交的改动中）只能有 `.md`、`.rst`、`.txt` 文档/记录，与 `git check` 使用同一白名单；脚本、场景、资源和配置均须自动验证：

```sh
python3 scripts/teamflow.py req complete REQ-20260101-a3f9 \
  --evidence "实际核对结论及可定位证据" --evidence-input docs --confirm-ac AC-01
```

`--evidence-input` 可重复，只允许项目相对文件/目录；省略时绑定整个项目的 Git 可见输入。始终额外绑定本需求语义（规则见 [CHECKS](CHECKS.md#证据)）；目录内新增文件也使证据失效，忽略生成证据和其他需求记录。显式文件范围外的变化不会使证据失效，因此范围必须覆盖实际影响面。

需求语义或文件快照变化、旧证据缺少源码绑定时，不迁移旧结论，重新实际核对并提供新的 `--evidence`。人工范围内存在非文档改动时，使用自动证据并通过 `--confirm-ac` 确认人工条件；人工文字不能替代必要自动验证。

`git check` 的人工证据仅支持 `.md`、`.rst`、`.txt` 文档/记录，仍核对文件范围和暂存快照；这些扩展名不是语义证明，脚本或业务数据即使使用文本扩展名也必须执行实际适用检查。

## 安装、升级与提交前检查

```sh
unzip -p ~/Downloads/teamflow-ios-v1.6.4.zip install_teamflow.py | python3 - ~/Downloads/teamflow-ios-v1.6.4.zip --mode ios
python3 scripts/teamflow.py install ~/Downloads/teamflow-ios-v1.6.4.zip --mode ios
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v1.6.4.zip --plan
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v1.6.4.zip
python3 scripts/teamflow.py verify init
python3 scripts/teamflow.py setup --git-hook
python3 scripts/teamflow.py setup --no-git-hook
```

- `install` / 包内 `install_teamflow.py`：从 ZIP 一键接入，写入核心与 Skill、刷新入口，并在缺失时生成验证配置与检查脚本骨架（不覆盖已有）。已安装时请用 `upgrade`；`--force` 覆盖安装文件后重新接入。见 [INSTALL](INSTALL.md#一键安装推荐) 与仓库 README。
- `upgrade` 按安装清单替换当前模式的核心与 Skill，移除新版不再包含的旧文件。有本地改动或包不含当前模式时拒绝；`--force` 覆盖本地改动，`--mode` 同时切换模式。不触碰 `.agents/team/`、需求卡和项目配置；旧形态时报告“验证配置待迁移”，Agent 按 README「验证配置迁移」处理。
- `verify init` 按当前模式补生成缺失的验证资产；已存在的文件不覆盖。
- `setup --git-hook` 为本机安装 pre-commit，提交前通过 `git hook` 复核覆盖暂存内容且仍有效的需求证据（自动或文档人工证据，不限定 profile）；仅含 `.md`/`.rst` 文档（不含需求卡）的暂存直接放行；缺失或失效直接报错，不自动跑测试；`--no-git-hook` 只移除 TeamFlow 管理的 Hook。规则见 [INSTALL](INSTALL.md#提交前检查可选)。
- `git check` 暂存了验证配置时，列出命令或范围有变化、但未经本次证据执行的其他 profile，需人工核对后再提交。

## 只读辅助

```sh
python3 scripts/teamflow.py doctor
python3 scripts/teamflow.py verify suggest
python3 scripts/teamflow.py req status REQ-20260101-a3f9
```

- `doctor` 汇总接入、验证配置与输入、占位卡片、失效证据及已启用模块索引，默认每项一行，`--json` 输出完整结构。已完成需求的自动证据与交付提交（卡片记录该证据的提交）输入一致时视为交付时有效，之后的代码演进不再提示；已提交但对不上的列为历史提示，不计入需处理；完成后未提交即失效的计入需处理。`req complete` 与 `git check` 仍按当前内容校验。Git 跟踪文件达到 1000 个且未启用模块索引时给出提示。发现需处理项退出 1，不执行修复或项目检查；不因工具仓库缺少 Xcode 强制阻塞。
- `verify suggest` 列出相对 HEAD 的暂存、未暂存和未跟踪改动（`--requirement` 另计该需求带尾注的已提交改动）、各 profile 覆盖和遗漏路径、各 profile 最近一次通过的实际耗时，以及 `req complete` 会自动选用的 profile。只按路径建议，不能判断某项测试足以验证业务语义；不执行检查。`verify suggest` 同时显示各 check 的触发和跳过情况，manual profile 标为仅显式执行。检查默认顺序，显式设置 parallelism 才并行；incremental profile 中指纹未变的检查复用上次通过结果，输出标明“复用上次通过（未重跑）”。
- `req pr` 由需求卡生成 PR 标题与正文，`git ci --base <基线>` 供 CI 核对基线之后改动的完成卡证据，用法见 [REVIEW](REVIEW.md)。
- `req status` 汇总状态、进度、证据有效性与问题、剩余 AC 和下一步，`--json` 另含范围、AC 与决策记录。不修改状态，不自动恢复阻塞或取消，不为已完成需求扩张交付。

这些命令按需使用，不成为每个需求的强制前置。历史提示只说明旧证据不能复用，不自动重开已交付需求。
