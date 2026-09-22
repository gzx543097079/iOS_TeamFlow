# Demo 工程现状

- 对象：App/TeamFlowDemo，内部本地演练 App，不连接交易服务。
- 来源：App/TeamFlowDemo/README.md、project.yml、Sources、共享 Scheme；2026-09-14 核对。
- Swift + UIKit，iOS 14，导航栈无 Tab，系统语义颜色；XcodeGen 2.46.0 配置与 .xcodeproj 一起维护。
- 日志：Sources/Shared/Logging/TFLogger.swift，Debug 全量，Release 不输出；自动布局通过 CocoaPods 接入 Masonry 1.1.0，Podfile.lock 固定版本；pod install 后打开 TeamFlowDemo.xcworkspace，桥接头供 Swift 使用。
- 验证入口：.agents/project-checks.json 的 ios-demo（Debug 单元/UI、Release 单元），scripts/test_demo.py 按实际可用模拟器执行。
- 大项目增量读取入口：`.agents/project-modules.json` 是可执行模块索引，当前以 `1f5a6d3abd3ad2424e43b0b0d18e367d44a0573e` 为基线登记 Application、Store、Product、Bag、Settings 五个模块。Shared、Infrastructure、Resources、project.yml、Podfile 与 Podfile.lock 作为跨模块路径，发生变化时工具要求扩大读取范围。`TeamFlowDemo.xcodeproj/project.pbxproj` 因当前存在用户未提交修改，尚未纳入索引；该文件变化仍需人工关注，待工作区干净后再补录基线。
- 默认语言、主题、商城增量按当前需求实施；当前 AC 与阶段结果只在各需求卡维护。

- Demo 入口为本地商城：Sources/Shared/Models/DemoCatalog.swift 提供示例商品与内存购物袋，Sources/Infrastructure/DemoPreferences.swift 管理语言与外观，Resources 提供英文/简体中文；用户可见及无障碍文本使用按语义层级伸缩的点分本地化键，两种语言的键集合与格式占位符由单元测试核对。无网络、库存、订单或支付服务。

- UIKit 启动：AppDelegate 处理进程启动；SceneDelegate 持有场景窗口与外观绑定。project.yml 生成显式 Info.plist，使用单窗口 Scene 配置。

## 已确认架构与实现映射

依据：用户要求 Demo 改为 MVVM，并明确按需求架构实现模块化与复用；本次范围见 REQ-20260915-074941506Z-ea88625b。

| 职责 | 实际路径（App/TeamFlowDemo/Sources 下） | 边界与复用 |
| --- | --- | --- |
| 场景、依赖与导航组装 | Application/SceneDelegate、DemoCoordinator、DemoAppearanceBinding | 场景持有 Coordinator；回调弱引用，统一共享购物袋/偏好；功能不引用其他功能 |
| 商城展示与筛选 | Features/Store/Views、ViewModels | 控制器只渲染/转发；VM 持有分类状态，返回时读取共享状态 |
| 商品详情与加购 | Features/Product/Views、ViewModels | VM 输出商品快照与反馈；View 负责布局和可访问性通知 |
| 购物袋列表与逐件减少 | Features/Bag/Views、ViewModels | VM 转换金额/数量，按稳定 ID 每次减少一件；Model 汇总整数金额并在数量归零时移除商品 |
| 设置、语言、外观、关于 | Features/Settings/Views、ViewModels | VM 更新 PreferencesStore，输出选择状态和文案；Application 注入版本信息 |
| 共用数据、协议与展示组件 | Shared/Models、Presentation、Views、Logging | 不依赖 Features/Infrastructure；ProductItem 被商城/详情/购物袋复用，ChoicePresenting/ChoiceViewController 被语言和外观共用 |
| 存储与事件实现 | Infrastructure/DemoPreferences、DemoEvents | 实现 Shared 协议，构造注入，不持有页面 |

更新方式：同步意图处理后拉取 ViewModel 最新快照渲染；商城/设置返回时在 viewWillAppear 重新渲染，购物袋实例全场景共享。外观服务通知由窗口绑定消费，绑定释放时移除监听。不额外引入响应式框架。

本 Demo 使用单一 App Target，以上是职责与接口边界，不宣称目录形成编译器模块隔离；没有独立发布需求，因此不拆空 Package。测试通过内存 PreferencesStore/事件替身独立验证 ViewModel，并回归真实 UI 与页面/Coordinator 释放。
