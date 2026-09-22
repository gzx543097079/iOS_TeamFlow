# 代表性场景

| 请求 | 应执行 | 不应执行 |
| --- | --- | --- |
| “检查当前实现” | 只读分析 | 建卡、commit 或发布 |
| “修复登录错误” | 建卡、实施、验证、完成 | 自动 commit/push |
| “提交代码” | 暂存、最终核对、commit | push 或 PR |
| “发布当前 GitHub Release” | 验证、提交、推送、标签及 Release 的最小依赖链 | PR、App Store 发布 |
| “检查能否上传 TestFlight” | 只读准备 | Archive 或上传 |
| “上传 build 123 到 TestFlight” | 只上传指定 build | 分发、Beta Review、App 审核 |
| “上传 build 123 到 TestFlight，仅限内部测试” | 上传并启用 `testFlightInternalTestingOnly` | 外部测试或 App Store 使用该 build |
| “分发给内部测试员” | 分发到明确的内部测试组 | 倒推启用 TestFlight Internal Only |
| “提交 App Store 审核” | 提交指定版本/build | 审核通过后自动发布 |
| “归档、上传并分发内部测试” | 执行明确列出的三项 | Beta Review 或 App 审核 |

真实平台操作需要真实账号、目标和权限；工具测试不能冒充外部平台成功。
