# Demo 工程现状

- 对象：App/TeamFlowDemo，内部本地演练 App，不连接交易服务。
- 来源：App/TeamFlowDemo/README.md、project.yml、Sources、共享 Scheme；2026-09-14 核对。
- Swift + UIKit，iOS 14，导航栈无 Tab，系统语义颜色；XcodeGen 2.46.0 配置与 .xcodeproj 一起维护。
- 日志：Sources/Support/Logging/TFLogger.swift，Debug 全量，Release 不输出；自动布局通过 CocoaPods 接入 Masonry 1.1.0，Podfile.lock 固定版本；pod install 后打开 TeamFlowDemo.xcworkspace，桥接头供 Swift 使用。
- 验证入口：.agents/project-checks.json 的 ios-demo（Debug 单元/UI、Release 单元），scripts/test_demo.py 按实际可用模拟器执行。
- 默认语言、主题、商城增量按当前需求实施；当前 AC 与阶段结果只在各需求卡维护。

- Demo 入口为本地商城：Sources/DemoCatalog.swift 提供示例商品与内存购物袋，DemoPreferences.swift 管理语言与外观，Resources 提供英文/简体中文。无网络、库存、订单或支付服务。

- UIKit 启动：AppDelegate 处理进程启动；SceneDelegate 持有场景窗口与外观绑定。project.yml 生成显式 Info.plist，使用单窗口 Scene 配置。
