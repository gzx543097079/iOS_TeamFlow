# iOS TeamFlow

项目级中文 Codex iOS 工作流：Apple UI 规范、Objective-C / Swift / SwiftUI 规范、需求追踪、构建测试、提交审查、团队验收与 App 发布记录。完整规则只维护在 `.agents/skills/ios-team-flow/`。

## 每个项目接入一次

需要 Python 3.10+、Git 和支持项目 Skill 的 Codex；业务 App 构建另需匹配的 macOS/Xcode。

1. 空项目先创建目录；已有项目直接进入其 Git 根目录，再创建 `.agents/skills/`，保留原业务工程。

```sh
mkdir -p ~/Desktop/MyGit/MyApp
cd ~/Desktop/MyGit/MyApp
mkdir -p .agents/skills
```

2. 从 [GitHub Releases](https://github.com/gzx543097079/iOS_TeamFlow/releases) 下载选定版本的 `ios-team-flow-skill-vX.Y.Z.zip`，将解压出的完整 `ios-team-flow` 文件夹放入 `.agents/skills/`。最终必须是 `.agents/skills/ios-team-flow/SKILL.md`，不要多套目录或只复制一个文件。Finder 按 `Command + Shift + .` 显示隐藏目录。

3. 在项目根目录执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

脚本生成/合并 `AGENTS.md`、`.agents/teamflow.json`、`scripts/review_gate.py`，创建 `requirements/` 和 `logs/reviews/`。若目录尚不属于任何 Git 仓库，首次提交前执行 `git init`，不要创建嵌套仓库。

4. 在 Codex 打开项目根目录并开始新会话，直接提出需求，例如“增加订阅管理页，显示套餐并支持恢复购买”。后续无需再次点名 Skill。将完整 Skill、入口及项目记录一同提交，团队克隆后使用相同版本，无需安装到个人目录。

只有复制 Skill 而未接入 AGENTS.md 时，不应依赖每次都能自动触发。接入不创建业务 App，也不安装 Hook。详细冲突处理和安装边界见 [安装说明](.agents/skills/ios-team-flow/references/INSTALL.md)。

## 接入后的处理

| 场景 | 行为与入口 |
| --- | --- |
| 新产品 | 先生成 [PRD](.agents/skills/ios-team-flow/references/templates/new-project.md)，团队确认后建工程；默认 Swift + UIKit、iOS 14、导航栈、无 Tab Bar、支持深色并跟随系统 |
| 已有工程 | [记录现状并增量实施](.agents/skills/ios-team-flow/references/EXISTING-PROJECT.md)，保留实际配置，不套用新项目默认值 |
| 日常需求 | [自行判断拆分并追踪](.agents/skills/ios-team-flow/references/WORKFLOW.md)：⬜ 未执行 → 🔄 执行中 → 🧪 待验证 → ✅ 执行完成；失败重开并留证 |
| 构建与测试 | [配置项目命令/profile](.agents/skills/ios-team-flow/references/PROJECT-CHECKS.md)，记录实际执行结果；无明确要求不验证超大字号 |
| 提交前审查 | [默认只审本次暂存改动](.agents/skills/ios-team-flow/references/REVIEW.md)，检查正确性、规范、订阅价格/文案/商品一致性、内存、打点、测试代码及安全；同一有效指纹复用 |
| Git 客户端/PR | [按需安装 Hook 和 PR 检查](.agents/skills/ios-team-flow/references/GIT-CHECKS.md)；本地 Hook 每个克隆显式安装，PR 使用明确 base/head，必需检查另在仓库配置 |
| 团队验收与交付 | [验收及问题复核](.agents/skills/ios-team-flow/references/ACCEPTANCE.md) 区分自审、测试、团队确认；[交付追踪](.agents/skills/ios-team-flow/references/DELIVERY.md) 关联提交、PR 与 GitHub Release |
| App 发布 | [归档、TestFlight、审核和商店状态](.agents/skills/ios-team-flow/references/APP-RELEASE.md) 单独记录，不以 GitHub Release 代表 App 上线 |
| 场景试运行 | [验证矩阵](.agents/skills/ios-team-flow/references/SCENARIOS.md) 区分 CLI 夹具演练与真实项目、设备和平台证据 |

所有规范和模板见 [Skill 内容导航](.agents/skills/ios-team-flow/references/README.md)。Codex 负责语义审查；脚本负责记录、去重和门禁，不自动证明无内存泄漏或价格正确。需求完成不自动授权提交、推送或发布。

## 升级与目录

保存团队定制及当前版本后，替换项目内完整 Skill，再运行同一条接入命令。脚本采用托管基线合并，真实冲突会停止。新版支持写入失败回滚与中断恢复，详见 [接入中断与恢复](.agents/skills/ios-team-flow/references/INSTALL.md#接入中断与恢复)。恢复托管入口不等于回退手动替换的 Skill。

```text
项目根目录/
├── AGENTS.md
├── .agents/skills/ios-team-flow/
├── .agents/teamflow.json
├── .github/workflows/          # 可选业务 CI / PR 检查
├── App/                        # 新工程默认；已有工程保留原位置
├── requirements/               # PRD、进度、验收与发布记录
├── logs/                       # 脱敏验证与审查证据
└── scripts/                    # 根门禁入口与项目辅助脚本
```

需求、脚本和脱敏日志可随 Git 上传；密钥、用户数据和大型构建产物不入库。GitHub Actions 位于根 `.github/workflows/` 才能被发现。

## 源仓库维护与版本

业务项目使用独立 Skill 包。`iOS-TeamFlow-vX.Y.Z.zip` 是包含源仓库校验、测试和工作流发布 CI 的完整分发包，不要将其中发布流水线直接覆盖进业务仓库。

当前正式版本为 1.3.0；本分支新增能力见 [未发布变更](.agents/skills/ios-team-flow/references/CHANGELOG.md#未发布)，**已发布的 1.3.0 附件不包含后续源码改动**。使用未发布能力需固定对应源码 commit 并复制完整 Skill；正式团队分发建议使用后续已发布版本，不能仅凭 VERSION 相同认定文件一致。

源仓库验证与打包：

```sh
python3 scripts/validate_workflow.py
python3 -m unittest discover -s tests -v
python3 scripts/package_release.py
```

本地打包不等于发布，未发布源码产生的同版本文件不能覆盖既有 Release 附件。发布时按 [工作流发布规程](.agents/skills/ios-team-flow/references/RELEASE.md) 更新版本、打标签并上传 ZIP 与校验和。参考项目及官方来源见 [调研记录](.agents/skills/ios-team-flow/references/SOURCES.md)。
