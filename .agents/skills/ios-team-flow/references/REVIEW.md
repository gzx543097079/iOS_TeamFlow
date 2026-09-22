# 提交前自动审查与去重

这是 Codex 必须执行的语义审查流程。Python 门禁校验报告与改动匹配，不能代替代码理解，也不是不可绕过的签名系统。无需为每次普通审查询问许可。

## 范围与步骤

1. 核对工作区和暂存区，确认本次范围；默认 `git diff --cached`，包含新增、删除、重命名、资源、配置、锁文件和构建设置。只审本次改动，必要时读取调用者/产品配置作为上下文；发现历史问题单独标注，不擅自扩大整改。
2. 完成需求卡和测试证据；完整卡实际验收完成时先执行一次 finish --accept，轻量卡不执行 finish。将本次文件暂存（保留用户已有暂存内容，不能用 git add . 混入无关工作）。引用实际测试 result 到报告；最终 check 统一核对测试与暂存对象，独立 verify 仅用于排错。然后运行 `python3 scripts/review_gate.py prepare`。脚本输出指纹、暂存树、所需维度及 JSON 报告路径；已完成且完全匹配则输出“复用”，直接 check。
3. 用输出的 `diff_command` 或等价 `git diff --cached` 读取暂存对象，不能只读工作区文件（部分暂存时两者不同）。只完成报告 `required_checks` 列出的核心及风险维度，填写 status 与 evidence；再填 summary、reviewer、completed_at、findings、blockers、requirements 和 validation_results。风险被明确接受时记录理由/负责人，不能伪填通过。需要主动扩大范围时可用 `prepare --risk subscription|memory|analytics|test_artifacts`；重大、未知或显式全量审查用 `prepare --full`。
4. 完成报告后只需 `git add logs/reviews/<指纹>.json`，再运行 `python3 scripts/review_gate.py check`。check 只读取暂存区报告并重新计算 HEAD、暂存差异和测试对象；有失败、未验证或 blocker 时不通过。问题修复后重新暂存，同一 HEAD 下运行 `prepare --continue-from 前次完整指纹`，工具通过前后暂存树动态计算差量并携带材料；当前 required_checks 仍须重新确认，不生成或提交 patch/delta.patch。
5. 有提交授权才 commit。上一步 check 通过且内容未变时不再调用；启用 Hook 时可由提交时 Hook 承担最终门禁。commit 后不再 finish：Requirement trailer 和交付概览由 Git 动态查询。若新 HEAD、规范或其他暂存内容变化，旧审查不能直接通过。

## 核心与风险维度

| JSON key | 内容与判定证据 |
| --- | --- |
| correctness | 验收一致性、边界/空值、错误处理、兼容性、线程安全、资源变更、测试覆盖；注明跑了哪些检查；新主 App 或生命周期变更同时核对 [Scene 启动证据](APP-LIFECYCLE.md)，按 UIKit / SwiftUI 实际入口判定。 |
| standards | 按 [架构一致性](ARCHITECTURE.md) 核对需求架构、实际职责/依赖与复用调用方；不以目录或类型名称代替实现证据。按 OC / Swift / SwiftUI / UI 加载规范，混编兼顾桥接；按中文注释规范核对本次职责、契约和关键原因的说明及准确性；不要因个人偏好提出无关重构。 |
| subscription | 产品 ID ↔ 选中套餐 ↔ 周期/权益 ↔ StoreKit 本地化价格 ↔ 试用资格/续订文案 ↔ CTA ↔ 购买参数。检查远程开关、String Catalog、StoreKit 配置及可得的 App Store Connect 产品证据。验证恢复、pending、取消、失败、重复交易、退款撤销；实际商品配置不可得时明确未验证，不能宣称价格正确。 |
| memory | owner/闭包/代理/计时器/通知/订阅/Task/CF/C++ 所有权，页面退出后释放和取消；风险路径用 Memory Graph / Leaks / Allocations 或针对性测试。静态无发现只证明审查范围内无明显问题，不证明无泄漏。 |
| analytics | 对照需求事件表检查命名、参数、触发时机、重复曝光、购买成功必须在验证后、取消与失败区分、隐私脱敏；已有契约不可得时记录缺项，不凭空新增事件。 |
| test_artifacts | 生产 target 中的 mock、硬编码测试帐号/价格、localhost/测试环境、debug 菜单、print/NSLog、跳过校验、强制成功/VIP、临时开关；结合 Release 构建条件判断，正常 Tests/Preview 不当作泄露。日志组件接入时核对实际 Target 成员及两种语言的编译条件、Release 消息不求值和无输出证据。 |
| security | 本次改动的凭据、权限、隐私、输入验证与日志；涉及系统权限时对照 PRD 的首版权限清单，核对实际 Target 用途 key、多语言提示、能力配置、请求时机、拒绝/部分授权处理及 SDK 访问。只基于具体代码证据报告问题。 |

