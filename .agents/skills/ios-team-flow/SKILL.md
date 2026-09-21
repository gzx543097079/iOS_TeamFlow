---
name: ios-team-flow
description: 中文 iOS 团队需求实施与提交审查。用于已安装本 Skill 的项目中的 iOS 新需求、缺陷修复、Objective-C、Swift、SwiftUI 代码生成及提交前 review，维护需求状态和审查证据。
---

# 项目级 iOS 团队协作入口

SKILL_ROOT 是本文件所在目录；PROJECT_ROOT 是接入时确定的当前 Git 根（新目录为用户选定根），它及子目录是本工作流默认允许的项目空间。只使用当前项目 .agents/skills/ios-team-flow，不引用个人或其他项目版本。产物写项目根，规则维护在 Skill。

将 PROJECT_ROOT 外的文件、目录或其他项目作为本次工作的读取、搜索、写入、删除或执行对象前，先说明准确对象、原因和拟执行操作，取得用户本次明确允许；不把 Codex 可访问范围、符号链接、工具可用性、沉默或无关的历史授权当作允许。项目内命令正常使用系统工具链、SDK 和缓存不算扩大工作对象；提交、推送、发布及其他外部写操作仍遵守各自授权规则。

完成已授权项目任务确实需要安装尚缺失的开发工具时，使用官方安装方式或项目既有包管理器的标准默认位置；该安装不因目录位于 PROJECT_ROOT 外而另行请求项目空间授权，不自行改到项目内、临时目录或自定义前缀。因管理员权限、密码或登录交互、系统策略、网络、包管理器缺失或平台兼容性而无法直接安装到默认位置时，停止安装，说明工具用途、默认位置、原因和解决方案，并给出按当前环境可直接执行的安装命令与验证命令；不擅自执行 `sudo`、代替用户输入凭据或改用非默认位置。

读取 [WORKFLOW](references/WORKFLOW.md) 执行日常顺序、分工及记录归属；已读且未变化不重读。只加载本次需要的专题：

| 当前工作 | 资料 |
| --- | --- |
| 首次接入、明确升级或恢复 | [INSTALL](references/INSTALL.md) |
| 新产品启动草案 | [启动模板](references/templates/new-project.md) |
| 已有工程首次现状或相关变化 | [EXISTING-PROJECT](references/EXISTING-PROJECT.md) |
| 大型项目模块路由与增量读取 | [MODULE-CONTEXT](references/MODULE-CONTEXT.md) |
| 实际失败、返工或明确纠正触发的流程改进 | [自我进化](references/EVOLUTION.md) |
| 业务代码生成、模块扩展或架构重构 | [架构一致性](references/ARCHITECTURE.md) |
| 生成或修改业务代码的注释 | [中文注释](references/standards/comments.md) |
| 新工程生成或业务日志接入 | [分级日志组件](references/LOGGING.md) |
| Bug 修复、复现与处理历史 | [缺陷处理](references/BUGFIX.md) |
| 新 App 生成或启动生命周期修改 | [Scene 生命周期](references/APP-LIFECYCLE.md) |
| 业务验证 | [PROJECT-CHECKS](references/PROJECT-CHECKS.md) |
| 验收绑定、状态/交付事实变化 | [DELIVERY](references/DELIVERY.md) |
| 提交前审查 | [REVIEW](references/REVIEW.md) |
| 团队验收、多轮问题复核 | [ACCEPTANCE](references/ACCEPTANCE.md) |
| 可选本地提交 Hook | [GIT-CHECKS](references/GIT-CHECKS.md) |
| 业务 App 发布 | [APP-RELEASE](references/APP-RELEASE.md) |
| 工作流分发仓库发布 ZIP | [RELEASE](references/RELEASE.md) |

语言/UI 规范由 WORKFLOW 按改动路由。接入成功不等于 App 验证成功，提交授权不代替团队产品验收。用户本次明确范围与已有授权优先，不因阅读专题重复索要批准。
