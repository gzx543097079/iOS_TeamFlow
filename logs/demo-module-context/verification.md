# TeamFlowDemo 大项目增量模块验证

- 对象：`App/TeamFlowDemo`
- 工具：`.agents/skills/ios-team-flow/scripts/module_context.py`
- 索引：`.agents/project-modules.json`
- Git 基线：`1f5a6d3abd3ad2424e43b0b0d18e367d44a0573e`
- 索引 SHA-256：`f789bece98a39f7315c66eb43aa59296450ca23c86775bbee76168cc6cc34333`

## 验证矩阵

| 场景 | 输入 | 结果 |
| --- | --- | --- |
| 单模块路由 | `inspect --query '修改商城分类与商品卡片'` | 仅选择 `demo-store`；状态 `unchanged`；不扩大范围 |
| 多模块路由 | `inspect --query '购物袋移除后更新设置语言'` | 选择 `demo-bag`、`demo-settings`；均为 `unchanged`；不扩大范围 |
| 未知需求 | `inspect --query '新增完全未知的会员能力'` | 无模块匹配；报告 query 未匹配并设置 `expand_scope=true` |
| 模块内变化 | 在 Store 路径临时创建 `.teamflow-module-probe` | `demo-store` 报告 `untracked`，只建议读取该探针；`expand_scope=false` |
| 跨模块变化 | 在 Shared 路径临时创建 `.teamflow-cross-probe` | 报告跨模块 `untracked` 并设置 `expand_scope=true` |
| 脏路径保护 | 尝试把已有未提交改动的 `project.pbxproj` 录入 `demo-store` | 命令退出码 1；提示关注路径存在未提交变化；索引哈希未变化，无部分写入 |
| 最终完整校验 | `module_context.py validate` | 五个模块全部 `unchanged`，无 problem，`expand_scope=false` |

两个临时探针均在对应断言后删除；最终工作区中不存在探针文件。现有 `App/TeamFlowDemo/TeamFlowDemo.xcodeproj/project.pbxproj` 修改属于用户原有改动，验证未修改该文件。

工具回归执行 `python3 -m unittest -v tests.test_module_context tests.test_consumer_release.ConsumerReleaseTests.test_packaged_module_context_routes_without_reading_source_contents`，模块工具 6 项单测与安装包消费场景 1 项测试共 7 项全部通过。

## Demo 工程检查

执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/project_checks.py run --profile ios-demo
```

结果文件：`logs/project-checks/20260921T153900Z-43675c99/result.json`。检查记录 `source_unchanged=true`，但 `ios-demo` 与 `ios-demo-release` 均以退出码 65 失败。日志显示当前 Xcode 27 / iOS Simulator SDK 27 支持的部署目标下限为 iOS 15，而 TeamFlowDemo 为 iOS 14、Masonry Pods 为 iOS 6；因此构建在测试执行前被工具链拒绝。这是既有工程部署目标与当前 Xcode 的兼容问题，不是模块索引、路由或变更检测失败。本次验证未获授权修改部署版本。
