# 新项目需求文档：〈项目名称〉

- 文档版本：v1
- 状态：待确认
- 产品负责人：待确认
- 技术负责人：待确认
- 更新日期：待填写

填写规则：Codex 根据团队输入先完成草案，未知项写“待确认”，不适用项注明原因。下面的默认值是团队起步建议，生成 PRD 时应填入并标“默认建议，待确认”；团队确认具体版本后才创建工程。不得将默认值、示例 ID、语言列表或占位信息当作已批准配置。

## 1. 项目身份与版本

| 配置项 | 填写值 / 默认建议 | 说明与确认要求 |
| --- | --- | --- |
| 项目名称（产品中文名） | 待填写 | 对外名称，与工程名分别记录 |
| 工程名称 / Product Name | 待填写，例如 MyApp | 建议稳定的英文名称，用于工程、Target 与 Scheme 命名 |
| App 显示名称 / Display Name | 待填写 | 桌面名称；可按语言本地化 |
| buildid / Bundle ID | 待确认；格式示例 `com.example.myapp` | 本模板把用户所称 buildid 暂解释为 Bundle ID，必须确认含义；示例不可直接用于正式项目 |
| App 版本 / MARKETING_VERSION | `1.0.0`（默认建议） | 对应 CFBundleShortVersionString，与工作流版本无关 |
| 构建号 / CURRENT_PROJECT_VERSION | `1`（默认建议） | 对应 CFBundleVersion；每次交付构建递增，不与 Bundle ID 混用 |
| CI Build ID | 待确认 / 不适用 | 若 buildid 指流水线任务 ID，记录在本行；说明与 App 构建号的映射 |
| 开发团队 / Team ID | 待确认 | 使用团队实际 Apple Developer 账号，不编造 ID |
| App Store Connect App ID / SKU | 待确认 / 上架准备时提供 | 分别记录 Apple 分配的数字 App ID 和团队 SKU，不能用 Bundle ID 代替 |
| 仓库 / 默认分支 / 代码负责人 | 待填写 | 使用项目根目录，不建立嵌套 Git 仓库 |
| 工程目录 | `App/`（默认建议） | 与 workflow/、requirements/、logs/、scripts/ 同级 |

确认 Bundle ID 所有者及唯一性，并与开发者后台、签名、App Store Connect 配置一致。若有 Widget、通知扩展等，逐个记录 Target 与独立 Bundle ID；不要把同一个 ID 用于不同 App/扩展。开发/测试环境是否需要独立 App ID 见第 6 节，不擅自增加。

## 2. 背景、目标与首版范围

- 需求材料：原始描述 / PRD / 设计稿 / 接口文档及版本：待填写。
- 目标用户、主要市场、使用场景和核心问题：待填写。
- 项目目标与可衡量成功指标：待填写。
- 首版必须交付 / 可后续交付 / 本期不做：待填写。
- 角色、权限、业务术语、竞品或参考流程：待填写。

## 3. 技术选型与项目架构

| 配置项 | 填写值 / 默认建议 | 选型约束 |
| --- | --- | --- |
| 主要开发语言 | Swift（默认建议） | 可选 Objective-C / Swift / 混编，记录比例或模块边界 |
| UI 框架 | UIKit（默认） | 采用 Swift + UIKit；项目明确要求时可调整为 SwiftUI / 混合 |
| 项目架构 | MVVM + 按功能组织（默认建议） | 可选 MVC / MVVM / TCA / Clean 等；按需求复杂度决定，不默认引入架构库 |
| 状态管理与依赖注入 | ViewModel 管理界面状态 + 构造注入（默认建议） | UIKit 视图负责展示与交互，明确状态更新方式和共享状态 owner；不默认引入 SwiftUI 状态模型 |
| 导航方案 | UINavigationController，按需使用 UITabBarController（默认建议） | 记录深链、登录拦截与路由恢复需求 |
| 最低 iOS / iPadOS | iOS 14.0；启用 iPad 支持时默认 iPadOS 14.0 | 按此部署目标选择 API 和依赖；更高版本 API 提供兼容处理，不自动提高最低系统版本 |
| Xcode / SDK / Swift 语言模式 | 待确认具体版本 | 本地与 CI 对齐；不写模糊“最新版”，部署目标和 SDK 分开记录 |
| 依赖管理 | Swift Package Manager（默认建议） | 既有 CocoaPods 等可保留；记录依赖、版本锁定及引入理由 |
| 工程生成方式 | Xcode 原生工程（默认建议） | XcodeGen / Tuist 等仅有明确需求再采用 |
| 模块边界 | Application / Features / Shared / Infrastructure / Resources（默认建议） | 详见第 3.1–3.5 节；按需建目录，不强制拆成多个 Target/Package |
| OC / Swift 桥接 | 无（默认建议） | 混编时明确桥接头、公开接口、空值及语言规范 |
| 网络层 / 本地存储 | 待确认 | 根据功能确定 URLSession、数据库等；不预装无用依赖 |

