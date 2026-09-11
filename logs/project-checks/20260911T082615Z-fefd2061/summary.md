# iOS 测试工程执行证据

- 执行时间：2026-09-11 16:26 +08:00
- 入口：project_checks.py --project . run --profile ios-demo
- 工具链：Xcode 26.6 (17F113)
- 环境：iPhone 17 Pro 模拟器，iOS 26.5
- 结果：xcodebuild test 成功，退出码 0；3 个单测 + 1 个 UI 测试通过。
- 覆盖：价格周期模型、导航/事件、页面释放、启动/套餐展示/无 Tab/详情返回。
- 代码：本次未提交工作区；对应源码 SHA256 见 source-hashes.json。
- xcresult：本地 DerivedData/TeamFlowDemo/Logs/Test 下；不进入 Git。
- 局限：没有执行真实支付、系统权限、iOS14 设备或 OC/SwiftUI 场景。默认跳过超大字号；不是团队产品验收结论。
