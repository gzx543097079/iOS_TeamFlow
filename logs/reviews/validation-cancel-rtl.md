# 取消默认 RTL 需求

时间：2026-09-14T17:28:08+08:00

- 用户取消最近的 RTL 需求；原 f238dba 已推送，追加撤销提交，不重写远端历史。
- 核对 `git diff a6c600b -- .agents scripts tests .github README.md` 无差异，全部规则、组件、工具、测试、CI 与版本恢复日志需求完成时的 2.1.1。中文注释和自动日志接入保留。
- 复用完全相同输入的 validation-2.1.1.md：113 项完整回归通过；原生和生成工程验证见 validation-logging.md。无源码新变化，不重复相同本地测试。
- RTL 卡标已取消，当前 AC 为不适用并说明取消原因；原通过证据和 Git 历史保留。finish 成功，无过期项；diff 格式检查通过。不创建 Release，不移动标签。