选型理由、已存在代码、必须复用模块及禁止引入的依赖：待填写。
生成代码默认采用 Swift + UIKit，最低支持 iOS 14.0；执行 Swift 与 `workflow/standards/ui.md` 规范。使用 OC 或 SwiftUI 的模块再加载对应规范。项目确需调整默认技术栈或提高最低系统版本时，写明原因并纳入需求确认，不能静默替换。

### 3.1 工程目录设计

依据 Apple 的 Xcode 文件/文件夹管理、Target 资源归属、本地 Swift Package 和构建配置机制组织工程。**Apple 没有规定统一的 MVVM 目录树；下面的名称、层次和依赖边界是本团队针对 Swift + UIKit、iOS 14 制定的默认设计。**

先根据确认的功能给出本项目实际目录树，再创建工程。以下 MyApp、FeatureName 是示意名称，必须替换；可选目录仅在有真实内容时创建，不生成空壳模块或没有用途的基础类。

```text
项目根目录/                         # Git 根目录
├── AGENTS.md
├── .agents/skills/ios-team-flow/     # 项目工作流 Skill
├── workflow/                       # 版本绑定；源仓库模式可保留规则
├── requirements/                   # PRD、需求卡、架构决定
├── logs/                           # 脱敏过程与验证记录
├── scripts/                        # 工程外的辅助脚本
└── App/                            # iOS 工程，和工作流/日志同级
    ├── MyApp.xcodeproj/
    ├── MyApp/                      # 主 App Target 源码
    │   ├── Application/
    │   │   ├── AppDelegate.swift
    │   │   ├── SceneDelegate.swift
    │   │   └── AppComposition.swift # 启动时组装依赖、设置根页面
    │   ├── Features/
    │   │   └── FeatureName/         # 每个功能独立组织
    │   │       ├── ViewControllers/
    │   │       ├── Views/          # UIView、Cell 等
    │   │       ├── ViewModels/
    │   │       ├── Models/         # 本功能的数据与状态
    │   │       └── Services/       # 本功能服务协议/业务协作，按需
    │   ├── Shared/                # 已有明确跨功能用途的代码
    │   │   ├── UI/                # 通用 UIKit 组件
    │   │   ├── DesignSystem/      # 颜色/字体/间距的统一接口
    │   │   └── Extensions/        # 范围清楚、可复用的扩展
    │   ├── Infrastructure/        # 外部系统访问，按需建立
    │   │   ├── Networking/
    │   │   ├── Persistence/
    │   │   ├── Permissions/
    │   │   └── Analytics/
    │   └── Resources/
    │       ├── Assets.xcassets
    │       ├── Localization/
    │       │   ├── Localizable.xcstrings
    │       │   └── InfoPlist.xcstrings
    │       ├── LaunchScreen.storyboard
    │       └── PrivacyInfo.xcprivacy # 依据实际 API/SDK 要求配置
    ├── Configurations/             # 不作为 App 普通资源打包
    │   ├── Base.xcconfig
    │   ├── Debug.xcconfig
    │   └── Release.xcconfig
    ├── MyAppTests/                  # 单元/集成测试 Target，按行为需求添加
    │   ├── Features/
    │   └── TestSupport/            # 测试替身、fixture，仅测试引用
    ├── MyAppUITests/                # UI 测试 Target，按需求添加
    ├── Extensions/                 # Widget/通知扩展等，仅需求明确时创建
    └── Packages/                   # 本地 Swift Package，可选
```

资源目录中的 String Catalog 是工具链支持时的默认示例；使用旧工具链或既有本地化方案时改为各语言 `.lproj/Localizable.strings`、`InfoPlist.strings` 和适用的 `.stringsdict`，不要同时维护两套相同 key。工程最低 iOS 14 与所选 Xcode 的文件组织功能分别确认。

### 3.2 各层职责与依赖边界

