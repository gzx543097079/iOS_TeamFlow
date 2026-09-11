# 提交前自动审查与去重

这是 Codex 必须执行的语义审查流程。Python 门禁校验报告与改动匹配，不能代替代码理解，也不是不可绕过的签名系统。无需为每次普通审查询问许可。

## 范围与步骤

1. 核对工作区和暂存区，确认本次范围；默认 `git diff --cached`，包含新增、删除、重命名、资源、配置、锁文件和构建设置。只审本次改动，必要时读取调用者/产品配置作为上下文；发现历史问题单独标注，不擅自扩大整改。
2. 将本次文件暂存（保留用户已有暂存内容，不能用 git add . 混入无关工作）。运行 `python3 scripts/review_gate.py prepare`。脚本输出指纹、快照及 JSON 报告路径；已完成且完全匹配则输出“复用”，直接 check。
3. 新报告读取 `logs/reviews/<指纹>.patch` 与暂存对象，不能只读工作区文件（部分暂存时两者不同）。完成下表所有维度，填写每项 status（通过/失败/未验证/不适用）与 evidence；填 summary、reviewer、completed_at、findings 和 blockers。风险被明确接受时记录理由/负责人，不能伪填通过。
4. 运行 `python3 scripts/review_gate.py check`。有失败、未验证或 blocker 时门禁不通过；“不适用”只用于确实无关维度，不用于缺工具或缺线上配置。已验证的问题修复后重新暂存，prepare 新快照，在报告 previous_review 指向旧指纹，只复查两个快照间变化与受影响问题，其余证据注明复用来源。
5. 有提交授权才 commit。提交前最终 check，commit 后将 SHA 关联到需求卡；报告元数据后续单独归档不触发同一代码重复审查。若新 HEAD 或规范/其他暂存内容变化，旧审查不能直接通过。

## 必查维度

| JSON key | 内容与判定证据 |
| --- | --- |
| correctness | 验收一致性、边界/空值、错误处理、兼容性、线程安全、资源变更、测试覆盖；注明跑了哪些检查。 |
| standards | 按 OC / Swift / SwiftUI / UI 加载规范，混编兼顾桥接；不要因个人偏好提出无关重构。 |
| subscription | 产品 ID ↔ 选中套餐 ↔ 周期/权益 ↔ StoreKit 本地化价格 ↔ 试用资格/续订文案 ↔ CTA ↔ 购买参数。检查远程开关、String Catalog、StoreKit 配置及可得的 App Store Connect 产品证据。验证恢复、pending、取消、失败、重复交易、退款撤销；实际商品配置不可得时明确未验证，不能宣称价格正确。 |
| memory | owner/闭包/代理/计时器/通知/订阅/Task/CF/C++ 所有权，页面退出后释放和取消；风险路径用 Memory Graph / Leaks / Allocations 或针对性测试。静态无发现只证明审查范围内无明显问题，不证明无泄漏。 |
| analytics | 对照需求事件表检查命名、参数、触发时机、重复曝光、购买成功必须在验证后、取消与失败区分、隐私脱敏；已有契约不可得时记录缺项，不凭空新增事件。 |
| test_artifacts | 生产 target 中的 mock、硬编码测试帐号/价格、localhost/测试环境、debug 菜单、print/NSLog、跳过校验、强制成功/VIP、临时开关；结合 Release 构建条件判断，正常 Tests/Preview 不当作泄露。 |
| security | 本次改动的凭据、权限、隐私、输入验证与日志；只基于具体代码证据报告问题。 |

订阅适用时，evidence 附逐产品映射表（可链接 `logs/` 的脱敏 Markdown），至少产品 ID、周期、展示价格来源、CTA、实购 ID、地区/语言、验证环境、结果。不能只写“已检查”。

findings 使用 `{id, severity, file, line, trigger, impact, recommendation, status}`，严重度 P0/P1/P2/P3，status 为 open/fixed/accepted；接受必须附 reason 和 accepted_by，实际阻塞仍放 blockers。失败/未验证维度不可仅靠接受问题绕过。

## 指纹和记录边界

指纹由 HEAD、暂存 diff（二进制、文件模式和路径）组成。没有 HEAD 的初始仓库使用空树。默认审查所有暂存路径，唯一排除 `logs/reviews/` 审查回执目录以避免自引用；该目录只准报告 JSON、快照 patch 和说明文档，禁止存放可执行代码或业务资源。其变更仍应检查隐私与记录真实性；门禁会拒绝该目录内非回执后缀文件。

未跟踪/未暂存文件不会进入本次提交审查，prepare 会提示数量；提交前核实有无漏暂存的新文件。不支持用此指纹替代显式要求的全仓审计或 PR 多提交审查；这类范围另记基准 SHA 和范围。

普通 Git 客户端可把 `python3 scripts/review_gate.py check` 接入既有 pre-commit hook（先合并已有 hook，不覆盖）。本包不修改团队全局 Git 配置。无 Codex 的 Git 客户端不会自动生成语义报告，会由门禁提示先完成审查。
