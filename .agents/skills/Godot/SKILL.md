---
name: godot
description: Godot 项目的场景、资源、GDScript 与游戏验收工作流，按需处理游戏的 iOS 导出、原生桥接和发布。不用于纯原生 iOS App。
---

# Godot 工作流扩展

适用于 Godot 4.x + GDScript；已有工程的版本、语言和渲染器优先，不因本 Skill 自动迁移。C#、GDExtension 或自编译引擎涉及的能力按实际版本另行核实，不宣称已覆盖。

本扩展依赖项目内 `.agents/teamflow-core/` 共用核心，以及同级 `iOS` 的平台规则与原生插件规范。需求、状态、证据和交付使用唯一来源：[WORKFLOW](../../teamflow-core/references/WORKFLOW.md)。命令仍为 `python3 scripts/teamflow.py`；首次接入运行 `python3 .agents/teamflow-core/scripts/teamflow.py setup --mode godot-ios`。不创建第二套需求卡，不套用原生界面或生命周期模板。

同级 iOS 目录只提供下表引用的平台资料，不读取其 SKILL.md；读取规则见 WORKFLOW「按需读取」。

PROJECT_ROOT 是当前 Git 根及其目录树。工程可在根目录或子目录；先定位实际 `project.godot`，不得混淆 Git 根与游戏资源根。工具使用已有默认安装位置；处理项目外对象遵循核心的范围边界。

仅按本次实际工作选择资料：

| 当前工作 | 资料 |
| --- | --- |
| 场景、资源、游戏 UI 或玩法组织 | [工程与玩法](references/ENGINE.md) |
| 编写或修改 GDScript | [GDScript](references/GDSCRIPT.md)；涉及场景交互时再读工程与玩法 |
| 检查、测试、性能与验收 | [Godot 验证](references/CHECKS.md)、[核心证据机制](../../teamflow-core/references/CHECKS.md) |
| iOS 导出、原生桥接或前后台行为 | [Godot 与 iOS](references/IOS.md) |
| Git 交付或敏感数据 | [共用边界](../../teamflow-core/references/BOUNDARIES.md) |
| Archive、TestFlight、提审或发布 | [Godot 与 iOS](references/IOS.md)、[App 外部动作](../iOS/references/APP-RELEASE.md) |
| 大型工程模块定位 | [共用模块索引](../../teamflow-core/references/MODULE-CONTEXT.md)，关注路径包含场景、脚本、资源及横切配置 |

Swift／Objective-C 原生插件只加载相应[Swift](../iOS/references/standards/swift.md)／[OC](../iOS/references/standards/objective-c.md)规范；原生 UI 才加载原生 UI 规范。游戏界面和引擎入口按 Godot 规范处理，不将原生生命周期模板套到引擎生成工程。

普通游戏功能不预读 iOS 导出、桥接、App 发布或其他语言规范；实际新增原生能力或提出对应外部目标时，才使用上述相关行。
