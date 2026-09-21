# iOS TeamFlow

项目级中文 iOS 团队工作流，支持 Objective-C、Swift、SwiftUI、UI 规范、需求追踪、验证、提交审查和交付记录。当前版本为 **2.3.2**（源码版本，未发布 Release）。完整规则只维护在项目 `.agents/skills/ios-team-flow/`，团队克隆后共用。

## 先看你属于哪种情况

| 情况 | 从哪里开始 |
| --- | --- |
| 只有空文件夹，尚无 iOS 工程 | 按下面的“空文件夹如何使用”，无需提前创建 Xcode 工程 |
| 已有业务工程，首次接入 | 进入已有 Git 根目录，创建 `.agents/skills/`，从下面第 2 步开始；不重新 git init、不移动工程 |
| 克隆了团队已经接入的项目 | 直接在 Codex 打开项目根的新会话，不重复下载或接入；可选本地 Hook 按克隆单独安装 |
| 已接入，需要升级或恢复 | 按 [安装说明中的完整包升级与恢复](.agents/skills/ios-team-flow/references/INSTALL.md) 预览并处理，不直接覆盖团队定制 |

需要 Python 3.10+、Git 和支持项目 Skill 的 Codex；实际 App 构建另需项目匹配的 macOS/Xcode。可先用 `python3 --version`、`git --version` 核对环境。

## 空文件夹如何使用

### 1. 准备项目根目录

在终端创建并进入你自己的项目目录，例如：

```sh
mkdir -p ~/Desktop/MyGit/MyApp
cd ~/Desktop/MyGit/MyApp
mkdir -p .agents/skills
```

如果已有空文件夹，直接进入它再创建 `.agents/skills/`。此目录也是后续 Codex 打开、存放需求和业务工程的根目录。

先用 `git rev-parse --show-toplevel` 确认是否属于现有仓库。只有目录尚未纳入任何 Git 仓库时才执行：

```sh
git init
```

如果返回的是上级仓库根，使用原仓库根，或另选仓库外的新目录，不创建嵌套 Git 仓库。Git 必须在首次需求收尾前就绪。

### 2. 放入完整 Skill

当前源码版本为 2.3.2：大型已有项目通过 `.agents/project-modules.json` 和 `module_context.py` 执行模块路由、Git 增量检查和受控基准刷新，不再只依赖文字约束。商城 Demo 仅保留在源码仓库，不进入分发包。

