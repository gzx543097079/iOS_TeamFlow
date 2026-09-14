# iOS UI 规范（中文）

核对日期：2026-09-14。适用于 UIKit（OC / Swift）和 SwiftUI。
本规范是基于 Apple 官方资料编写的团队落地标准，不是 Apple 认证文件。区分“审核要求”“Apple 设计建议”“团队默认”；上线前再次核对目标地区、系统版本及最新官方规则。

## 1. 设计基线

- 【Apple 设计建议】优先系统导航、列表、表单、弹窗、菜单、分享和购买组件，遵循所在系统的交互及外观；尊重安全区域、键盘、手势返回和辅助功能。
- 【团队默认】先明确页面目标、主要动作和导航路径，再设计视觉。每页提供内容、加载、空、失败、权限不足等实际适用状态；失败提供重试或恢复入口。
- 【团队默认】先采用系统语义颜色、文字样式和组件默认尺寸。自定义间距可从 4/8/12/16/24/32 pt 取值，但这是项目约定，不是 Apple 强制栅格。设计变量集中管理，避免散落魔法数字。
- 【团队默认】不强制特定 iOS 最低版本；先读取工程部署目标。新系统材质（包括 Liquid Glass）优先用系统组件，使用新 API 时核对可用性并提供必要回退，不把新系统外观强加给旧系统。

## 2. 排版、颜色和适配

- 【Apple 设计建议】使用 Dynamic Type，优先 `.body`、`.headline` 等语义样式；UIKit 用 preferredFont 并启用字体缩放。重要信息在大字号下可换行、滚动，不能截掉价格、购买条件或主操作。
- 【Apple 设计建议】iOS 自定义文字参考默认 17 pt、最小 11 pt；它们不是所有标签必须使用的固定字号。团队避免用最小字号承载购买条件等关键信息。
- 【团队默认】正常正文采用至少 4.5:1 对比度，大字至少 3:1；以 Apple Accessibility 当前尺寸/字重分类及 Accessibility Inspector 实测为准。同时检查深色、浅色、增强对比度和透明背景。
- 【Apple 设计建议】状态同时用文字、图形或形状表达，不只用红绿区分；图片配适当替代说明，纯装饰图不制造朗读噪音。
- 【团队默认】触控热区至少 44×44 pt，图标可小于热区。Apple 当前可访问性文档区分 iOS 默认 44×44 pt 和最小 28×28 pt；本团队采用更宽松易点的 44 pt，不宣称它是所有场景的审核硬门槛。相邻热区避免重叠。
- 支持横竖屏和 iPad 的范围以需求确认结果为准；所支持设备必须验证安全区域、窗口尺寸变化、长文案、RTL 和键盘遮挡。不要用屏幕宽度推算所有布局。

## 默认兼容 RTL

【团队默认】所有新生成及本次修改的 UI 默认兼容 LTR 与 RTL，与是否启用阿拉伯语翻译分开处理。新项目仍可仅启用英语和简体中文；不为支持 RTL 自动添加 ar 资源、修改开发语言或强制整个 App 使用 RTL。已有工程保留配置，在本次修改范围内补齐方向适配。

- UIKit（OC/Swift）：约束优先 leadingAnchor/trailingAnchor，边距用 directionalLayoutMargins / NSDirectionalEdgeInsets，普通文字用 natural 对齐，视图默认继承 semanticContentAttribute。涉及手工布局、滑动手势、动画或自定义绘制时按 effectiveUserInterfaceLayoutDirection 判断；不能靠语言代码等于 ar 推断方向，也不能用全屏负缩放代替正确布局。
- SwiftUI：优先 .leading/.trailing 对齐和边距，让标准容器跟随 layoutDirection；自定义 Layout、偏移或手势通过 @Environment(\.layoutDirection) 判断方向。UIKit/SwiftUI 混合容器要核对方向传递，不能在桥接层硬编码 leftToRight。
- 导航返回/前进与阅读方向有关的图标采用语义方向资源，例如 backward/forward 系列；自定义资源仅在语义需要时镜像。不要重复镜像系统已适配的资源。照片、品牌标志、地图/物理方向和播放控制等按实际语义保持方向，不能把所有图片、顺序或数字统一翻转。
- 邮箱、URL、电话、编号与混合数字遵循内容的双向文本语义，必要时只在局部设置书写方向；不要手工倒序字符串或给整页强制 LTR。自定义富文本、横向列表、分页与手势分别核对阅读顺序，不能只看边距是否翻转。
- 接口命名、参数和中文注释明确 leading/trailing 与物理 left/right 的区别；确需固定方向的局部内容记录原因。正常生成代码中不加入全局 forceLeftToRight/forceRightToLeft 或固定 layoutDirection。

