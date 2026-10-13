# TeamFlow iOS 测试工程

这是源仓库的内部验证 App，使用 Swift + UIKit、最低 iOS 14、导航栈无 Tab Bar、系统颜色并跟随主题。展示中英文本地示例商城，不请求权限、不访问网络、不发起付款。它不属于新建业务产品，也不能直接用于上架。

## 运行

在仓库根目录执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/project_checks.py --project . run --profile ios-demo
```

ios-demo profile 同时执行 Debug 的单元/UI 测试和 Release 的单元测试；日志消息求值测试分别验证 Debug 执行、Release 不执行。源码通过项目内 TFLog 接入，五等级仅 Debug 输出，生产调用不含测试开关。

需要完整 Xcode 与可用的 iPhone 模拟器。脚本优先使用环境变量 DEVELOPER_DIR，未设置时使用 /Applications/Xcode.app；只影响当前进程，不切换全局开发目录。默认从最新可用 iOS runtime 选择 iPhone，避免复用与当前 Xcode 测试框架不兼容的旧模拟器；也可通过 TEAMFLOW_SIMULATOR_ID 指定设备 UDID。不可用、超时、构建或测试失败均返回非零结果。

首次在 examples/TeamFlowDemo 执行 `pod install`，随后打开 TeamFlowDemo.xcworkspace（包含 Pods）。已提交工程无需 XcodeGen 即可安装依赖并构建。修改 project.yml 后用 XcodeGen 2.46.0 重新生成：

```sh
xcodegen generate --spec examples/TeamFlowDemo/project.yml
pod install --project-directory=examples/TeamFlowDemo
```

在仓库根目录执行该命令。工程关闭代码签名用于模拟器；真机测试需另行配置团队与签名。

## 场景及工作流演练

| 测试 | 检查 |
| --- | --- |
| 商品与购物袋 | 分类与整数金额汇总、添加及逐件减少 |
| 事件与导航 | 点击记录一次事件，详情使用当前选中商品 |
| 页面释放 | 导航容器释放后页面无残留强引用 |
| UI 主路径 | 启动、分类、详情、加购/移除、设置/语言/主题、无 Tab Bar |

要演练完整开发流程，在当前仓库提出针对该 App 的明确小需求：例如“增加一件本地演示商品”，要求创建需求卡、运行 ios-demo、审查本次差异并关联证据。可在本地临时分支制造文案与模型不一致，再由 Agent 定位和修复；不要把故意失败代码合入正常分支。测试通过不会自动生成语义 review，也不等于团队验收。

实际构建日志和结果由 project_checks 写入根 logs/project-checks；xcresult 与产物位于忽略的 DerivedData。工程约定见 [项目现状](../../requirements/PROJECT-CONTEXT.md)。默认不测试超大字号。

当前测试不覆盖真实 StoreKit 商品、支付恢复、系统权限弹窗、OC/SwiftUI、中英文以外语言或全部辅助功能。页面释放断言只证明本场景，不代表 App 全面无内存泄漏。最低部署配置不等于已经在 iOS 14 设备运行。

本工程和根 scripts/test_demo.py、.agents/project-checks.json 仅随源码提供，均不进入通用工作流或独立 Skill ZIP，避免将示例 App 安装到业务项目。

设置入口位于首页右上角：语言支持跟随系统、English、简体中文，切换立即生效并保存；关于我们展示应用说明和构建版本。UI 测试使用独立偏好存储。

App 用户可见文本和无障碍文本均从中英文 `Localizable.strings` 读取。本地化键使用至少两段、按场景伸缩的点分语义路径；单元测试核对两种语言的键集合、键格式、空值和格式占位符一致性。

外观默认跟随系统，设置中也可选择浅色或暗黑模式；窗口立即切换，重启保留选择。

商城首页包含四个本地示例商品、全部/音频/日常分类、详情及演示购物袋。购物袋使用整数金额汇总，左滑每次减少一件，数量归零时移除商品行，仅在本次运行保存；没有真实库存、订单、支付或网络请求。商品插图使用系统符号，无远程图片依赖。主路径 UI 测试覆盖同一商品加入两件后逐件减少，并保留浅色商城、暗黑商城、设置、关于及详情截图。

启动采用 UIKit Scene 生命周期：project.yml 生成 Info.plist 中的单窗口 Scene 配置；SceneDelegate 使用 UIWindow(windowScene:) 组装导航与主题，AppDelegate 只处理进程启动。修改配置后重新运行 XcodeGen，并同时提交生成的 plist 与工程。

## Masonry 自动布局

通过 CocoaPods 接入官方 [Masonry](https://github.com/SnapKit/Masonry) 1.1.0，提交 Podfile 与 Podfile.lock，Pods 目录不入库。使用 CocoaPods 1.16.2 安装；版本由锁文件固定。工程生成后必须再次执行 pod install 恢复集成，构建和测试使用 TeamFlowDemo.xcworkspace。

桥接头向 Swift 暴露 Masonry；商城容器、横幅、商品卡片、详情和关于页使用 mas_makeConstraints。UILayoutGuide 桥接保留真实安全区域、滚动内容和视口对象；Stack View 内部排列与系统表格行由 UIKit 管理。

## MVVM 与模块组织

需求架构及实际职责映射见根 requirements/PROJECT-CONTEXT.md「已确认架构与实现映射」。Sources 按 Application、Features、Shared、Infrastructure 组织；Features 内分 Views 与 ViewModels。ViewModel 通过 Shared 协议使用存储和事件能力，不引用 UIKit 或具体页面。

控制器只负责渲染、布局、事件转发；DemoCoordinator 组装依赖并协调导航，Masonry 仍通过 CocoaPods 管理。语言/外观共用 ChoiceViewController，商城/详情/购物袋共用 ProductItem 格式化，布局共用 StoreStyle。同步操作后重新渲染快照，页面返回时刷新共享状态。

ViewModelTests 使用内存替身检查筛选、加购/逐件减少、设置共享状态、版本注入及 Coordinator 释放；DemoTests 和 UI 测试继续检查真实窗口、布局、语言与外观持久化、商城操作。
