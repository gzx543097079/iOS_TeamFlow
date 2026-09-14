# 2.1.0 发布验证

时间：2026-09-14T17:00:41+08:00

- `python3.12 scripts/run_workflow_checks.py --full`：110 项通过，35.664 秒，退出码 0；含异常卡容错、模板落地、验收门禁、升级与真实 ZIP 消费。
- 日志 /tmp/teamflow-2.1.0-full.log，SHA256：22e4219d4efe7f6dd125319caead082f50d55a4e0fef56841981d0aa4403e767。
- skill-creator quick_validate 通过；双分发包和 SHA256 生成成功。VERSION、teamflow.json、下载链接、CHANGELOG 对齐 2.1.0；diff 格式检查通过。
- 进化规程语义场景及包内内容验证见 validation-evolution.md，异常卡行为见 validation-card-tolerance.md；实际长期效率收益仍未测量。
- 本次无 App 变化，ios-demo 不适用。线上发布及提交事实由交付工具另行核实。
