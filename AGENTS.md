# TeamFlow 源码仓库

本仓库是 TeamFlow 工作流本身的源码，使用中文协作；这里没有 App 或游戏工程，不安装任何模式的托管入口。

- 主流程、需求卡与授权边界按 `.agents/teamflow-core/references/WORKFLOW.md` 执行，命令使用 `python3 scripts/teamflow.py`。
- 只读 WORKFLOW 与本次实际要改的文件；iOS、Godot Skill 是分发内容，只在改动涉及时读取对应文件，不把它们当作本仓库的工作入口。
- 验证按 README「源码仓库」的 profile 选择；规则改动以 `docs/TRIAL.md` 中真实项目的使用记录为依据。
- 改动规则或工具时同步核对安装包内容：`scripts/package_release.py`、`tests/` 与相关文档。
- `tests/test_token_budget.py` 是维护护栏，防止文档膨胀，不是优化目标：必要内容使上限逼近时按约 10% 余量放宽，不为过测试压缩规则；它不进入安装包，也不约束使用时的读取与验证。