2.3.2 本次只推送源码、未发布 Release；需要正式附件时仍从 [2.3.0 Release](https://github.com/gzx543097079/iOS_TeamFlow/releases/tag/teamflow-v2.3.0) 下载 `ios-team-flow-skill-v2.3.0.zip`，解压后把完整的 `ios-team-flow` 文件夹放到 `.agents/skills/`。

最终必须是 `.agents/skills/ios-team-flow/SKILL.md`，不要只复制 SKILL.md，也不要多套一层同名文件夹。Finder 按 `Command + Shift + .` 显示隐藏文件夹。

```text
MyApp/
└── .agents/
    └── skills/
        └── ios-team-flow/
            ├── SKILL.md
            ├── references/
            └── scripts/
```

已有同名 Skill 时先比较版本和定制，按升级流程处理。业务项目使用上述独立 Skill 包；`iOS-TeamFlow-v2.3.0.zip` 是带源仓库测试和发布流水线的完整分发包。

### 3. 接入项目并查看诊断

仍在项目根目录执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

也可以在放好 Skill 后让 Codex“接入当前项目的 iOS 工作流”。脚本保留既有规则，生成/合并有效指令入口、`.agents/teamflow.json`、`scripts/review_gate.py`，创建 `requirements/` 和 `logs/reviews/`。它不会创建 App、安装 Hook、提交代码或上传远端。

接入结束会自动诊断。Git 根、Skill 和入口问题先解决；新工程创建后补齐实际验证配置，已有工程从既有 CI/脚本提取命令；未安装可选本地 Hook 不阻塞接入。重复查看诊断时执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project . --doctor
```

诊断只读，不执行项目测试；入口就绪不代表 App 已构建通过。冲突、AGENTS.override.md 等详细规则见 [INSTALL](.agents/skills/ios-team-flow/references/INSTALL.md)。

### 4. 在 Codex 中提出产品需求

打开这个项目根目录，开始新会话。例如：

> 做一个习惯记录 App，先整理新项目需求文档，确认后再创建工程。

Codex 先根据 [详细新项目需求模板](.agents/skills/ios-team-flow/references/templates/new-project.md) 整理具体 PRD 和需求卡。模板保留工程目录、权限、多语言、订阅等详细条目；新项目默认语言为英语和简体中文，其他语言按需启用；按启动、功能、发布阶段填写；先确认启动范围，再创建最小可运行工程。未确认的默认建议不会自动成为产品配置。

已有项目可以直接说“修复登录页的问题”或“增加订阅管理页”，按 [已有项目流程](.agents/skills/ios-team-flow/references/EXISTING-PROJECT.md) 核对相关现状，保留实际框架、语言、部署目标和目录。大型项目按需使用 [模块增量工具](.agents/skills/ios-team-flow/references/MODULE-CONTEXT.md) 建立可执行索引；后续工具先返回命中模块、Git 变化、建议文件和扩大范围信号，无需每次点名 Skill、重复接入或通读全仓。

### 5. 团队共享

经审查并授权后，将完整 Skill、有效项目入口、接入记录、辅助脚本及脱敏需求/日志随项目提交。其他成员克隆后在项目根使用相同规则，无需个人安装。

确认 `.gitignore` 不忽略整个 `.agents/`、`requirements/` 或 `logs/`；缓存、备份、构建输出和敏感原始日志按实际项目排除。密钥、证书私钥、用户数据和大型构建产物不入库。

## 日常怎么协作

成员负责提出需求、确认必要业务决定、实际验收和授权提交/推送/发布。Codex 负责建卡、实施、选择和运行验证、更新记录、提交前审查与交付同步。正常使用不要求成员背诵需求编号、finish 或门禁参数。

需求编号采用 `REQ-YYYYMMDD-HHMMSSmmmZ-随机码`，文件名按 UTC 创建时间排序。用 `delivery.py list` 查看序号、时间、标题和状态，`list --reverse` 查看最新需求；序号仅用于浏览，引用始终使用固定编号。

提出需求 → 一次确定范围与 AC（验收条件）→ 实施和验证 → 更新验收记录并绑定证据 → 最终提交门禁 → 授权交付后同步事实。

- 小需求在一张卡完成，复杂需求按可交付结果拆分；同一需求续接原卡，历史需求不补同步。
- 当前状态和 AC 结果只在需求卡维护；测试命令及范围在 `.agents/project-checks.json`；原始结果由日志保存、卡片引用，Git 交付索引自动生成。
- 输入和事实未变不重复测试、审查或收尾。自动测试验收引用真实 result；已封存验收绑定当时提交，新需求不会自动迫使旧需求重验。
- 团队验收与测试、自审分别取证。待团队验收也可按授权提交、推送或开 PR，需求保持待验证；合并/发布遵守团队门槛。
- 提交前默认审查本次暂存内容，检查正确性、规范、订阅、内存、打点、测试代码及安全；工具核对记录和指纹，不能代替语义审查或证明无泄漏。
- 生成交付记录可随下一次正常提交归档；需要立即归档时复用未变审查维度，核对新增事实和安全。没有授权不自动提交、推送或发布。

出现实际流程缺陷、重复返工或明确纠正时，按 [自我进化机制](.agents/skills/ios-team-flow/references/EVOLUTION.md) 改进相关规则、模板或工具；复用现有需求与验证记录，无问题不额外复盘。机制在任务内执行，提交和发布仍按授权。该能力随 2.1.0 分发。

新生成工程会自动加入对应 OC/Swift [分级日志组件](.agents/skills/ios-team-flow/references/LOGGING.md)，完成目标成员关系和编译条件设置；Debug 全等级输出，Release 关闭。此能力为源码未发布变更。

## 资料和记录在哪里

| 要处理的事情 | 入口 |
| --- | --- |
| 日常顺序、分工、状态含义和唯一记录归属 | [WORKFLOW](.agents/skills/ios-team-flow/references/WORKFLOW.md) |
| 新项目需求细节与分阶段确认 | [详细新项目模板](.agents/skills/ios-team-flow/references/templates/new-project.md) |
| 需求卡格式、已有项目现状 | [需求卡模板](.agents/skills/ios-team-flow/references/templates/requirement.md) · [现状模板](.agents/skills/ios-team-flow/references/templates/project-context.md) |
| UI 和语言规范，按改动加载 | [UI](.agents/skills/ios-team-flow/references/standards/ui.md) · [Objective-C](.agents/skills/ios-team-flow/references/standards/objective-c.md) · [Swift](.agents/skills/ios-team-flow/references/standards/swift.md) · [SwiftUI](.agents/skills/ios-team-flow/references/standards/swiftui.md) |
| 配置实际构建/测试命令、检查输入和结果 | [PROJECT-CHECKS](.agents/skills/ios-team-flow/references/PROJECT-CHECKS.md)；工具测试不代替 App 验证，未明确要求不验证超大字号 |
| 团队验收、失败和多轮复核证据 | [ACCEPTANCE](.agents/skills/ios-team-flow/references/ACCEPTANCE.md) · [详细证据模板](.agents/skills/ios-team-flow/references/templates/acceptance.md) |
| 手动操作或排错：验收绑定、只读 status、按需历史、PR/Release 关联 | [DELIVERY](.agents/skills/ios-team-flow/references/DELIVERY.md) |
| 提交审查、归档继承 | [REVIEW](.agents/skills/ios-team-flow/references/REVIEW.md) |
| 可选本地提交 Hook | [GIT-CHECKS](.agents/skills/ios-team-flow/references/GIT-CHECKS.md)；每个克隆单独接入，可被 `--no-verify` 跳过，不宣称远端强制门禁 |
| App 归档、TestFlight、审核和商店上线 | [APP-RELEASE](.agents/skills/ios-team-flow/references/APP-RELEASE.md) · [发布记录模板](.agents/skills/ios-team-flow/references/templates/app-release.md)；GitHub Release 不代表 App Store 上线 |
| 场景试运行与验证边界 | [SCENARIOS](.agents/skills/ios-team-flow/references/SCENARIOS.md) |
| 安装冲突、完整包升级、预览与恢复 | [INSTALL](.agents/skills/ios-team-flow/references/INSTALL.md) |

```text
项目根目录/                       # Git 与 Codex 打开位置
├── AGENTS.md                     # 有 override 时以有效指令入口为准
├── .agents/skills/ios-team-flow/  # 项目固定版本的完整 Skill
├── .agents/teamflow.json         # 接入记录
├── .agents/project-modules.json  # 大型项目按需建立的可执行模块索引
├── .agents/project-checks.json   # 工程就绪后配置实际验证
├── App/                          # 新工程默认；已有工程保留目录
├── requirements/                 # PRD、需求卡、验收证据及生成交付索引
├── logs/                         # 测试和审查证据
├── scripts/                      # 根门禁入口及项目辅助脚本
└── .github/workflows/            # 可选 push 校验与发布流程
```

按当前阶段阅读所需专题，不要求成员通读全部规范；完整导航见 [Skill 内容导航](.agents/skills/ios-team-flow/references/README.md)。

## 源仓库维护与版本

2.3.2 将大型项目模块路由工具化：配置记录完整基准和稳定影响关系，命令返回四类 Git 变化、建议读取文件与失效/横切扩大信号，并受控刷新基准。本次只提交并推送源码，不创建 Release。2.3.1 移除 PR/分支保护门禁依赖并修复 Release 先公开后验证问题。源码 Demo 不进入分发包。保留 Scene 生命周期、Bug Fix、中文注释、自动日志、自我进化与异常需求卡容错。需求编号按 UTC 创建时间排序，支持列表、倒序和 JSON 查询；日常 CI 按改动选择测试，正式发布、公共或未知变化仍执行全量。工具输出沿用 1.10.1，新项目默认英语和简体中文。版本变化见 [CHANGELOG](.agents/skills/ios-team-flow/references/CHANGELOG.md)。

以下命令用于工作流分发仓库维护，不要求业务项目为了接入而运行：

```sh
python3 scripts/run_workflow_checks.py --full
python3 scripts/package_release.py
```

工作流 ZIP 发布按 [RELEASE](.agents/skills/ios-team-flow/references/RELEASE.md)，本地打包不代表已发布；完整分发包中的发布流水线不直接覆盖进业务项目。真实 App 示例只在源码 `App/TeamFlowDemo/`，不随独立 Skill 包分发。参考来源见 [SOURCES](.agents/skills/ios-team-flow/references/SOURCES.md)。

## Bug 修复模板与历史

缺陷使用 [Bug Fix 模板](.agents/skills/ios-team-flow/references/templates/bug-fix.md)，包含复现、根因、修复、回归和处理历史。创建与续接规则见 [缺陷处理规程](.agents/skills/ios-team-flow/references/BUGFIX.md)。本仓库已有记录入口见 `requirements/BUGFIX-HISTORY.md`；业务项目的真实记录保留在各自 requirements/。
