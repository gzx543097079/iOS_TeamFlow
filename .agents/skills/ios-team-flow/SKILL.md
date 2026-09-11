---
name: ios-team-flow
description: 中文 iOS 团队需求实施与提交审查。用于已安装本 Skill 的项目中的 iOS 新需求、缺陷修复、Objective-C、Swift、SwiftUI 代码生成及提交前 review，维护需求状态和审查证据。
---

# iOS 团队协作

本 Skill 采用项目级独立安装，必须位于当前项目 `.agents/skills/ios-team-flow/`，不依赖用户级目录或原始分发仓库。`SKILL_ROOT` 为本 SKILL.md 所在目录，不能从当前项目路径推算；`PROJECT_ROOT` 为本次工作的项目根目录，已有 Git 时用 git rev-parse --show-toplevel 确定。二者必须分开。

## 接入项目（仅首次或明确升级时）

本 Skill 必须位于当前项目 `.agents/skills/ios-team-flow/`，不使用用户级或其他项目的同名 Skill。首次实施时检查项目入口及约定，运行：

```sh
python3 "<SKILL_ROOT>/scripts/setup_project.py" --project "<PROJECT_ROOT>"
```

替换为实际绝对路径。接入保留既有规则，不创建业务工程或修改 Hook；冲突先比较再按已授权范围合并，不直接覆盖。纯咨询不接入、不建卡。项目固定版本与 Skill 不同不得静默升级。

需要安装、入口恢复或完整包升级时才读取 [INSTALL](references/INSTALL.md)。完整升级先预览、保护定制并备份；不因版本不同自动迁移项目。

## 执行

1. 读取 [工作流](references/WORKFLOW.md)。查找 PROJECT_ROOT 下 requirements/ 的相关需求，复用编号和历史。已有工程按 [已有项目流程](references/EXISTING-PROJECT.md) 首次记录项目现状，后续只核对本次相关变化，保留原配置。新 iOS 产品按 [PRD 模板](references/templates/new-project.md) 整理具体需求，交团队确认后创建业务工程。
2. 按改动读取：[OC](references/standards/objective-c.md)、[Swift](references/standards/swift.md)、[SwiftUI](references/standards/swiftui.md)。SwiftUI 同时执行 Swift；所有 UI 改动先读 [UI](references/standards/ui.md)。项目明确约定优先，解释冲突。
3. 新需求通过 delivery.py create --title 从 [精简模板](references/templates/requirement.md) 生成 UUID 卡，只在卡片维护一次状态与 AC 结果；交付索引自动生成，历史卡不补同步。阶段结束与最终回复前执行本需求 finish（自带写后核验），未提交也适用；首次实际验收完成及复核后用 finish --accept 绑定证据，普通同步不能重设基线。需求、日志、工程和项目辅助脚本均写入 PROJECT_ROOT，不写入安装目录。
业务验证使用 [项目验证入口](references/PROJECT-CHECKS.md)，按实际工程配置本次必跑项并记录结果。

4. 提交前读取 [审查规程](references/REVIEW.md)，在 PROJECT_ROOT 运行 scripts/review_gate.py；同指纹复用，新增变化只复查增量与关联影响。用户未授权时不 commit/push。已授权的实施提交使用 Requirement 尾注，并按 [交付追踪](references/DELIVERY.md) 执行 finish 收尾并报告缺失或未归档记录，验收与后续远端状态分别登记。

规则、模板、版本和工具实现均直接维护在本 Skill 内，不需要外部规范目录或同步脚本。`<SKILL_ROOT>/references/` 表示本 Skill 的资料位置；`requirements/`、`logs/`、`scripts/`、`App/` 为项目根目录下的产物。项目接入版本记录在 `.agents/teamflow.json`，根 scripts/review_gate.py 加载本 Skill 的门禁实现。入口和完整 Skill 随项目提交；团队克隆后直接使用。

本 Skill 不把规则发布流水线安装进消费项目。发布本工作流版本属于源仓库维护，读取 [发布规程](references/RELEASE.md) 并使用源仓库发布工具；业务 App 发布读取 [App 发布流程](references/APP-RELEASE.md) 并结合既有项目流程执行。

风险或已确认约定要求团队验收时读取 [团队验收与问题复核](references/ACCEPTANCE.md)；普通低风险且验收明确的改动可自审。不能将自动 review 或提交授权当作团队产品验收。已读且未变化的规范不重读，按 WORKFLOW 的最小路径加载当前阶段资料。