| 层 / 目录 | 负责内容 | 约束 |
| --- | --- | --- |
| Application | App/Scene 生命周期、依赖组装、根导航与启动协调 | 不堆积页面业务逻辑；只组装当前需要的能力 |
| Features / ViewControllers | UIKit 页面生命周期、事件转发、渲染绑定和导航调用 | 不直接实现网络请求、数据库操作或订阅权益判定 |
| Features / Views | 视图布局、组件样式、局部交互与无障碍 | 不依赖具体页面控制器，不主动访问外部服务 |
| Features / ViewModels | 界面状态、输入处理、调用业务服务与结果转换 | 不持有 UIViewController/UIView，不依赖页面生命周期回调细节 |
| Features / Models、Services | 功能数据、状态、服务协议与必要业务协调 | 简单功能可用少量文件，不机械创建 Repository/UseCase 层 |
| Shared | 已被多个功能使用的组件、样式和通用类型 | 不能反向依赖某个 Feature，不作为随意堆放代码的 Utils 目录 |
| Infrastructure | 网络、存储、系统权限与打点等外部访问实现 | 通过构造注入供功能使用，不持有页面；权限只实现确认清单中的能力 |
| Tests / TestSupport | 可验证行为、隔离外部依赖的测试替身 | Mock、fixture、调试捷径不进入生产 Target |

默认依赖方向：Application 组装 Features 与 Infrastructure；Features 使用自身或中立位置定义的服务协议；Infrastructure 提供具体实现。Shared 不依赖具体功能，功能间协作由明确的接口或上层导航协调。真正复杂的业务再引入领域层或独立 Package，避免循环依赖。

以上首先是代码职责约定：在单个 App Target 中，目录并不会形成 Swift 模块隔离。需要编译器强制依赖边界或独立复用/测试时，再拆 Target/Package；不要把多建文件夹当成已经模块化。

### 3.3 Xcode 文件与资源归属

- Xcode 导航器结构尽量与磁盘路径一致。确认团队 Xcode 版本后选择文件夹同步方式或与实际文件夹对应的 Group；不要为整齐只建大量虚拟分组，也不强制旧工具链使用不支持的工程格式。
- 创建、移动、重命名文件后核对引用、Target membership、Compile Sources 与 Copy Bundle Resources，避免重复编译、重复资源或文件存在但未参与构建。
- `.xcconfig` 按项目/Target 的 Build Configuration 明确绑定，检查最终生效设置；不勾入普通资源复制阶段。Debug/Release 与 Development/Staging/Production 映射遵循第 6 节。
- 若使用手工 Info.plist 或 `.entitlements`，建议放在 Configurations/ 或对应扩展目录，并通过实际构建设置指定。若由 Xcode 自动生成 Info.plist，则维护其有效设置，不再创建一份未使用的 Info.plist。
- 各 Target 独立确认 Bundle ID、权限用途说明、能力和资源；扩展不能自动继承主 App 的一切配置。隐私清单按实际归属打包，不能因它位于 Resources/ 就省略验证。
- App 资源、Package 资源和测试资源各归其所属 Target。图片/颜色优先 Asset Catalog；文案集中本地化管理，业务代码不写机器绝对路径。
- 提交 `.xcodeproj` 必要文件、共享 Scheme、依赖锁定记录及源资源；多人共享所需 Scheme 用共享配置。忽略 DerivedData、构建产物和 xcuserdata 等个人状态；不把项目工作流、requirements/、logs/ 当作 App 资源打包。
- 默认一个 App 工程即可；只有多个工程协作或现有工具确需 Workspace 时，才引入 `.xcworkspace`。不要额外建立空 Workspace 或嵌套 Git 仓库。

### 3.4 何时拆为本地 Swift Package

满足明确的独立复用、稳定边界、独立测试或维护需求时再拆，例如网络组件或通用业务能力。包仍保存在当前 Git 仓库的 App/Packages/，不因本地模块化创建新仓库。

```text
App/Packages/NetworkingKit/          # 示例，仅决定拆包后创建
├── Package.swift
├── Sources/
│   └── NetworkingKit/
│       ├── NetworkClient.swift
│       └── Resources/             # 仅有包资源时创建
└── Tests/
    └── NetworkingKitTests/
```

Package.swift 明确产品、Target、依赖和平台要求；iOS 支持范围与 App 的 iOS 14 目标兼容，不静默抬高要求。包含资源时按类型声明处理/复制规则；包内资源通过 `Bundle.module` 访问，不假定在主 App bundle 中。公开最小接口，App 添加产品依赖，禁止包反向依赖 App Target。OC 与 Swift 混编拆包时先核对所用工具链对 Target 的语言约束。

### 3.5 本项目结构确认表

| 决定项 | 本项目方案 | 依据 / 确认状态 |
| --- | --- | --- |
| 实际工程名称、目录树与功能目录 | 按首版功能填写 | 待确认 |
| UI 实现方式 | UIKit；纯代码布局或 Storyboard/XIB 选择待确认 | 与 Swift + UIKit、iOS 14 保持一致 |
| App / 扩展 / 测试 Target 清单 | 待填写 | 不需要的 Target 不创建 |
| 文件夹 / Group 策略 | 按团队 Xcode 版本填写 | 待确认 |
| 依赖方向、共享边界与服务注入 | 按上述职责结合功能填写 | 待确认 |
| 本地 Package / Workspace | 默认不额外创建 | 若需要，填写具体收益与维护人 |
| 配置、权限、资源和测试归属 | 按实际 Target 填写 | 待确认 |

