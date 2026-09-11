---
name: ios-team-flow
description: 中文 iOS 团队需求实施与提交审查。用于已安装本 Skill 的项目中的 iOS 新需求、缺陷修复、Objective-C、Swift、SwiftUI 代码生成及提交前 review，维护需求状态和审查证据。
---

# iOS 团队协作

本 Skill 采用项目级独立安装，必须位于当前项目 `.agents/skills/ios-team-flow/`，不依赖用户级目录或原始分发仓库。`SKILL_ROOT` 为本 SKILL.md 所在目录，不能从当前项目路径推算；`PROJECT_ROOT` 为本次工作的项目根目录，已有 Git 时用 git rev-parse --show-toplevel 确定。二者必须分开。

## 接入项目

每个项目只需接入一次。首先确认本 Skill 在当前项目的 `.agents/skills/ios-team-flow/` 内，拒绝用其他项目或用户级同名 Skill 代替。首次用于实施需求时，先检查项目 AGENTS.md 和已有约定，再运行：

```sh
python3 "<SKILL_ROOT>/scripts/setup_project.py" --project "<PROJECT_ROOT>"
```

上述为路径占位，执行时替换为已确认的绝对路径。脚本首次接入时生成带标记的入口、版本基线和门禁加载脚本；用户要求完整升级时按 [完整包升级](references/INSTALL.md#完整-skill-包升级默认预览) 先预览、保护定制并备份整个 Skill；已手动更新 Skill 的项目可运行同一接入命令更新托管入口。不创建业务工程、不改变 Git hook、不初始化嵌套 Git。脚本报告冲突时先读差异，保留团队原有规则再按用户已授权范围合并，禁止直接覆盖。非空 AGENTS.override.md 存在时接入实际生效的 override 文件。纯咨询不接入项目、不创建需求。

项目版本与本 Skill 不同不得静默升级规则：继续使用项目固定版本，或在用户明确要求升级时调整版本和入口。不能借升级自动覆盖项目定制规范。安装与版本说明见 [安装说明](references/INSTALL.md)。

## 执行

1. 读取 [工作流](references/WORKFLOW.md)。查找 PROJECT_ROOT 下 requirements/ 的相关需求，复用编号和历史。已有工程按 [已有项目流程](references/EXISTING-PROJECT.md) 首次记录项目现状，后续只核对本次相关变化，保留原配置。新 iOS 产品按 [PRD 模板](references/templates/new-project.md) 整理具体需求，交团队确认后创建业务工程。
2. 按改动读取：[OC](references/standards/objective-c.md)、[Swift](references/standards/swift.md)、[SwiftUI](references/standards/swiftui.md)。SwiftUI 同时执行 Swift；所有 UI 改动先读 [UI](references/standards/ui.md)。项目明确约定优先，解释冲突。
3. 用 [需求模板](references/templates/requirement.md) 记录拆分判断、过程状态与验收。需求、日志、工程和项目辅助脚本均写入 PROJECT_ROOT，不写入安装目录。
业务验证使用 [项目验证入口](references/PROJECT-CHECKS.md)，按实际工程配置本次必跑项并记录结果。

4. 提交前读取 [审查规程](references/REVIEW.md)，在 PROJECT_ROOT 运行 scripts/review_gate.py；同指纹复用，新增变化只复查增量与关联影响。用户未授权时不 commit/push。已授权的实施提交使用 Requirement 尾注，并按 [交付追踪](references/DELIVERY.md) 执行 finish 收尾并报告缺失或未归档记录，验收与后续远端状态分别登记。

规则、模板、版本和工具实现均直接维护在本 Skill 内，不需要外部规范目录或同步脚本。`<SKILL_ROOT>/references/` 表示本 Skill 的资料位置；`requirements/`、`logs/`、`scripts/`、`App/` 为项目根目录下的产物。项目接入版本记录在 `.agents/teamflow.json`，根 scripts/review_gate.py 加载本 Skill 的门禁实现。入口和完整 Skill 随项目提交；团队克隆后直接使用。

本 Skill 不把规则发布流水线安装进消费项目。发布本工作流版本属于源仓库维护，读取 [发布规程](references/RELEASE.md) 并使用源仓库发布工具；业务 App 发布读取 [App 发布流程](references/APP-RELEASE.md) 并结合既有项目流程执行。

业务验收读取 [团队验收与问题复核](references/ACCEPTANCE.md)，不能将自动 review 或提交授权当作团队产品验收。
