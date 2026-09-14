# TeamFlow iOS 测试工程

这是源仓库的内部验证 App，使用 Swift + UIKit、最低 iOS 14、导航栈无 Tab Bar、系统颜色并跟随主题。展示中英文本地示例商城，不请求权限、不访问网络、不发起付款。它不属于新建业务产品，也不能直接用于上架。

## 运行

在仓库根目录执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/project_checks.py --project . run --profile ios-demo
```

ios-demo profile 同时执行 Debug 的单元/UI 测试和 Release 的单元测试；日志消息求值测试分别验证 Debug 执行、Release 不执行。源码通过项目内 TFLog 接入，五等级仅 Debug 输出，生产调用不含测试开关。

需要完整 Xcode 与可用的 iPhone 模拟器。脚本优先使用环境变量 DEVELOPER_DIR，未设置时使用 /Applications/Xcode.app；只影响当前进程，不切换全局开发目录。自动选可用已启动 iPhone，也可通过 TEAMFLOW_SIMULATOR_ID 指定设备 UDID。不可用、超时、构建或测试失败均返回非零结果。

已提交的 TeamFlowDemo.xcodeproj 与共享 Scheme 可直接由 Xcode 打开，无需 XcodeGen。修改 project.yml 后用 XcodeGen 2.46.0 重新生成：

```sh
xcodegen generate --spec App/TeamFlowDemo/project.yml
```

在仓库根目录执行该命令。工程关闭代码签名用于模拟器；真机测试需另行配置团队与签名。

## 场景及工作流演练

| 测试 | 检查 |
| --- | --- |
| 商品与购物袋 | 分类与整数金额汇总、添加及移除 |
| 事件与导航 | 点击记录一次事件，详情使用当前选中商品 |
| 页面释放 | 导航容器释放后页面无残留强引用 |
| UI 主路径 | 启动、分类、详情、加购/移除、设置/语言/主题、无 Tab Bar |

要演练完整开发流程，在当前仓库提出针对该 App 的明确小需求：例如“增加一件本地演示商品”，要求创建需求卡、运行 ios-demo、审查本次差异并关联证据。可在本地临时分支制造文案与模型不一致，再由 Codex 定位和修复；不要把故意失败代码合入正常分支。测试通过不会自动生成语义 review，也不等于团队验收。

实际构建日志和结果由 project_checks 写入根 logs/project-checks；xcresult 与产物位于忽略的 DerivedData。需求记录见根 requirements/REQ-20260911-017.md。默认不测试超大字号。

当前测试不覆盖真实 StoreKit 商品、支付恢复、系统权限弹窗、OC/SwiftUI、中英文以外语言或全部辅助功能。页面释放断言只证明本场景，不代表 App 全面无内存泄漏。最低部署配置不等于已经在 iOS 14 设备运行。

本工程和根 scripts/test_demo.py、.agents/project-checks.json 仅随源码提供，均不进入通用工作流或独立 Skill ZIP，避免将示例 App 安装到业务项目。

设置入口位于首页右上角：语言支持跟随系统、English、简体中文，切换立即生效并保存；关于我们展示应用说明和构建版本。UI 测试使用独立偏好存储。

外观默认跟随系统，设置中也可选择浅色或暗黑模式；窗口立即切换，重启保留选择。

商城首页包含四个本地示例商品、全部/音频/日常分类、详情及演示购物袋。购物袋使用整数金额汇总，左滑移除，仅在本次运行保存；没有真实库存、订单、支付或网络请求。商品插图使用系统符号，无远程图片依赖。主路径 UI 测试保留浅色商城、暗黑商城、设置、关于及详情截图。
