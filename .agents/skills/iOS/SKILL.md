---
name: ios
description: 原生 iOS App 的 Objective-C、Swift、SwiftUI 实现、测试与发布工作流。Godot 游戏、iOS 导出及其插件由 Godot 入口按专题引用，不触发本 Skill 的完整入口。
---

# 工作流入口

本 Skill 仅维护原生 iOS 实现与平台规则，依赖项目内 `.agents/teamflow-core/` 的共用流程和工具。安装入口由 AGENTS 中的模式决定，目录是否存在不改变已选模式。

PROJECT_ROOT 是当前 Git 根及其目录树；只使用本项目内的 Skill。处理空间外对象前，说明范围和操作并取得用户本次明确允许。开发工具使用官方或既有包管理器默认位置；需要管理员权限、密码、登录或系统确认时交给用户处理。

命令统一使用 `python3 scripts/teamflow.py`；尚未接入时运行 `python3 .agents/teamflow-core/scripts/teamflow.py setup --mode ios`。

流程、状态、授权与按需读取见 [WORKFLOW](../../teamflow-core/references/WORKFLOW.md)。按本次实际工作选择资料：

| 当前工作 | 资料 |
| --- | --- |
| 构建、测试与证据 | [CHECKS](../../teamflow-core/references/CHECKS.md)；命令参数再读 [COMMANDS](../../teamflow-core/references/COMMANDS.md) |
| 建立或编辑验证配置；迁移全量检查脚本或处理验证配置迁移提示 | [CHECKS-CONFIG](../../teamflow-core/references/CHECKS-CONFIG.md) |
| Git 动作；账号、网络或敏感数据 | [BOUNDARIES](../../teamflow-core/references/BOUNDARIES.md) |
| PR、评审或 CI | [REVIEW](../../teamflow-core/references/REVIEW.md) |
| 新增或升级依赖、SDK；锁定 Xcode 版本 | [DEPENDENCIES](../../teamflow-core/references/DEPENDENCIES.md) |
| App 外部动作（归档、TestFlight、审核、发布）的准备或执行 | [APP-RELEASE](references/APP-RELEASE.md) |
| 安装或接入诊断 | [INSTALL](../../teamflow-core/references/INSTALL.md) |
| 新 App 启动或生命周期变化 | [启动模板](references/templates/new-project.md)、[APP-LIFECYCLE](references/APP-LIFECYCLE.md) |
| 新工程日志组件 | [LOGGING](references/LOGGING.md) |
| 功能分析清单；复杂功能设计 | [功能清单](references/templates/feature.md) |
| 已有工程现状；大型模块索引 | [EXISTING-PROJECT](references/EXISTING-PROJECT.md)、[MODULE-CONTEXT](../../teamflow-core/references/MODULE-CONTEXT.md) |
| UI 评审、打磨或设计质量检查 | [UI 评审与打磨](references/UI-REVIEW.md) |
| 性能指标、启动、滚动、内存、崩溃或卡死 | [性能与稳定性](references/PERFORMANCE.md) |
| 架构调整、跨模块接口或数据迁移 | [共用架构](../../teamflow-core/references/ARCHITECTURE.md) + [iOS 补充](references/ARCHITECTURE.md)，同时读取；局部业务代码改动只按下方实际语言与涉及的专题加载 |
| App 用户可见文本或多语言变更 | [共用本地化](../../teamflow-core/references/LOCALIZATION.md) + [iOS 补充](references/LOCALIZATION.md)，同时读取 |

修改业务代码时只加载实际语言对应的 [OC](references/standards/objective-c.md)、[Swift](references/standards/swift.md) 或 [SwiftUI](references/standards/swiftui.md) 规范，SwiftUI 同时加载 Swift 规范；涉及 UI 时再加载 [UI](references/standards/ui.md)，改输入时加 [键盘与输入](references/standards/ui-keyboard.md)，购买或订阅页面加 [付费 UI](references/standards/ui-paywall.md)；新增或修改注释时参考[中文注释规则](../../teamflow-core/references/standards/comments.md)。已有项目明确约定优先。
