# App 发布动作：版本 / build

此文件只在用户明确要求某个 App 外部动作后创建。不要预生成全部阶段或把未授权动作写成待执行计划。

- App / Bundle ID：待填写
- 版本 / build：待填写
- commit：待填写

## 已执行动作

每次只追加用户明确授权且已实际执行的动作：时间、动作、对象、结果和证据。Archive、TestFlight 上传、测试分发、Beta App Review、App Store 审核、发布、分阶段发布及下架互不授权。

TestFlight Internal Only 需要单独明确授权。普通 TestFlight 上传默认省略 `testFlightInternalTestingOnly`；不能根据“内部测试员”或“内部测试组”自行推断启用。