correctness、standards、security 始终必查。运行时源码自动增加 memory 与 test_artifacts；脚本或运行配置增加 test_artifacts；差异命中 StoreKit/购买或事件/打点信号时增加 subscription 或 analytics。文件过多、类型未知或路由不可靠时自动回退全部七维。路由结果是最低范围，审查人发现风险时必须用 --risk 或 --full 扩大，不能靠改名规避。通过项写一句可核对结论及证据；问题仍按 findings 完整记录，不用统一套话代替语义审查。

订阅适用时，evidence 附逐产品映射表（可链接 `logs/` 的脱敏 Markdown），至少产品 ID、周期、展示价格来源、CTA、实购 ID、地区/语言、验证环境、结果。不能只写“已检查”。

findings 使用 `{id, severity, file, line, trigger, impact, recommendation, status}`，严重度 P0/P1/P2/P3，status 为 open/fixed/accepted；接受必须附 reason 和 accepted_by，实际阻塞仍放 blockers。失败/未验证维度不可仅靠接受问题绕过。

当前报告指纹/路径仅保存在回执中，回执单向关联需求编号；需求卡不嵌入覆盖自身的当前指纹，也不在 prepare 后为写“审查通过”修改卡片。需要修复业务或需求时生成新快照，只复查变化。

续审保留前次需求、测试引用、发现、阻塞和仍适用的维度证据，`previous_status` 仅供对照；当前 required_checks 全部重置为未验证，审查人、完成时间和结论重新填写，不自动关闭问题或批准变化。最终 check 仍核对所需维度及引用测试；测试过期时更新引用。前次报告必须包含匹配的暂存树快照；差异通过 Git tree 动态计算。缺失快照或 HEAD 改变时重新 prepare 完整审查，不猜测旧对象。

## 指纹和记录边界

指纹由 HEAD、暂存 diff（二进制、文件模式和路径）组成。没有 HEAD 的初始仓库使用空树。默认审查所有暂存路径，唯一排除 `logs/reviews/` 审查回执目录以避免自引用；新回执只生成 JSON。旧 patch 可从 Git 历史读取但不再生成或保留在当前树；目录仍禁止可执行代码或业务资源。其变更应检查隐私与记录真实性。

未跟踪/未暂存文件不会进入本次提交审查，prepare 会提示数量；提交前核实有无漏暂存的新文件。不支持用此指纹替代显式要求的全仓或提交范围审计；这类范围另记基准 SHA 和范围。

普通 Git 客户端可把 `python3 scripts/review_gate.py check` 接入既有 pre-commit hook（先合并已有 hook，不覆盖）。本包不修改团队全局 Git 配置。无 Codex 的 Git 客户端不会自动生成语义报告，会由门禁提示先完成审查。

## 可选本地 Hook

按 [Git 检查说明](GIT-CHECKS.md) 可选安装本地 Hook，在 `git commit` 前核对暂存内容已有匹配审查。Hook 可以用 `--no-verify` 跳过，不作为远端强制门禁；已提交范围的审计另行记录明确基准和对象。

## 外部事实记录

提交 SHA、提交数量和交付概览均动态查询，不再创建纯归档提交。PR、Release、人工关联纠错或其他无法从本地 Git 推导的事实变化时，相关 JSON 与普通改动一起接受风险路由审查；仅在兼容旧项目遗留归档操作时保留 `prepare --previous`，新流程不使用它。

待团队验收不禁止已授权的阶段性提交、推送或 PR；按实际状态保存需求和已执行证据，不为提交改成完成。合并和发布是否需要团队验收由既有团队规则及本需求决定。
