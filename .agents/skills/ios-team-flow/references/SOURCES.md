# 参考资料

按当前任务选择相关资料。工作流基于通用实践独立编写；参考项目不构成强制依赖，也不规定消费项目的工具链版本。

## 工程实践

- [Kickstarter iOS](https://github.com/kickstarter/ios-oss)：功能边界与可测试性参考。
- [fastlane](https://github.com/fastlane/fastlane)：有实际构建或分发需求时参考，沿用项目现有 CI。
- [SwiftLint](https://github.com/realm/SwiftLint) 与 [Airbnb Swift](https://github.com/airbnb/swift)：命名、可读性和静态规范参考，不强制整仓迁移。
- [Composable Architecture](https://github.com/pointfreeco/swift-composable-architecture)：状态与副作用可测试性参考，不强制引入 TCA。
- [NYTimes OC](https://github.com/NYTimes/objective-c-style-guide)：稳定命名与结构参考，SDK 可用性以实际工具链为准。

## 官方资料

- [AGENTS.md 自定义指令](https://learn.chatgpt.com/docs/agent-configuration/agents-md)；[Build skills](https://learn.chatgpt.com/docs/build-skills)
- [HIG](https://developer.apple.com/design/human-interface-guidelines)；[Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility)；[Typography](https://developer.apple.com/design/human-interface-guidelines/typography)
- [购买界面](https://developer.apple.com/design/human-interface-guidelines/in-app-purchase)；[订阅](https://developer.apple.com/app-store/subscriptions/)；[审核指南](https://developer.apple.com/app-store/review/guidelines/#subscriptions)
- [Swift API Design](https://www.swift.org/documentation/swift-api-design-guidelines/)；[SwiftUI 模型数据](https://developer.apple.com/documentation/swiftui/managing-model-data-in-your-app)
- [Objective-C 指南](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/ProgrammingWithObjectiveC/Introduction/Introduction.html)
- [GitHub Release 事件](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#release)

## 使用与复核

仅在本次改动涉及入口机制、部署 API、订阅审核或依赖选择时，复核对应资料；单纯升版不触发全量调研。不维护 stars、旧 API 查询结果或参考工程的工具版本快照。实际使用的工具版本由消费项目锁定，影响实现的结论写入当前需求或工程约定。
