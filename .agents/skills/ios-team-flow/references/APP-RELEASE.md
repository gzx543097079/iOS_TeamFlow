# 显式 App 外部动作

本专题只在用户明确提出准备或执行某个 App 外部目标动作时加载。普通开发、需求完成、commit、push 或 GitHub Release 都不会触发本专题。目标动作依赖缺失的 Archive 或上传时可自动补齐最小必要前置，但不会继续执行目标之后的动作。

## 动作边界

| 用户表达 | 允许范围 |
| --- | --- |
| 检查/准备 TestFlight 或提审 | 只读核对并列出缺项，不 Archive、不上传、不提交 |
| Archive / 归档指定版本 | 生成并验证指定 Archive，不上传 |
| 上传 TestFlight | 上传指定 build，不自动分发测试员，也不启用 TestFlight Internal Only |
| 上传 TestFlight 并明确要求 Internal Only / 仅内部测试 | 上传指定 build，并将 `testFlightInternalTestingOnly` 设为 `true` |
| 分发 TestFlight | 将指定 build 分发到明确测试组 |
| 提交 Beta App Review | 只提交外部 TestFlight 测试审核 |
| 提交 App Store 审核 | 只提交指定版本和 build，不自动发布 |
| 发布 | 发布已审核的指定版本 |
| 开启或暂停分阶段发布 | 只执行明确的分阶段动作 |
| 下架 | 只处理明确 App 和地区的下架 |

用户可一次明确多个目标，例如“归档 build 123、上传 TestFlight 并分发给内部测试员”。如果只要求后面的目标，也可自动补齐确实缺失的必要前置；执行到目标即停止，不扩张到 Beta Review、App Store 审核或发布。前置所需目标 App、版本、build、账号或环境无法确定时先询问，不猜测。

`TestFlight Internal Only` 是可选上传参数，不是任何目标的必要前置，也不等于“分发给内部测试员”。启用后，该 build 不能用于外部 TestFlight 或 App Store。即使上传是目标或必要前置，只要没有另外明确要求 Internal Only，就必须省略 `testFlightInternalTestingOnly`，不能写成 `true`。

## 准备与记录

准备时直接读取实际工程、签名配置与平台状态，列出已核对事实和缺项，无需运行边界回显命令。TestFlight Internal Only 参数按上表处理。

实际动作使用项目既有 Xcode、CI 或发布工具。先核对目标 App、Bundle ID、版本、build、commit、环境、签名和账号；不得猜测目标。完成或失败后再记录真实证据：

```sh
python3 scripts/teamflow.py release record upload-testflight --version 1.2.0 --build 123 \
  --bundle-id com.example.app --environment production --commit <完整提交哈希> \
  --outcome succeeded --evidence "App Store Connect 已处理完成，构建可选"
```

记录生成到 `releases/com.example.app-production-1.2.0-123.md`，按 App、环境和构建汇集跨需求事件。命令必须明确 Bundle ID、环境、完整 commit 和结果；同一记录拒绝替换构建身份。结果区分 `failed`（失败）、`processing`（平台处理中）和 `succeeded`（本次动作已完成），不能将处理中记为可分发；后续平台处理完成再追加真实结果。记录命令不执行平台动作，也不验证证据真实性。只保存关键结果和可定位的平台或 CI 链接；已有记录足够时直接引用，不抄写长输出，也不预生成流水线。

重新构建会产生新的 build；旧 build 的安装、测试或审核结论不能自动沿用。审核通过不等于发布，上传成功不等于平台处理完成，GitHub Release 不等于 App Store 上线。
