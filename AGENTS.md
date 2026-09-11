# iOS 团队工作流入口

本仓库使用中文协作。开始读取 `.agents/skills/ios-team-flow/references/WORKFLOW.md`；实施和审查读取本地 Skill。只加载本次相关资料，已读且未变化的文件不重复读取。

- 新需求用 create 生成 UUID/v3 精简卡；状态与验收只维护一份，状态、验收或交付事实变化时用 finish 生成并核对交付索引，实际验收完成才用 --accept。历史需求不补同步。
- 新 iOS 产品先确认具体 PRD；已有项目按 EXISTING-PROJECT.md 增量处理，保留既有配置。本仓库维护不属于新建 iOS 产品。
- 按文件加载 Objective-C、Swift、SwiftUI 规范；UI 改动先读 ui.md，.mm 同时沿用工程 C++ 约定。
- 产物位于项目根目录 requirements/、logs/、scripts/ 和业务工程目录，不写进 Skill 的 references/。

## Code Review Rules

提交前按 REVIEW.md 审查本次暂存内容及必要上下文，七个维度给出结论/证据；脚本不代替语义分析。引用的测试证据由最终门禁统一核对，无需预先重复 verify。按指纹复用，变化只复核增量及关联影响；执行 review_gate.py check。需求卡不嵌入覆盖自身的当前审查指纹。

<!-- ios-team-flow:start -->
## iOS 团队工作流

本项目采用仓库内的 `.agents/skills/ios-team-flow/SKILL.md`。实施 iOS 需求和提交前必须读取该文件，无需用户再次点名 Skill；按 OC / Swift / SwiftUI / UI 类型加载规范，维护 requirements/ 需求过程与 logs/ 审查记录。
新产品先整理 PRD 交团队确认。提交前只 review 本次改动，相同有效指纹复用；运行 `python3 scripts/review_gate.py check`。未经授权不提交或发布。
版本见 .agents/teamflow.json，Skill 与项目一起提交和克隆，不依赖用户级安装。找不到本地 Skill 时明确报告缺失，不自动改用其他项目或用户级同名版本。遵守项目现有具体约定，有冲突先说明。
<!-- ios-team-flow:end -->
