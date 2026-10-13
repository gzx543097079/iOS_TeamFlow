# Demo 工程现状

- 对象：examples/TeamFlowDemo，内部本地演练 App，不连接交易服务。
- 来源：examples/TeamFlowDemo/README.md、project.yml、Sources、共享 Scheme；2026-09-14 核对。
- Swift + UIKit，iOS 14，导航栈无 Tab，系统语义颜色；XcodeGen 2.46.0 配置与 .xcodeproj 一起维护。
- 日志：Sources/Shared/Logging/TFLogger.swift，Debug 全量，Release 不输出；自动布局通过 CocoaPods 接入 Masonry 1.1.0，Podfile.lock 固定版本；pod install 后打开 TeamFlowDemo.xcworkspace，桥接头供 Swift 使用。
- 验证入口：.agents/project-checks.json 的 ios-demo（Debug 单元/UI、Release 单元），scripts/test_demo.py 按实际可用模拟器执行。
- 大项目增量读取入口：[模块索引](../.agents/project-modules.json)，定位和维护方式见 [MODULE-CONTEXT](../.agents/skills/ios-team-flow/references/MODULE-CONTEXT.md)。
- 默认语言、主题、商城增量按当前需求实施；当前 AC 与阶段结果只在各需求卡维护。

- Demo 入口为本地商城：Sources/Shared/Models/DemoCatalog.swift 提供示例商品与内存购物袋，Sources/Infrastructure/DemoPreferences.swift 管理语言与外观，Resources 提供英文/简体中文；用户可见及无障碍文本使用按语义层级伸缩的点分本地化键，两种语言的键集合与格式占位符由单元测试核对。无网络、库存、订单或支付服务。

- UIKit 启动：AppDelegate 处理进程启动；SceneDelegate 持有场景窗口与外观绑定。project.yml 生成显式 Info.plist，使用单窗口 Scene 配置。

## 架构约定

Demo 按已确认的 MVVM 架构实现模块化与复用。模块职责、入口与依赖统一查阅上方模块索引。

控制器负责渲染和事件转发，ViewModel 管理展示状态；依赖与导航由应用层组装，功能不直接引用其他功能。同步意图处理后读取最新快照；商城和设置返回时刷新。购物袋实例在场景内共享，外观通知由窗口绑定消费，释放时移除监听。不额外引入响应式框架。

业务约定：购物袋按稳定商品 ID 逐件减少，数量归零时移除；Model 使用整数金额汇总。偏好与事件实现通过协议注入；共用层不依赖功能或基础设施层，页面回调弱引用。

本 Demo 使用单一 App Target，目录表示职责边界，不形成编译器模块隔离；无独立发布需求时不拆空 Package。测试通过内存偏好存储和事件替身验证 ViewModel，并回归真实 UI 与对象释放。
