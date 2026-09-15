# Masonry 接入验证

- CocoaPods 1.16.2 安装 Masonry 1.1.0 成功；Podfile.lock 与 Pods/Manifest.lock 一致，实际通过 workspace 构建。见 pod-install.log。
- ios-demo 结果：logs/project-checks/20260915T073047Z-d6a241c7/result.json；Debug 9 项单元 + 3 项 UI，Release 9 项单元全部通过。
- 新布局测试在 320×568、844×390、768×1024 容器检查实际滚动内容宽度、长文案滚动高度及无歧义约束；此项不是 iPad 设备实测。
- UI 回归覆盖分类、详情、加购/移除、语言切换与重启、外观切换、前后台及重启。截图抽查商城和中文关于页，无重叠；shop.png、about.png 来自本轮 xcresult。旋转附件存在截取异常，未将其作为完整视觉验收证据；横竖尺寸以布局测试和 UI 操作断言为准。
- 两配置运行日志未发现 Unable to simultaneously satisfy constraints 或 UIScene lifecycle will soon be required；页面释放、Scene 窗口和 Release 日志消息不求值测试通过。
- Masonry 上游 1.1.0 Pod Target 保留旧部署目标及编译警告，本轮未改写第三方源码；App 部署目标仍为 iOS 14，两配置实际编译运行通过。未宣称最低系统、全部设备、VoiceOver 或超大字号实测。
- 源仓库规程文档检查通过，见 workflow-docs.log；本次仅 Demo 及测试入口修改，不需要重复 115 项工作流工具测试。