生成工程后验证：磁盘路径与工程引用一致、代码编译进入正确 Target、实际包内资源可读取、权限本地化有效、测试资源未混入生产、构建设置符合 iOS 14，并在需求记录中填写证据。只生成上述目录树不代表已创建可运行工程。

## 4. 用户流程与功能

| 功能 ID | 场景与用户目标 | 输入与操作 | 结果及异常状态 | 优先级 | 验收条件 |
| --- | --- | --- | --- | --- | --- |
| F-001 | 待填写 | 待填写 | 待填写 | 待确认 | 可观察、可验证的行为 |

补充页面入口、返回路径、登录/游客、离线/弱网、空数据、重复操作、权限拒绝及删除账号等适用流程。

## 5. UI、设备与交互配置

| 配置项 | 填写值 / 默认建议 |
| --- | --- |
| 设计稿、品牌色、图标、字体与素材使用权 | 待提供，未提供时采用系统组件与语义样式 |
| UI 规范及项目特例 | 遵循工作流 UI 规范；特例填写理由 |
| 支持设备 | iPhone（默认建议）；iPad 是否支持待确认 |
| 屏幕方向 | iPhone 竖屏（默认建议）；视频等特殊页面单独说明 |
| iPad 多窗口 / 尺寸变化 | 待确认 / 不适用；若支持 iPad，补充其适配要求 |
| 深浅色模式 | 跟随系统，支持两种主题（默认建议） |
| Dynamic Type / VoiceOver / 减少动态效果 | 支持系统设置（默认建议），列出验收范围 |
| 页面状态 | 每页明确加载、空、成功、失败及权限不足等适用状态 |
| 键盘、长文案、RTL、触控区域 | 按 UI 与国际化规范验证，不靠固定尺寸隐藏问题 |
| App Icon / 启动界面 | 待提供；开发期占位与正式资产区分 |

## 6. 构建、环境与能力配置

| 配置项 | 填写值 / 默认建议 | 补充要求 |
| --- | --- | --- |
| 环境 | Development / Staging / Production（默认建议） | 不需要服务端时可简化，确认后创建实际配置 |
| Build Configuration | Debug / Release（默认建议） | 环境不等同编译优化配置，单独记录映射 |
| Target / Scheme / Bundle ID 映射 | 待确认 | 每种分发环境写明 Scheme、配置、服务地址引用及 App ID |
| 配置管理 | `.xcconfig` + 配置引用（默认建议） | 不把私钥、服务端秘密写入配置；客户端可读取的内容不视为秘密 |
| 签名方式 / Provisioning | 待确认 | 记录开发、测试和发布的签名负责人及 CI 获取方式 |
| Capabilities / Entitlements | 默认不额外启用；按需求确认 | 如 Push、Associated Domains、App Groups、iCloud、Sign in with Apple |
| 隐私权限与用途文案 | 按第 7 节首版权限清单确认 | 生成工程时落实配置、运行时请求和各语言提示 |
| URL Scheme / Universal Links | 待确认 / 不适用 | 域名归属、路由规则、关联配置及验证方式 |
| 后台任务 / 推送 / Widget / 通知扩展 | 待确认 / 不适用 | 说明必要性、Target、生命周期和权限 |
| 构建 / 单测 / UI 测试 / lint 命令 | 工程生成后填入实际可执行命令 | 生成前写待落实；不能把占位命令记作已验证 |
| CI 与工具版本 | 待确认；团队现有方案优先 | Xcode、依赖、签名、产物保留和分支检查规则 |
| 分发渠道 | TestFlight → App Store（默认建议） | 企业或其他渠道需另行明确，发布前获得授权 |

环境映射表：

| 环境 | Target / Scheme | Build Configuration | Bundle ID | API 配置引用 | 签名与分发 |
| --- | --- | --- | --- | --- | --- |
| Development | 待确认 | Debug（建议） | 待确认 | 待确认 / 不适用 | 待确认 |
| Staging | 待确认 | 待确认 | 待确认 | 待确认 / 不适用 | 待确认 |
| Production | 待确认 | Release（建议） | 待确认 | 待确认 / 不适用 | 待确认 |

## 7. 首版系统权限与提示文案

