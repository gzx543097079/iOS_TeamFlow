---
name: ios-team-flow
description: 中文 iOS 团队需求实施与提交审查。用于已安装本 Skill 的项目中的 iOS 新需求、缺陷修复、Objective-C、Swift、SwiftUI 代码生成及提交前 review，维护需求状态和审查证据。
---

# 项目级 iOS 团队协作入口

SKILL_ROOT 是本文件所在目录；PROJECT_ROOT 是当前 Git 根（新目录为用户选定根）。只使用当前项目 .agents/skills/ios-team-flow，不引用个人或其他项目版本。产物写项目根，规则维护在 Skill。

读取 [WORKFLOW](references/WORKFLOW.md) 执行日常顺序、分工及记录归属；已读且未变化不重读。只加载本次需要的专题：

| 当前工作 | 资料 |
| --- | --- |
| 首次接入、明确升级或恢复 | [INSTALL](references/INSTALL.md) |
| 新产品启动草案 | [启动模板](references/templates/new-project.md) |
| 已有工程首次现状或相关变化 | [EXISTING-PROJECT](references/EXISTING-PROJECT.md) |
| 业务验证 | [PROJECT-CHECKS](references/PROJECT-CHECKS.md) |
| 验收绑定、状态/交付事实变化 | [DELIVERY](references/DELIVERY.md) |
| 提交前审查 | [REVIEW](references/REVIEW.md) |
| 团队验收、多轮问题复核 | [ACCEPTANCE](references/ACCEPTANCE.md) |
| Hook / PR 范围检查 | [GIT-CHECKS](references/GIT-CHECKS.md) |
| 业务 App 发布 | [APP-RELEASE](references/APP-RELEASE.md) |
| 工作流分发仓库发布 ZIP | [RELEASE](references/RELEASE.md) |

语言/UI 规范由 WORKFLOW 按改动路由。接入成功不等于 App 验证成功，提交授权不代替团队产品验收。用户本次明确范围与已有授权优先，不因阅读专题重复索要批准。
