---
name: ios-team-flow
description: 中文 iOS 需求分析、实施、验证与显式交付工作流。用于 Objective-C、Swift、SwiftUI 和 App 发布动作。
---

# iOS 工作流入口

PROJECT_ROOT 是当前 Git 根及其目录树；只使用本项目内的 Skill。处理空间外对象前，说明范围和操作并取得用户本次明确允许。开发工具使用官方或既有包管理器默认位置；需要管理员权限、密码、登录或系统确认时交给用户处理。

先读 [WORKFLOW](references/WORKFLOW.md)，它是主流程、状态和授权原则的唯一规则来源。同会话已读且未变化时不重读。只加载本次相关专题：

| 当前工作 | 资料 |
| --- | --- |
| 安装或接入诊断 | [INSTALL](references/INSTALL.md) |
| 工作流源码分发 | [RELEASE](references/RELEASE.md) |
| 新 App 启动 | [启动模板](references/templates/new-project.md) |
| 功能分析清单；复杂功能设计 | [功能清单](references/templates/feature.md) |
| 已有工程现状 | [EXISTING-PROJECT](references/EXISTING-PROJECT.md) |
| 已启用或明确需要大型模块索引 | [MODULE-CONTEXT](references/MODULE-CONTEXT.md) |
| 业务代码或架构调整 | [ARCHITECTURE](references/ARCHITECTURE.md) |
| Bug 修复 | [BUGFIX](references/BUGFIX.md) |
| 构建与测试 | [PROJECT-CHECKS](references/PROJECT-CHECKS.md) |
| App 用户可见文本或多语言变更 | [LOCALIZATION](references/LOCALIZATION.md) |
| Git 动作 | [GIT-ACTIONS](references/GIT-ACTIONS.md) |
| App 外部动作的准备或执行 | [APP-RELEASE](references/APP-RELEASE.md) |
| 新 App 或生命周期变化 | [APP-LIFECYCLE](references/APP-LIFECYCLE.md) |
| 新工程日志组件 | [LOGGING](references/LOGGING.md) |
| 已复现流程缺陷或明确工作方式纠正 | [EVOLUTION](references/EVOLUTION.md) |

修改业务代码时按实际语言读取 [OC](references/standards/objective-c.md)、[Swift](references/standards/swift.md)、[SwiftUI](references/standards/swiftui.md) 与 [UI](references/standards/ui.md) 规范，遵守 [中文注释规则](references/standards/comments.md)。已有项目明确约定优先。