本节必须在创建工程前完成。Codex 根据第 4 节首版功能逐项判断需要哪些权限，填入“启用 / 不启用 / 待确认”及理由，提交团队确认；没有相关功能时默认不启用。不能把下面的候选项全部写进工程，也不能以“首版可能用到”为由申请权限。没有受保护资源访问的项目可以明确写“首版无额外系统权限”。

### 7.1 首版权限清单

| 权限候选 | 启用状态 / 对应功能 ID | 最小必要访问范围 | 工程配置参考 | 首次请求场景与拒绝处理 |
| --- | --- | --- | --- | --- |
| 相机 | 待判断 / F-xxx | 拍照、扫码等具体用途 | `NSCameraUsageDescription` | 用户选择拍照/扫码时请求；拒绝后提供实际可用的替代入口 |
| 麦克风 | 待判断 / F-xxx | 录音或带声音的视频 | `NSMicrophoneUsageDescription` | 用户开始录音时请求；禁止默默录音或循环弹窗 |
| 照片选择 | 待判断 / F-xxx | 用户主动选择的照片 | 优先 PhotosPicker / PHPicker；仅使用系统选择器通常无需申请整个照片库权限 | 取消选择视为正常取消，不当作权限拒绝 |
| 照片库读取 | 待判断 / F-xxx | 确需 PhotoKit 读取的资源 | `NSPhotoLibraryUsageDescription` | 使用读取功能时请求，处理 limited 部分授权，不能把部分授权当失败 |
| 保存到照片库 | 待判断 / F-xxx | 仅添加照片 | 适用时使用 add-only 与 `NSPhotoLibraryAddUsageDescription` | 用户保存结果时请求，拒绝后按需求提供分享/其他保存方案 |
| 使用期间定位 | 待判断 / F-xxx | 前台定位；精度按功能需要 | `NSLocationWhenInUseUsageDescription` | 用户使用附近/定位功能时请求；处理精度降低、单次许可和手动输入 |
| 始终定位 / 后台定位 | 待判断 / F-xxx | 仅确有持续定位需求 | 核对 `NSLocationAlwaysAndWhenInUseUsageDescription`、使用期间说明和必要的后台配置 | 独立解释后台用途，按当前系统规则请求/升级，不能默认跟随前台定位启用 |
| 通知 | 待判断 / F-xxx | alert / sound / badge 按实际需要选择 | `UNUserNotificationCenter` 请求；没有通用的通知 UsageDescription key | 用户开启提醒时请求；拒绝后保留 App 内功能。远程推送才另配 Push Notifications / APNs |
| 通讯录 | 待判断 / F-xxx | 明确需要的联系人访问范围 | 直接受保护访问核对 `NSContactsUsageDescription`；优先评估系统选择方式 | 用户导入联系人时请求；按系统版本处理有限访问与手动输入 |
| 蓝牙 | 待判断 / F-xxx | 连接指定外设 | `NSBluetoothAlwaysUsageDescription`；旧系统键及后台模式按部署目标另核对 | 配对/连接设备时触发；区分未授权、蓝牙关闭和无设备 |
| Face ID | 待判断 / F-xxx | 本地身份验证 | `NSFaceIDUsageDescription`；认证时提供符合实际用途的 localizedReason | 用户启用/使用生物认证时触发，处理无硬件、未录入、锁定与密码替代 |
| 本地网络 | 待判断 / F-xxx | 发现/连接局域网设备 | `NSLocalNetworkUsageDescription`；Bonjour 场景另核对服务声明 | 用户连接局域网设备时触发；普通互联网请求不因此默认添加本地网络权限 |
| 跨 App / 网站跟踪（ATT） | 待判断 / F-xxx | 确实符合跟踪定义的用途 | `NSUserTrackingUsageDescription` 与 ATT API，需核对真实 SDK 行为 | 只有实际需要跟踪才请求；拒绝后不得继续跟踪，不影响无关功能 |
| 其他：日历/提醒事项/健康/运动/语音识别等 | 待判断 / F-xxx | 按具体数据类型、读写范围填写 | 按最低系统版本查对应 API、UsageDescription 和能力配置，不复用其他权限的 key | 填写实际场景、拒绝/受限状态、替代方案；例如健康读取不能假设可获知用户是否拒绝 |

每个启用项另填写：适用 Target / 扩展、最低系统与 API、调用代码位置、配置位置、负责人及验收状态。记录第三方 SDK 引入的受保护资源访问；发现多余访问时移除对应代码/依赖，不能用虚构用途文案掩盖。

### 7.2 权限提示文案表

“权限提示词”指用户可见文案：区分系统弹窗用途说明、可选的 App 内前置解释，以及拒绝后的提示。系统弹窗的标题和按钮由系统控制，不承诺自行改写；通知等没有自定义用途字段的权限，相关解释写在 App 自己的界面中。

