---
name: ios
description: 中文 iOS 需求分析、实施、验证与显式交付工作流。用于 Objective-C、Swift、SwiftUI 和 App 发布动作。
---

# 工作流入口

本 Skill 仅维护原生 iOS 实现与平台规则，依赖项目内 `.agents/teamflow-core/` 的共用流程和工具。安装通过 `setup --mode ios`（iOS 原生）或 `setup --mode godot-ios`（Godot + iOS）选择入口；Godot 模式读取同级 `Godot/SKILL.md`。目录是否存在不改变已选模式。

PROJECT_ROOT 是当前 Git 根及其目录树；只使用本项目内的 Skill。处理空间外对象前，说明范围和操作并取得用户本次明确允许。开发工具使用官方或既有包管理器默认位置；需要管理员权限、密码、登录或系统确认时交给用户处理。

命令统一使用 `python3 scripts/teamflow.py`；尚未接入时运行 `python3 .agents/teamflow-core/scripts/teamflow.py setup --mode ios`。默认输出简短摘要，`--json` 输出完整结构。验证强度与截图范围按 WORKFLOW、PROJECT-CHECKS 与 UI 规范执行。

先读 [WORKFLOW](../../teamflow-core/references/WORKFLOW.md)，它是主流程、状态、授权原则、Bug 修复与流程改进的唯一规则来源。同会话已读且未变化时不重读。只加载本次相关专题：

| 当前工作 | 资料 |
| --- | --- |
| 构建、测试、命令参数与证据 | [CHECKS](../../teamflow-core/references/CHECKS.md) |
| Git 动作；账号、网络或敏感数据 | [BOUNDARIES](../../teamflow-core/references/BOUNDARIES.md) |
| App 外部动作（归档、TestFlight、审核、发布）的准备或执行 | [APP-RELEASE](references/APP-RELEASE.md) |
| 安装或接入诊断 | [INSTALL](../../teamflow-core/references/INSTALL.md) |
| 新 App 启动或生命周期变化 | [启动模板](references/templates/new-project.md)、[APP-LIFECYCLE](references/APP-LIFECYCLE.md) |
| 新工程日志组件 | [LOGGING](references/LOGGING.md) |
| 功能分析清单；复杂功能设计 | [功能清单](references/templates/feature.md) |
| 已有工程现状；大型模块索引 | [EXISTING-PROJECT](references/EXISTING-PROJECT.md)、[MODULE-CONTEXT](../../teamflow-core/references/MODULE-CONTEXT.md) |
| 业务代码、架构调整或数据迁移 | [ARCHITECTURE](references/ARCHITECTURE.md) |
| App 用户可见文本或多语言变更 | [LOCALIZATION](references/LOCALIZATION.md) |

修改业务代码时按实际语言读取 [OC](references/standards/objective-c.md)、[Swift](references/standards/swift.md)、[SwiftUI](references/standards/swiftui.md) 与 [UI](references/standards/ui.md) 规范，遵守 [中文注释规则](../../teamflow-core/references/standards/comments.md)。已有项目明确约定优先。
