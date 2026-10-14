# 工作流入口

本仓库使用中文协作，是工作流工具仓库，不属于新建 iOS 产品。

<!-- teamflow:start -->
## Godot 工作流

读取并遵循 `.agents/skills/Godot/SKILL.md`；iOS 原生插件按该 Skill 的路由加载对应规范。需求、验证和交付复用 TeamFlow 核心；命令使用 `python3 scripts/teamflow.py`。

首次仅读取上述 Skill 和 `.agents/teamflow-core/references/WORKFLOW.md`。其他 Skill、专题、模板和脚本按本次任务需要读取，不因目录、依赖声明或链接出现而批量加载。跨平台任务直接引用相关规范，不自动读取另一 Skill 的完整入口；同一会话已读且未变化的内容直接复用。
<!-- teamflow:end -->
