# 业务 App 发布流程

适用于真实 iOS App。工作流自身 ZIP 发布见 [RELEASE](RELEASE.md)，GitHub Release 不能证明 App 已上线。以下为团队执行规程，Apple 官方链接核对日期：2026-09-11；每次发布重新核对上传工具链及平台要求，最低运行 iOS 14 不等于可以用旧 Xcode 上传。

先从 [发布记录模板](templates/app-release.md) 创建 requirements/releases/App-版本-build.md，绑定需求、commit、Bundle ID、Target、版本/build 与环境；复用项目既有发布流水线，不擅自迁移签名或账号。

| 阶段 | 工作及证据 | 完成条件 |
| --- | --- | --- |
| ⬜ 发布准备 | 明确负责人、渠道、地区、时间、发布方式，关联验收与阻塞问题 | 团队验收通过、发布范围已授权 |
| ⬜ 构建归档 | 确认 Release 配置、Team、签名、entitlements、所有扩展 Bundle ID；记录 Xcode/SDK、干净代码 SHA、archive 与摘要 | 实际 archive 成功且与验收代码匹配 |
| ⬜ 上传处理 | 用项目既有工具或 Xcode Organizer 验证并上传，记录上传日志和 App Store Connect build 标识 | 平台处理完成且 build 可选；上传退出成功不等于处理完成 |
| ⬜ TestFlight 验证 | 记录内部/外部测试渠道与实际安装 build，验证关键业务和升级路径 | 适用测试通过；外部测试所需 Beta App Review 按平台要求完成 |
| ⬜ 提交审核 | 核对所选 build、截图/多语言文案、隐私信息、年龄分级、出口合规、审核说明与可用演示方式 | 获授权后实际提交，保留平台状态 |
| ⬜ 发布与观察 | 按已确认手动/自动/分阶段方式发布，核对目标地区可用性和版本，观察崩溃/购买/服务指标 | 实际可用且适用观察项完成，记录来源与时间 |

阶段可按项目采用的渠道标不适用并说明理由，不能把未上传/未审核写通过。归档、TestFlight、等待审核、审核通过和商店可用分别记录。外部上传、邀请测试、提交审核与发布按用户已有授权范围执行；缺少授权时先完成可审阅准备，再请求具体动作的授权。

## 本次发布检查

- 订阅相关：核对商品 ID、周期、权益、地区本地化价格、试用资格与续费说明；App 展示、实际购买项及 App Store Connect 配置一致，执行购买、取消、恢复、到期/退款的适用路径。检查服务端权益与打点，不用本地 StoreKit 配置测试代替平台环境验证。
- 权限和隐私相关：实际功能、用途文案及多语言、权限拒绝路径、隐私申报/清单与使用的 SDK 保持一致，按本次范围和平台要求核对。
- 包体检查：生产服务地址与配置正确，没有调试开关、测试账号、假购买成功入口、敏感日志；签名私钥、API 密钥和完整用户数据不提交 Git。
- 测试范围按需求、风险与发布变更选择，检查实际 archive/install 构建；无明确要求不验证超大字号。仅静态 review 不证明无内存泄漏，相关生命周期变化使用适用运行证据。

## 失败、拒审与回退

构建/处理失败保留原因与实际状态；拒审关联问题编号、平台原文、修复提交和重提记录。任何重新构建或商品变更需判断受影响验收并重开，不能沿用不同 build 的整套通过结论。

发现线上故障按项目既有开关/服务回退方案止损，指定负责人和可验证触发阈值。App Store 已安装二进制不能靠回退 Git tag 降级；需要修复版本时走新的 build 与适用审核。分阶段发布暂停、下架等外部操作按明确授权执行，并记录用户影响。没有发布权限或真实 App 时保留待验证，不模拟上线成功。

## Apple 官方依据

- [Xcode 分发与归档](https://developer.apple.com/documentation/xcode/distributing-your-app-for-beta-testing-and-releases)：归档和分发入口。
- [上传构建](https://developer.apple.com/help/app-store-connect/manage-builds/upload-builds)：工具支持与平台处理。
- [TestFlight](https://developer.apple.com/help/app-store-connect/test-a-beta-version/testflight-overview/)：测试分发渠道。
- [提交 App](https://developer.apple.com/help/app-store-connect/manage-submissions-to-app-review/submit-an-app)：审核提交步骤。
- [App 与提交状态](https://developer.apple.com/help/app-store-connect/reference/app-information/app-and-submission-statuses)：记录实际平台状态。
