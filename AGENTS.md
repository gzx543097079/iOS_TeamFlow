# iOS 团队工作流入口

本仓库使用中文协作，是工作流工具仓库，不属于新建 iOS 产品。开始读取 `.agents/skills/ios-team-flow/references/WORKFLOW.md`；按本次范围加载专题，已读且未变化不重读。

<!-- ios-team-flow:start -->
## iOS 团队工作流

本项目采用仓库内的 `.agents/skills/ios-team-flow/SKILL.md`。实施 iOS 需求和提交前必须读取该文件，无需用户再次点名 Skill；按 OC / Swift / SwiftUI / UI 类型加载规范，维护 requirements/ 需求过程与 logs/ 审查记录。
新产品先整理 PRD 交团队确认。提交前只 review 本次改动，相同有效指纹复用；运行 `python3 scripts/review_gate.py check`。未经授权不提交或发布。
版本见 .agents/teamflow.json，Skill 与项目一起提交和克隆，不依赖用户级安装。找不到本地 Skill 时明确报告缺失，不自动改用其他项目或用户级同名版本。遵守项目现有具体约定，有冲突先说明。
<!-- ios-team-flow:end -->