本次涉及 UI 的验证默认包含 LTR 和强制 RTL，即使 App 没有 ar 本地化也要检查。UIKit 在测试/调试容器设置 forceRightToLeft，SwiftUI 在预览或测试容器注入 .environment(\.layoutDirection, .rightToLeft)；强制配置限验证环境，不进入生产默认路径。只改 locale 不能作为布局方向已切换的证据，先确认实际方向再检查。

对本次页面检查导航/返回、内容起止对齐、图标语义、横向列表/分页/手势、混合数字及输入、截断和可点击区域；适用的 LTR/RTL 场景分别记录结果。预览用于早期核对，必要交互仍需运行验证。无工具时写未验证及缺项，不能因未启用阿拉伯语标 RTL 不适用；纯非 UI 改动才可按范围不适用。RTL 布局验证不等同于阿拉伯语翻译验收。

## 3. 操作与无障碍

- 按钮说明实际动作，破坏性操作说明后果；有可恢复设计时优先提供撤销。不要阻断系统返回手势或隐藏必要退出路径。
- VoiceOver 验证名称、值、特征、顺序和焦点；滑动等手势有可发现的等效控件。自定义组件支持辅助功能动作。
- 尊重减少动态效果、降低透明度和增强对比度；不要只用声音传达结果。加载期间避免重复提交，加载与失败必须可区分。
- 输入框提供标签、正确键盘类型、焦点切换、校验时机、错误原因；不以 placeholder 代替永久标签。

## 4. 订阅与付费 UI

- 【审核要求】购买前清晰说明获得的内容、订阅期限、价格和适用续订条件；试用说明时长和结束后的收费。不得制造虚假免费、倒计时或节省金额。以 App Review Guidelines 3.1.2 和官方订阅页面为依据。
- 【团队默认】购买按钮、选中套餐、产品 ID、周期、权益、展示价格、购买 API 参数必须来自同一个已验证产品模型。StoreKit 2 使用 `Product.displayPrice`；OC/StoreKit 1 使用产品价格及其 priceLocale 格式化。产品未加载成功时不能用占位价格发起购买。
- 年付折算月价只能作辅助说明，同时明确“按年收取的总金额”；币种、地区和舍入规则必须匹配。节省比例基于真实同币种可比价格计算。
- 首购优惠必须校验适用资格；无试用资格时更新 CTA 和说明。恢复购买、管理订阅、服务条款与隐私政策提供可访问入口；恢复中、取消、待批准、交易失败有独立反馈。
- 付款成功后只根据验证后的交易/权益状态解锁；关闭支付面板或点击按钮不等于成功。不能把 Sandbox 数据当线上价格证据。

## 5. UI 验收记录

对本次涉及页面记录设备/系统、语言、字号、主题、操作及结果；不涉及的维度注明原因。

【团队默认测试范围】无明确要求时不验证超大字号（辅助功能的更大字体档位）。只有用户明确要求或已确认需求/验收标准列入时才测试；普通字号与常规字号适配仍按本次改动验证。未要求的超大字号标“不适用：未明确要求，按默认测试范围跳过”，不阻塞完成或提交，不标为通过。本约定不改变 Dynamic Type 与现有字号适配的实现建议。

| 检查项 | 通过 / 失败 / 未验证 / 不适用 | 证据 |
| --- | --- | --- |
| 主路径及加载、空、错误状态 | | |
| 普通字号与常规字号适配 | | |
| 超大字号（仅明确要求时） | | 未明确要求时记录不适用及跳过原因 |
| 深浅色 / 对比度 | | |
| VoiceOver / 热区 / 减少动态效果 | | |
| 小屏 / 支持的 iPad / 键盘 / 长文案 | | |
| LTR / 强制 RTL（不依赖 ar 本地化） | | 实际方向、布局与适用交互证据 |
| 套餐、价格、周期、按钮与实际购买一致 | | |

## 官方来源

- [Apple：Get it right (to left)](https://developer.apple.com/videos/play/wwdc2022/10107/)
- [UIView semanticContentAttribute](https://developer.apple.com/documentation/uikit/uiview/semanticcontentattribute)
- [SwiftUI LayoutDirection](https://developer.apple.com/documentation/swiftui/layoutdirection)

- [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines)
- [Accessibility](https://developer.apple.com/design/human-interface-guidelines/accessibility)
- [Typography](https://developer.apple.com/design/human-interface-guidelines/typography)
- [In-app purchase](https://developer.apple.com/design/human-interface-guidelines/in-app-purchase)
- [自动续期订阅](https://developer.apple.com/app-store/subscriptions/)
- [审核指南 3.1.2](https://developer.apple.com/app-store/review/guidelines/#subscriptions)
- [Product.displayPrice](https://developer.apple.com/documentation/storekit/product/displayprice)

HIG 页面若仅显示 JavaScript 提示，可读取 Apple 自有 DocC 数据路径 `https://developer.apple.com/tutorials/data/design/human-interface-guidelines/<主题>.json`；本次已读取 accessibility、typography、in-app-purchase 的正文。