| 文案 ID | 权限与界面 | 系统 key / App 文案 key | 简体中文 | 英语 | 其他首发语言 | 状态 |
| --- | --- | --- | --- | --- | --- | --- |
| PERM-001 | 相机系统用途说明（示例） | `NSCameraUsageDescription` | 允许使用相机，以拍摄并设置你的个人头像。 | Allow camera access to take a photo for your profile picture. | 按确认的语言范围翻译 | 示例，需按实际功能改写 |
| PERM-002 | 仅保存图片用途说明（示例） | `NSPhotoLibraryAddUsageDescription` | 允许将你生成的图片保存到照片图库。 | Allow saving the images you create to your photo library. | 按确认的语言范围翻译 | 示例，需按实际功能改写 |
| PERM-003 | 通知 App 内说明（示例） | `permission.notifications.explanation` | 开启通知后，可以接收你设置的任务提醒。 | Enable notifications to receive the task reminders you set. | 按确认的语言范围翻译 | 示例，不是系统弹窗文案 |
| PERM-004 | 相机被拒绝后的 App 提示（示例） | `permission.camera.denied` | 相机访问已关闭。你可以前往设置开启，或选择已有照片。 | Camera access is off. You can enable it in Settings or choose an existing photo. | 按确认的语言范围翻译 | 只有确实提供选图替代时才使用 |

文案规则：

- 系统用途说明写清“访问什么 + 完成什么具体功能”，简洁、准确，不使用“为了更好的体验”“请授予必要权限”等空泛文案。
- 不添加未经证实的“绝不上传”“仅在本地使用”等承诺；每个权限、每个 Target 的用途与实际数据处理一致。
- 前置解释只在确实有帮助时展示，不仿冒系统授权弹窗，不以奖励或阻断无关功能强迫同意；允许用户继续或暂不启用。
- 拒绝后的引导说明影响，并提供“暂不 / 取消”和适用的“前往设置”或替代功能；仅由用户主动操作打开设置，不反复自动弹出。
- 所有已确认首发语言都有对应文案和审校状态。系统用途文案放入 `InfoPlist.xcstrings`（工具链支持时）或各语言 `InfoPlist.strings`；App 内说明放入普通文案资源。不能只翻译 App 内解释、遗漏系统用途说明。

### 7.3 生成项目时必须落实

1. 从团队确认的权限清单生成配置，仅处理“启用”项；“待确认”不自动加入工程。有缺项时继续独立工作，暂停依赖该权限的实现，不默认选全部。
2. 针对实际 Target 添加有效的 Info.plist / 构建设置用途说明，补齐所需 Capabilities、Entitlements、后台模式和后台服务关联。检查项目是否自动生成 Info.plist，避免改了未参与构建的文件。
3. 生成本地化权限文案资源并确认 Target membership。示例或占位内容不能作为正式用途说明；未审校的翻译明确记录。
4. 实现对应框架的状态检查、首次请求、授权后的业务动作、拒绝/受限/部分授权/硬件不可用的分支；不同权限状态不能机械套用同一枚举。仅写 Info.plist 不算完成权限接入。
5. 请求发生在相关功能的用户操作上下文，默认不在冷启动时集中索要全部权限；从设置返回时刷新状态，并处理系统中撤销权限的情况。
6. 工程配置只声明用途，不等于用户已经授权。使用 Apple 原生权限机制，不能绕过授权或自动同意系统弹窗。
7. 对相关路径执行验证并把结果写回需求卡：配置文件/代码/本地化资源位置、设备和系统版本、权限初始状态、操作与结果、截图或测试证据；无设备/工具时标未验证，不能声称授权流程已通过。

### 7.4 权限验收清单

- [ ] 首版每个启用权限均关联功能 ID、实际用途及团队确认；不启用项有简短理由。
- [ ] 实际构建产物中的用途 key、文案和能力声明匹配对应 Target，无缺失或空白说明。
- [ ] 未决定、已允许、已拒绝、受限及该权限适用的部分授权/硬件状态分别验证；拒绝不导致崩溃。
- [ ] 请求时机与 PRD 一致，不重复骚扰；设置返回、撤销权限、取消操作可正确恢复界面。
- [ ] 每个首发语言的系统用途文案与 App 提示正确，系统弹窗不能自定义的字段未伪装实现。
- [ ] 第三方 SDK 访问与清单一致，测试仅在测试设备/模拟器进行，不擅自重置个人设备权限。

## 8. 多语言与地区配置

默认建议以下 16 个语言/地区条目作为面向多地区 App 的首版候选。它们是本工作流为覆盖英语、中文、欧洲、东亚、东南亚及部分其他市场制定的默认组合，不是 Apple 要求或“所有 App 通用”的统计结论。生成 PRD 时默认勾选，团队可按市场、翻译与验收预算删减；未确认或未完成翻译不能宣称已经支持。

