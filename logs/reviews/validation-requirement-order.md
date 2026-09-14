# 需求编号与排序验证

时间：2026-09-12T22:43:42+08:00

- `python3.12 -m unittest discover -s tests -p test_delivery.py`：30 项通过，11.419 秒；日志 /tmp/teamflow-sort-delivery.log。
- `python3.12 scripts/run_workflow_checks.py --full`：109 项通过，35.507 秒；包含真实 ZIP 接入、双分支建卡合并、提交关联、验收、门禁及选择器。日志 /tmp/teamflow-sort-full.log，SHA256：1d6e4921f595ae1cdee2050c1f6e3fabdeb72945f6ae95aeaabe4a8d023ff839。
- 新增固定 UTC 毫秒与同目录撞号重试测试，确认不覆盖；列表覆盖跨日顺序、倒序稳定序号、未同步卡、标题竖线转义、JSON 及只读。旧数字/UUID 和无效日期/时分拒绝，历史原件保持。
- 当前项目实际运行 list 与 list --reverse --json，正确显示本需求编号、UTC 创建时间、标题与当前状态。git diff --check 通过；文档与分发校验已包含在完整套件。
- 语义核对：序号只用于浏览，固定 ID 用于引用；无共享递增文件，跨分支随机后缀降低同毫秒碰撞风险；本地排他创建最多重试 128 次。机器时钟偏差与同毫秒先后不作严格因果保证。
- 不兼容旧编号、不自动迁移。新概览只收录新格式，旧卡/交付原件保留，旧概览可从 Git 历史查看。未改变 App 或执行 ios-demo profile，未提交/发布。
