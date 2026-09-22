---
name: ios-team-flow
description: 中文 iOS 需求分析、实施、验证与显式交付工作流。用于 Objective-C、Swift、SwiftUI 和 App 发布动作。
---

# iOS 工作流入口

PROJECT_ROOT 是当前 Git 根及其目录树；只使用本项目内的 Skill。处理空间外文件或其他项目之前，说明对象、原因和操作并取得用户本次明确允许。任务所需开发工具使用官方或既有包管理器默认位置；需要管理员权限、密码、登录或系统确认时停止并交给用户处理。

先读 [WORKFLOW](references/WORKFLOW.md)。同会话已读且文件未变化时不重读。只按当前工作加载专题：

| 当前工作 | 资料 |
| --- | --- |
| 新 App 启动 | [启动模板](references/templates/new-project.md) |
| 当前功能分析 | [功能模板](references/templates/feature.md) |
| 已有工程现状 | [EXISTING-PROJECT](references/EXISTING-PROJECT.md) |
| 大型项目模块路由 | [MODULE-CONTEXT](references/MODULE-CONTEXT.md) |
| 业务代码或架构调整 | [ARCHITECTURE](references/ARCHITECTURE.md) |
| Bug 修复 | [BUGFIX](references/BUGFIX.md) |
| 构建与测试 | [PROJECT-CHECKS](references/PROJECT-CHECKS.md) |
| 用户明确要求 commit、push、PR、标签或 GitHub Release | [GIT-ACTIONS](references/GIT-ACTIONS.md) |
| 用户明确要求 Archive、TestFlight、审核、发布或下架中的某一动作 | [APP-RELEASE](references/APP-RELEASE.md) |
| 新 App 或生命周期变化 | [APP-LIFECYCLE](references/APP-LIFECYCLE.md) |
| 新工程日志组件 | [LOGGING](references/LOGGING.md) |
| 已复现流程缺陷或明确工作方式纠正 | [EVOLUTION](references/EVOLUTION.md) |

修改业务代码时按实际语言读取 OC、Swift、SwiftUI 与 UI 规范，并遵守中文注释规则。已有项目明确约定优先，不顺手迁移无关代码。

问答、检查和只读分析不建需求。开发变更使用 `python3 scripts/teamflow.py req create --title "标题"` 建立唯一需求卡；同一需求续接原卡。需求完成不自动授权 Git 或 App 外部动作。

需求卡和需求列表始终用彩色图标显示状态与 AC 进度：状态使用固定语义映射，未开始/部分完成/全部完成的进度分别显示 `⚪` / `🔵` / `✅`；不得只写无图标状态。

有实现与交付的任务默认按固定顺序执行：完成全部改动 → 环境预检 → 针对性测试 → 文件冻结 → 一次完整验证 → 目标交付。完整验证前先同步本次代码、测试、文档、配置、版本和需求范围；完整验证后如其输入变化，原证据失效并重新执行，不为了凑“一次”沿用旧结果。详细规则见 [PROJECT-CHECKS](references/PROJECT-CHECKS.md)。

任何外部或共享状态写入都必须由用户明确指出目标动作。目标动作若客观依赖尚未完成的前置步骤，自动执行最小必要前置，不再逐项索要授权；例如发布当前 GitHub Release 可补齐验证、commit、push 和标签。目标授权不向后续动作、可选配置或相邻动作扩张：commit 不自动 push，push 不自动创建 PR，PR 不自动合并，TestFlight 上传不自动分发，审核不自动发布。无法确定目标、前置需要额外业务选择或会越出当前范围时停止并询问。

“上传 TestFlight”本身不授权启用 `TestFlight Internal Only`。只有用户明确要求“仅内部测试”或明确点名该选项时，才允许将 ExportOptions 的 `testFlightInternalTestingOnly` 设为 `true`；否则必须省略该键。

本版本为全新格式，不读取旧需求卡、delivery、review receipt 或旧 CLI。历史文件只是仓库历史，不参与当前流程。