| 默认启用 | 语言 / 地区 | App 本地化标识 | 翻译与验收状态 |
| --- | --- | --- | --- |
| 是（待确认） | 英语 | `en` | 待翻译 / 待验收 |
| 是（待确认） | 简体中文 | `zh-Hans` | 待翻译 / 待验收 |
| 是（待确认） | 繁体中文 | `zh-Hant` | 待翻译 / 待验收 |
| 是（待确认） | 日语 | `ja` | 待翻译 / 待验收 |
| 是（待确认） | 韩语 | `ko` | 待翻译 / 待验收 |
| 是（待确认） | 德语 | `de` | 待翻译 / 待验收 |
| 是（待确认） | 法语 | `fr` | 待翻译 / 待验收 |
| 是（待确认） | 西班牙语 | `es` | 待翻译 / 待验收 |
| 是（待确认） | 意大利语 | `it` | 待翻译 / 待验收 |
| 是（待确认） | 葡萄牙语（巴西） | `pt-BR` | 待翻译 / 待验收 |
| 是（待确认） | 俄语 | `ru` | 待翻译 / 待验收 |
| 是（待确认） | 阿拉伯语（RTL） | `ar` | 待翻译 / 待验收 |
| 是（待确认） | 印地语 | `hi` | 待翻译 / 待验收 |
| 是（待确认） | 印度尼西亚语 | `id` | 待翻译 / 待验收 |
| 是（待确认） | 泰语 | `th` | 待翻译 / 待验收 |
| 是（待确认） | 越南语 | `vi` | 待翻译 / 待验收 |

- 基础开发语言：英语 `en`（默认建议）；需求文档、团队沟通仍用中文。
- 跟随系统/App 语言偏好选择支持语言；不支持的语言最终回退到开发语言英语，按系统匹配规则验证。App 内自建语言切换页默认不做，若需要则明确切换、生效和持久化方式。
- 文案资源：工具链支持时采用 String Catalog（`.xcstrings`）；已有 `.strings/.stringsdict` 方案可保留。复数、变量、拼接和语境注释统一管理，不直接拼接可翻译句子。
- 范围：页面文案、按钮、错误、空状态、无障碍标签、权限用途说明、适用的通知内容、订阅说明。文案含图的素材需替换或本地化。App 名称按品牌决策选择是否翻译。
- 语言和地区分离：日期、数字、单位、时区按系统/业务地区规则格式化；购买金额使用 StoreKit 产品本地化价格，不能由 UI 语言推导币种或售价。
- 支持阿拉伯语时验收 RTL 排版、导航、图标方向与混合数字；所有语言检查长文案、字体覆盖、大字号、复数及参数占位符。
- 翻译负责人 / 审校负责人 / 文案冻结日期 / 更新流程：待确认。AI 可提供初稿，订阅、权限与条款等关键文案需要指定人员审校。
- App Store 元数据语言与 App 内语言分别确认；商店语言标识不直接照抄本表。App Store 截图、描述、关键词、隐私与服务条款页面分别记录负责人、翻译范围和实际商店 locale。
- 发布验收：确认范围内的必要文案翻译完成，格式参数与复数正确；不能通过复制英文到全部语言来宣称完成。不满足时缩减正式语言范围需团队确认并记录。

## 9. 商业化与订阅（无订阅时明确不适用）

| 权益/套餐 | Product ID | 订阅组/等级 | 周期 | 目标 storefront | 预期价格来源 | 优惠/试用资格 | UI 文案/CTA |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 待确认 | 待确认 | 待确认 | 待确认 | 待确认 | App Store Connect / StoreKit | 待确认 | 各语言分别核对 |

- 实际展示价格由 StoreKit 产品决定；需求中的预期金额不是可硬编码的真实售价。
- 续订、升级降级、恢复、退款/撤销、宽限期、跨设备权益规则：待确认。
- 隐私政策、服务条款、管理订阅入口：待提供。
- 产品配置负责人、确认材料、Sandbox 与线上产品对应关系：待确认。

## 10. 数据、服务与隐私

- 登录方式、认证有效期、游客模式、退出与注销行为：待确认 / 不适用。
- API 契约、错误码、请求取消、超时、幂等与重试：待确认 / 不适用。
- 本地存储、缓存期限、同步与冲突策略、数据迁移：待确认 / 不适用。
- 敏感数据、Keychain 使用、日志脱敏、数据保留/删除及第三方 SDK：按实际需求列明。
- 适用的 Privacy Manifest、隐私标签与权限配置：根据实际 API / SDK 核对，不凭模板猜测采集行为。
- 只记录环境与凭据配置引用，不粘贴证书、token、私钥或真实用户数据。

