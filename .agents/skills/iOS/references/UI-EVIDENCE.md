# UI 画面取证

本专题是节流阀，不是新义务。依赖 [WORKFLOW 改动分级](../../../teamflow-core/references/WORKFLOW.md#改动分级)；子 Agent 交派须带「展示小改 / 须扩大」结论，或先读该节。

## 何时加载

仅当需要**可定位的画面证据**时加载：用户要截图、远程看不到模拟器/真机，或交接表需附截图路径。

小改动与视觉类 AC 默认由用户确认即人工证据（见 WORKFLOW）；改完并跑适用自动检查后 `--wait-user` 即可，**不强制**读本文件，也**不强制**截图。本文件不授权全面设计审计，也不授权为纯视觉自跑全量单测或全量 UI 测。

## 构建与安装

截图必须来自**当前代码**构建并安装的模拟器或真机 App；旧构建无效。不用浏览器或 Preview 代替定稿证据。调样式期间可用 Preview 或增量编译迭代；定稿后只构建安装一次。

- 同一代码已有 Debug 模拟器产物（如验证刚构建过）→ 只 `simctl install`，不重编。
- 需另行构建 → 同一 `-derivedDataPath` 增量构建，不 clean。
- 用启动参数或测试数据直达目标页；有内容状态与空状态分开准备，不靠逐步点导航。
- 模拟器未启动先启动；多模拟器用 UDID 代替 `booted`：

```sh
xcrun simctl install booted <DerivedData>/Build/Products/Debug-iphonesimulator/<App>.app
xcrun simctl launch booted <Bundle ID> <启动参数>
xcrun simctl bootstatus <UDID> -b
xcrun simctl io booted screenshot <路径>.png
xcrun simctl ui booted appearance dark              # 结束后恢复
xcrun simctl ui booted content_size extra-extra-extra-large
```

## 截图范围与轮次

- 只覆盖本次改动的关键页与必要状态；共享组件选代表页；不默认展开设备×主题×语言×字号组合。全面审计组合仅在用户明确要求评审/全面核对且加载 [UI-REVIEW](UI-REVIEW.md) 时使用。
- 一批改完再统一截；不改一处截一次。放临时目录或需求卡引用处；项目无截图基准则不提交。
- 交互、焦点、VoiceOver、恢复路径靠实际操作或 UI 测试；截图只证明画面。
- 注明模拟器或真机；手势、触感、性能、传感器需真机，未取得标未验证。
- 两轮未解决先查容器、层级、安全区或状态根因，禁止盲调边距反复构建。
