# iOS TeamFlow 中文工作流

可放入项目 Git 根目录的 Codex 团队工作流，支持 OC、Swift、SwiftUI，先定义 UI 基线，再完成需求追踪、代码生成、改动审查与版本分发。

## 使用入口

首次接入、空目录创建、团队共享和升级恢复统一见 [安装说明](INSTALL.md)。本 Skill 必须完整安装在项目 `.agents/skills/ios-team-flow/` 并完成接入，然后在 Codex 的项目会话直接提需求；不使用个人级安装。

版本见 [VERSION](VERSION)，源码后续新增能力见 [版本记录](CHANGELOG.md)。已发布 ZIP 只包含其标签提交的内容，不能将新文档中的功能推断为旧附件已有。

## 内容导航

| 内容 | 入口 |
| --- | --- |
| 新工程自动接入分级日志 | [日志组件](LOGGING.md) |
| 生成代码的中文注释 | [注释规范](standards/comments.md) |
| UI 标准（Apple 来源与团队约定） | [UI 规范](standards/ui.md) |
| 需求处理、拆分与状态 | [工作流](WORKFLOW.md) |
| Objective-C / Swift / SwiftUI | [OC](standards/objective-c.md) · [Swift](standards/swift.md) · [SwiftUI](standards/swiftui.md) |
| 业务构建与测试入口 | [配置与执行](PROJECT-CHECKS.md) |
| 需求与交付状态 | [交付追踪](DELIVERY.md) |
| 可选本地提交 Hook | [Git 检查](GIT-CHECKS.md) |
| 提交审查及去重 | [Review](REVIEW.md) |
| 已有项目增量开发 | [处理流程](EXISTING-PROJECT.md) · [模块增量工具](MODULE-CONTEXT.md) · [项目现状模板](templates/project-context.md) |
| 新项目 PRD 与需求卡 | [PRD 模板](templates/new-project.md) · [需求模板](templates/requirement.md) |
| GitHub 对比与官方来源 | [调研记录](SOURCES.md) |
| 团队验收与问题复核 | [验收规程](ACCEPTANCE.md) · [记录模板](templates/acceptance.md) |
| App 发布 | [发布流程](APP-RELEASE.md) · [发布记录](templates/app-release.md) |
| 实际问题驱动的自我进化 | [触发、验证与回退](EVOLUTION.md) |
| 业务场景试运行 | [验证矩阵](SCENARIOS.md) |
| ZIP 与 GitHub Release | [发布规程](RELEASE.md) |

## 自动化边界

Codex 负责语义审查，脚本核验记录与指纹；Hook 不调用 AI，也不自动发现价格错误。项目构建需实际配置，团队确认需真实回复，GitHub Release 与商店上线分别核验。提交、推送和发布按用户已授权范围执行。

目录中 references 是通用规则，业务工程、requirements、logs 和项目 scripts 写在项目根目录。独立 Skill 包不携带源仓库测试或工作流发布流水线；本地 Hook 需在每个克隆中显式安装。未明确要求不验证超大字号。