## 11. 打点、质量与交付

| 事件 | 精确触发时机 | 必需参数/类型 | 去重键或规则 | 隐私处理 | 验收方式 |
| --- | --- | --- | --- | --- | --- |
| 待确认 / 不适用 | 待填写 | 待填写 | 待填写 | 待填写 | 待填写 |

- 崩溃/性能监控方案与负责人：待确认，不自动加入第三方 SDK。
- 启动、滚动、网络和内存预算及测量设备：待确认，填写可测量阈值。
- 测试框架、设备/系统矩阵、UI/语言/订阅测试与验收负责人：待确认；匹配实际工具链。
- 里程碑、依赖、发布渠道、灰度及回退方案：待确认。
- 风险、开放问题、解决条件及负责人：待填写。

## 12. 工程创建前确认与验收

- [ ] 项目名称、工程名称、显示名称、Bundle ID 含义与实际值已确认。
- [ ] UI 框架、主要语言、架构、最低系统与工具链已确认；默认建议已接受或调整。
- [ ] 首版功能、设备范围、默认 16 个语言条目的实际取舍已确认。
- [ ] 已根据首版功能确认实际目录树、层次职责、Target/资源归属与是否拆 Package；不是照抄示意目录。
- [ ] 环境/Target/签名/能力配置已确认，暂缺后台资料的事项有负责人、处理阶段与阻塞范围。
- [ ] 首版权限清单、用途文案、请求时机和拒绝处理已确认；创建工程后按第 7 节落实并验证。
- [ ] 原始需求与验收条件可追踪；未知订阅/认证/数据规则未被当作已确认。
- [ ] 团队对具体文档版本给出明确确认，再创建 App/ 工程。

工程生成后补齐实际 Target/Scheme/配置与构建命令并核验本节配置一致性；未跑通的检查记录“未验证”，不能提前勾选工程验收。尚未上架不必阻塞原型开发，但必须明确签名/商店等缺项何时补齐。

## 13. 团队确认记录

| 文档版本 | 确认范围 | 确认人 | 时间（含时区） | 原始确认内容/引用 | 结论 |
| --- | --- | --- | --- | --- | --- |
| v1 | 功能、工程配置、权限及提示文案、语言清单及待定项处理 | 待确认 | — | — | 待确认 |

确认后链接需求父卡和步骤。重大范围或基础配置调整时生成新文档版本，确认变化部分；保留此前确认和修改过程。

## 参考依据（模板维护用）

核对日期：2026-09-11。

- [Apple Bundle ID](https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleidentifier) 与 [构建版本](https://developer.apple.com/documentation/bundleresources/information-property-list/cfbundleversion)：标识和版本分开记录。
- [Apple 本地化](https://developer.apple.com/documentation/xcode/localization)：语言资源、地区格式、翻译与运行验证、商店资料分别处理。
- [Firefox iOS 语言覆盖示例](https://support.mozilla.org/en-US/kb/firefox-available-iphone-or-ipad-my-language)：参考其英语、中日韩与欧洲等语言覆盖；本模板加入阿拉伯语、印地语、泰语、越南语是团队面向更多市场的建议，并非该示例的支持清单或普遍性统计。

- [Apple 受保护资源访问](https://developer.apple.com/documentation/uikit/requesting-access-to-protected-resources) 与 [用途说明 key](https://developer.apple.com/documentation/bundleresources/protected-resources)：用途文案、本地化与 Target 配置。
- [Apple 照片隐私](https://developer.apple.com/documentation/photokit/delivering-an-enhanced-privacy-experience-in-your-photos-app)：系统选择器与有限照片访问。
- [Apple 通知授权](https://developer.apple.com/documentation/usernotifications/asking-permission-to-use-notifications)：结合实际功能请求并处理授权状态。

- [Apple Xcode 文件与文件夹管理](https://developer.apple.com/documentation/xcode/managing-files-and-folders-in-your-xcode-project)：导航器、文件夹与 Group 的关系。
- [Apple 本地 Package 组织](https://developer.apple.com/documentation/xcode/organizing-your-code-with-local-packages)：按复用与维护需求拆分代码。
- [Apple Package 资源](https://developer.apple.com/documentation/xcode/bundling-resources-with-a-swift-package)：资源的 Target 归属和 Bundle.module。
- [Apple 构建配置文件](https://developer.apple.com/documentation/xcode/adding-a-build-configuration-file-to-your-project)：.xcconfig 与构建配置绑定；上述 MVVM 目录命名是团队约定。
