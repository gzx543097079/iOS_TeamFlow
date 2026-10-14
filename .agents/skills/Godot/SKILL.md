---
name: godot
description: Godot 项目的场景、资源、GDScript、团队协作与游戏验收工作流，按需处理游戏的 iOS 导出、原生桥接和发布。不用于纯原生 iOS App。
---

# Godot 工作流扩展

适用于 Godot 4.x + GDScript，沿用已有工程的版本、语言和渲染器。C#、GDExtension 或自编译引擎按实际版本另行核实。

本扩展依赖项目内 `.agents/teamflow-core/` 共用核心；Godot + iOS 模式另依赖同级 `iOS` 的平台规则与原生插件规范。需求、状态、证据和交付见 [WORKFLOW](../../teamflow-core/references/WORKFLOW.md)。命令仍为 `python3 scripts/teamflow.py`。

AGENTS 入口写明不含 iOS 目标时为纯 Godot 模式：下表标注「iOS」的行不使用，项目内也不安装 iOS Skill。

PROJECT_ROOT 是当前 Git 根及其目录树。工程可在根目录或子目录；先定位实际 `project.godot`，区分 Git 根与游戏资源根。工具使用已有默认安装位置；处理项目外对象遵循核心的范围边界。

按本次实际工作选择资料；标注「iOS」的行只在 Godot + iOS 模式下新增原生能力或提出 App 外部目标时使用：

| 当前工作 | 资料 |
| --- | --- |
| 场景、资源、游戏 UI 或玩法组织 | [工程与玩法](references/ENGINE.md) |
| 编写或修改 GDScript | [GDScript](references/GDSCRIPT.md)；涉及场景交互时再读工程与玩法 |
| 引擎版本、多人改场景、合并冲突、导出预设与凭据 | [团队协作](references/TEAM.md) |
| 帧率、内存、加载时间、崩溃或泄漏 | [性能与稳定性](references/PERFORMANCE.md) |
| 编写测试或引入测试框架 | [测试脚本](references/TESTING.md) |
| 检查、测试与验收 | [Godot 验证](references/CHECKS.md)、[核心证据机制](../../teamflow-core/references/CHECKS.md)；命令参数再读 [COMMANDS](../../teamflow-core/references/COMMANDS.md) |
| iOS：导出、原生桥接或前后台行为 | [Godot 与 iOS](references/IOS.md) |
| Git 交付或敏感数据 | [共用边界](../../teamflow-core/references/BOUNDARIES.md) |
| PR、评审或 CI | [共用评审](../../teamflow-core/references/REVIEW.md) |
| 新增或升级插件、SDK | [依赖与工具链](../../teamflow-core/references/DEPENDENCIES.md)；引擎版本见团队协作 |
| iOS 以外平台的导出分发包、上传、提审或上线 | [游戏发布](references/RELEASE.md) |
| iOS：Archive、TestFlight、提审或发布 | [Godot 与 iOS](references/IOS.md)、[App 外部动作](../iOS/references/APP-RELEASE.md) |
| 大型工程模块定位 | [共用模块索引](../../teamflow-core/references/MODULE-CONTEXT.md)，关注路径包含场景、脚本、资源及横切配置 |

Godot + iOS 模式下，同级 iOS 目录只提供被引用的平台资料，其 SKILL.md 不属于本入口。原生插件按语言加载 [Swift](../iOS/references/standards/swift.md) 或 [OC](../iOS/references/standards/objective-c.md) 规范，原生 UI 再加载 UI 规范。原生界面与生命周期模板只用于原生代码。
