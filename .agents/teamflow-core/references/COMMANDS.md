# 命令参考

证据机制见 [CHECKS](CHECKS.md)，主流程见 [WORKFLOW](WORKFLOW.md)。

## 验证与完成

原则与双模式见 [WORKFLOW](WORKFLOW.md#实施与验收)；触发与证据见 [CHECKS](CHECKS.md)。

- `verify run --profile <名> [--requirement <编号>]`：按 covers 只跑触发项；`--rerun` 强制全项。
- `req complete … --profile <名>`：复用与执行规则见 [CHECKS#证据](CHECKS.md#证据)。`--result` / `--evidence` 与 `--profile` 互斥；`--rerun` 须带 `--profile`。
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

仅在适用自动检查不存在且实际人工核对足够时使用。项目已配置检查时，人工范围内（及本需求已提交的改动中）只能有 `.md`、`.rst`、`.txt` 文档/记录；脚本、场景、资源和配置均须自动验证，人工文字不能替代必要自动验证。指纹与失效规则见 [CHECKS#证据](CHECKS.md#证据)。

```sh
python3 scripts/teamflow.py req complete REQ-20260101-a3f9 \
  --evidence "实际核对结论及可定位证据" --evidence-input docs --confirm-ac AC-01
```

`--evidence-input` 可重复，只允许项目相对文件/目录；省略时绑定整个项目的 Git 可见输入。`git check` 的人工证据同一白名单，仍核对文件范围和暂存快照；文本扩展名不是语义证明。

## 安装、升级与提交前检查

步骤与 Hook 细则见 [INSTALL](INSTALL.md)。常用入口：

```sh
unzip -p ~/Downloads/teamflow-ios-v1.6.5.zip install_teamflow.py | python3 - ~/Downloads/teamflow-ios-v1.6.5.zip --mode ios
python3 scripts/teamflow.py install ~/Downloads/teamflow-ios-v1.6.5.zip --mode ios
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v1.6.5.zip [--plan]
python3 scripts/teamflow.py verify init
python3 scripts/teamflow.py setup --git-hook
python3 scripts/teamflow.py setup --no-git-hook
```

`git check` 暂存了验证配置时，列出命令或范围有变化、但未经本次证据执行的其他 profile，需人工核对后再提交。

## 只读辅助

```sh
python3 scripts/teamflow.py doctor
python3 scripts/teamflow.py verify suggest
python3 scripts/teamflow.py req status REQ-20260101-a3f9
```

- `doctor`：接入、验证配置、占位卡、失效证据与模块索引摘要；需处理项退出 1。细则见命令帮助与 [INSTALL](INSTALL.md)。
- `verify suggest`：改动相对各 profile 的覆盖/遗漏与最近耗时，不执行检查；触发与复用见 [CHECKS](CHECKS.md)。
- `req pr` / `git ci`：见 [REVIEW](REVIEW.md)。
- `req status`：状态、进度、证据问题与下一步；`--json` 含范围与 AC。

这些命令按需使用，不成为每个需求的强制前置。
