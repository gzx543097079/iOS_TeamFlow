# 验证与证据

主流程与停止条件见 [WORKFLOW](WORKFLOW.md)。首次使用环境或环境变化时，低成本核对工具、依赖、Scheme/Target、设备及目标所需账号；命令来自实际工程或 CI，不猜测，也不把完整构建当预检。

## 运行

```sh
python3 scripts/teamflow.py verify init
# 编辑 .agents/project-checks.json
python3 scripts/teamflow.py verify suggest --requirement REQ-20260101-0001
python3 scripts/teamflow.py verify run --profile change --requirement REQ-20260101-0001
```

声明检查 `covers` 后改动按各检查的 `covers`/`inputs` 逐项触发（`trigger: "covers"` 时只按 covers），修改验证配置只触发执行语义变化的检查；声明了 check 或 profile `covers` 时，范围外的工程改动在执行前报错。`manual: true` 的 profile 只在显式指定时执行。编辑 `.agents/project-checks.json`，或 `upgrade`/`doctor` 提示验证配置待迁移时，读[验证配置与迁移](CHECKS-CONFIG.md)。

## 验证强度与结果输出

支付、认证、数据迁移、共享状态和工程配置即使改动小也须补齐专项验证；是否可按小改动降强度见 [WORKFLOW 改动分级](WORKFLOW.md#改动分级)。路径匹配只能提供选择线索，不能证明测试充分；用户视觉确认不替代行为与契约类自动证据。测试命令必须能识别空套件，不能把“0 个测试”当通过。

失败时先用测试框架的单用例过滤等方式定位，修复后复核受影响范围；同一 profile 上次运行失败时，再次运行只执行失败项与检查级指纹变化项，上次通过项复用，`cache: false` 与 `--rerun` 例外，不要求 `incremental`。只有一个大 check 的 profile 仍整体重跑，需拆分检查才能受益。

开始执行前输出将执行与复用的检查、按各检查最近实际耗时估算的预计时间（无历史时注明）和结果文件路径。宿主不支持完成通知时，按预计耗时等待一次再查看结果文件，不预设远超预计的 sleep。输出区分本次执行、复用通过及未触发；没有触发项时返回“无需检查”，不生成通过证据、不自动完成需求。纯文档记录可使用实际人工核对。缺环境、工具、模拟器或账号是“未验证”，不能解释为未触发，更不能临时改 profile 绕过；需求保持进行中。

## 证据

- **运行**：日常 `verify run --profile <名> --requirement <编号>` 按触发模块检查，结果留在本地日志，不自动修改需求卡。`req complete --profile` 优先复用卡上有效摘要，其次复用本需求最近一次当前有效且覆盖必要检查的运行结果，否则执行适用项；最新结果失败或缺项时不回退到更早的通过结果；必要检查含 `cache: false` 时重新执行。两者的 `--rerun` 均强制执行显式 profile 的全部检查并绕过缓存。日志保存在 `logs/project-checks/<运行编号>/`，只作本地记录。
- **指纹**：绑定配置、实际通过检查的完整输入内容与可执行位、检查名单及需求语义。check 的范围外依赖也进入总证据；未触发项不贡献覆盖或额外输入。新证据采用 v6，旧 v4/v5 证据仍按原范围复核。失败、超时或运行中输入改变不算通过。
- **需求语义**：绑定范围、不包含和按编号排序的 AC 文字；标题、状态、勾选、排版与决策不影响证据。范围或 AC 文字变化必须重新验证，不能只替换摘要。独立检查未绑定需求时不能直接用于完成卡片。
- **复核**：提交钩子与 CI 按实际检查覆盖核对，不执行测试、不依赖本地日志；提交另比较暂存快照。旧证据按旧完整 profile 规则复核，新部分证据不能借 profile 的宽范围放行。
- 工具测试不替代真机、视觉、账号或平台验收；人工 AC 按主流程保留待验证。安全与 Git 边界见 [BOUNDARIES](BOUNDARIES.md)，参数见 [COMMANDS](COMMANDS.md)。
