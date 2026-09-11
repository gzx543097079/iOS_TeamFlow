# iOS 团队工作流入口

本仓库使用中文协作。开始工作时读取 `.agents/skills/ios-team-flow/references/WORKFLOW.md`；执行 iOS 需求、实现或提交审查时读取 `.agents/skills/ios-team-flow/SKILL.md`。遵守上级指令及用户本次明确要求，已有子目录约定按适用范围处理，冲突应说明。

- 用户提出“做一个 / 修改 / 修复”即创建或续接 `requirements/` 需求记录。按工作流自行判断拆分，记录状态、过程与验收证据。普通小改动直接推进。
- 新 iOS 项目先基于 `.agents/skills/ios-team-flow/references/templates/new-project.md` 整理团队需求文档；缺失信息标待确认，交团队确认后再创建工程和业务代码。此仓库本身是工作流分发仓库，维护工作流不属于新建 iOS 产品。
- 已有业务工程读取 `.agents/skills/ios-team-flow/references/EXISTING-PROJECT.md`，首次建立项目现状记录，后续核对相关变化；只处理本次增量，已有配置不套用新项目默认值。
- `.h/.m/.mm` 加载 `.agents/skills/ios-team-flow/references/standards/objective-c.md`；`.swift` 加载 `.agents/skills/ios-team-flow/references/standards/swift.md`；SwiftUI 文件另加载 `.agents/skills/ios-team-flow/references/standards/swiftui.md`。所有 UI 改动先加载 `.agents/skills/ios-team-flow/references/standards/ui.md`。`.mm` 还遵守工程现有 C++ 规则。
- 根目录是 Git 与 Codex 打开目录。`.agents/`、`App/`（新工程默认）、`requirements/`、`logs/`、`scripts/` 同级。现有工程保留原目录。不要在 `.agents/skills/ios-team-flow/references/` 下创建业务工程或运行日志。

## Code Review Rules

- 提交前自动执行 `.agents/skills/ios-team-flow/references/REVIEW.md`，默认只审本次暂存改动，可读必要调用上下文；没有明确要求不做全仓审计。
- 检查正确性、规范、订阅价格/文案/产品一致性、内存、打点和疑似测试代码。所有维度都给结论，不适用需说明原因，未验证不算通过。
- 使用 `scripts/review_gate.py` 绑定 HEAD 和暂存内容；同一有效指纹复用已完成审查，不重复全量 review。指纹变化仅复查增量及关联影响；旧问题修复后记录复核。
- 自动 review 由 Codex 负责语义分析，脚本只提供记录、去重与提交门禁，不伪称静态扫描能证明没有内存泄漏。普通 Git 客户端需要接入 hook 才有门禁。
- 提交前执行 `python3 scripts/review_gate.py check`。只在用户授权提交时 commit；不因 review 完成自动 push 或发布。
