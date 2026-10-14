# Godot 测试脚本

新建或扩充测试、引入测试框架时加载；检查入口与证据见 [Godot 验证](CHECKS.md)。

没有既有测试框架时，先用无依赖的入口脚本：`extends SceneTree`，在 `_initialize()` 中 `call_deferred` 执行用例；用例加载真实场景、发出输入或信号、等待 `process_frame` 后断言；失败计数大于 0 时 `quit(1)`，全部通过才 `quit(0)`。TeamFlow 源码仓库的 `examples/TeamFlowGame/tests/run_tests.gd` 即此写法，不需要安装插件。

用例增多或需要替身、参数化、报告时再引入框架，沿用项目已有选择：

- GUT：把 `addons/gut` 提交到工程，在游戏根放 `.gutconfig.json`（写明测试目录并启用测试结束后退出），检查入口传 `--test-script addons/gut/gut_cmdln.gd`。
- gdUnit4：使用其自带的命令行运行器，在 profile 中直接配置该命令的 argv。

引入框架属于新增依赖，按[依赖与工具链](../../../teamflow-core/references/DEPENDENCIES.md)锁定版本。首次接入时加一个故意失败的用例，确认检查判为失败后再删除，以证明退出码和错误输出能传到 TeamFlow。
