# 2.1.1 源码版本验证

时间：2026-09-14T17:22:05+08:00

- `python3.12 scripts/run_workflow_checks.py --full`：113 项通过，37.186 秒，退出码 0；包含最终 2.1.1 版本下的分发、安装、升级、模板和门禁。
- 日志 /tmp/teamflow-2.1.1-full.log，SHA256：74c21d37de3fb33e2e3035f9625c89c8b0344830992d13e4ae4ba8adf1b3cfd1。
- 组件原生 Debug/Release 输出、Release 不求值及实际生成工程构建证据见 validation-logging.md；对应组件、安装脚本、原生检查及生成规则在本次版本更新期间未变化。
- VERSION、teamflow.json、README 当前源码版本为 2.1.1；下载链接明确指向上一次正式 Release 2.1.0，不创建新 Release、不移动标签。CI YAML 解析通过，发布上传依赖原生日志验证。
- 按用户要求每需求一次提交：中文注释规则已独立提交；日志及自动工程接入、2.1.1 版本合为第二次提交。第一需求的生成交付记录顺带归档，第二需求提交后生成记录留待下次归档，不追加第三次提交。
