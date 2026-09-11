# 调研来源与选择理由

核对日期：2026-09-11。GitHub stars 是当日仓库 API 快照，仅作社区采用度信号，不等同质量评分；结合维护状态、官方文档、测试与落地成本评估。下列部分是完整 iOS 工程，部分是工具或规范，并非声称都是现成 Codex 工作流。本包基于这些实践独立编写中文流程，没有原样复制第三方实现。

| 项目 | Stars 快照 | 维护/类型 | 本次采用与限制 |
| --- | ---: | --- | --- |
| [Kickstarter iOS](https://github.com/kickstarter/ios-oss) | 8,671 | 未归档；真实 iOS 应用 | 采用可测试功能边界、本地化/无障碍/打点验证思路。仓库有 CircleCI、Fastlane、测试计划及 lint 配置；README 工具链说明偏旧，不照搬版本。 |
| [fastlane](https://github.com/fastlane/fastlane) | 42,097 | 未归档；移动构建/发布工具 | 借鉴构建、测试、发布分工与可重复命令；无 App 工程时不强塞 Ruby 或签名配置，有实际分发需求再接入。 |
| [SwiftLint](https://github.com/realm/SwiftLint) | 19,724 | 未归档；Swift 静态规范检查 | 采用自动检查思路，沿用项目配置，工具不能验证订阅映射或证明无泄漏。 |
| [Airbnb Swift](https://github.com/airbnb/swift) | 2,753 | 未归档；Swift 规范与格式工具 | 参考命名、可读性和规范自动化，团队格式选择与项目现有风格兼容，不强行整仓迁移。 |
| [Composable Architecture](https://github.com/pointfreeco/swift-composable-architecture) | 14,899 | 未归档；架构库及 CI | 借鉴状态/副作用可测、分层验证。TCA 依赖与学习成本较高，本流程不强制引入。 |
| [NYTimes OC](https://github.com/NYTimes/objective-c-style-guide) | 5,813 | 已归档；最后推送 2023-05-09 | 只借鉴稳定命名与结构约定，ARC/互操作以 Apple 文档和实际工具链为准。 |

结论：选择轻量的 Codex 入口 + 按需规范 + 可追踪需求 + 暂存改动审查 + 可重复发布。上述选择是本次适配判断，不是网络评分榜单。大型业务工程可继续使用现有 Fastlane/CI；不为了使用工作流增加 TCA、Ruby 或第三方运行依赖。

## 可复核的工程与 CI

- [Kickstarter 根目录](https://github.com/kickstarter/ios-oss)：存在 `.circleci/`、`.fastlane/`、`Makefile`、测试计划及格式配置；本次 GitHub API 查询 `.github/workflows` 返回 404，不将其描述为使用 GitHub Actions 的示例。
- [Fastlane CI](https://github.com/fastlane/fastlane/blob/master/.github/workflows/ci.yml)
- [TCA CI](https://github.com/pointfreeco/swift-composable-architecture/blob/main/.github/workflows/ci.yml)
- [SwiftFormat](https://github.com/nicklockwood/SwiftFormat)：作为格式工具候选；不与其他 formatter 重复处理同一文件。

## Codex 官方机制

- [AGENTS.md 自定义指令](https://learn.chatgpt.com/docs/agent-configuration/agents-md)：根到工作目录的发现与覆盖机制，入口保持精简。
- [Build skills](https://learn.chatgpt.com/docs/build-skills)：项目 `.agents/skills` 与 SKILL.md 的 name/description 元数据，按需读取详细规范。
- 官方机制只负责加载指令，不自动提供本包需求状态机、Git hook 或语义 review 证明；这些由流程和工具补充。

## Apple 与语言官方资料

- [HIG](https://developer.apple.com/design/human-interface-guidelines)；[Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility)；[Typography](https://developer.apple.com/design/human-interface-guidelines/typography)
- [购买界面](https://developer.apple.com/design/human-interface-guidelines/in-app-purchase)；[订阅](https://developer.apple.com/app-store/subscriptions/)；[审核指南](https://developer.apple.com/app-store/review/guidelines/#subscriptions)
- [Swift API Design](https://www.swift.org/documentation/api-design-guidelines/)；[SwiftUI 模型数据](https://developer.apple.com/documentation/swiftui/managing-model-data-in-your-app)
- [Objective-C 官方归档指南](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/ProgrammingWithObjectiveC/Introduction/Introduction.html)：基础语义参考，现代 SDK 可用性另查当前 API。
- [GitHub Release 事件](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#release)

## 更新规则

工作流升版时复核入口机制、部署目标相关 API、订阅与审核规则、依赖维护状态；在本文记录日期和变更。工具版本在消费项目中明确锁定；不把历史 stars 或参考工程工具链写成永久要求。
