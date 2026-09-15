# Demo MVVM 验证

- 依据：requirements/PROJECT-CONTEXT.md 的已确认架构映射；源码位于 App/TeamFlowDemo/Sources。
- Application 组装一个场景内共享的购物袋、PreferencesStore 和事件协议，持有 Coordinator；控制器通过弱捕获的导航回调进入其他功能，Feature 不引用另一个 Feature 的内部类型。
- ViewModel 处理分类、展示格式、加购反馈、按 ID 移除及偏好选择；Models 保存业务数据；Infrastructure 实现存储/事件接口。控制器仅消费展示快照并转发操作，窗口主题绑定留在 Application。
- 实际复用：ProductItem 由 Store/Product/Bag 使用；ChoicePresenting 与 ChoiceViewController 由 Language/Appearance 使用；StoreStyle 由商城和详情使用。Shared 不引用 Feature/Infrastructure 类型。单 App Target 的职责边界不冒充编译期模块隔离。
- boundary-check.json 是有限静态依赖核对，需结合以上语义审查及行为证据，不能单独证明架构符合。
- 实际验证：logs/project-checks/20260915T075656Z-a3b86675/result.json；Debug 14 单元+3 UI，Release 14 单元通过。新增内存替身验证分类与非法索引、跨页面共享购物袋、稳定 ID 删除、偏好选择与设置刷新、版本注入、Coordinator/页面释放。
- 原 UI 回归覆盖商城分类/详情/加购/删除、语言切换与重启、外观选择与前后台恢复，原 Scene 窗口归属及多尺寸 Masonry 滚动布局测试通过。运行日志未发现约束冲突或旧 UIScene 生命周期警告。
- 截图取自本轮 iPhone 17 Pro 的 xcresult；抽查 shop-light.png、product-detail.png、about-chinese.png，无重叠和操作遮挡。shop-dark.png 保留为暗黑回归附件。未宣称所有设备、VoiceOver 或最低 iOS 实测；超大字号按既有默认范围不测试。
- 日志组件和 Masonry 版本没有改变；移动源码后 XcodeGen + pod install 成功，workspace 两配置构建通过。Release 消息不求值断言通过。页面释放断言仅证明所测生命周期，不代表全面无泄漏。
