# iOS TeamFlow

中文 Codex iOS 团队工作流：Apple UI 规范、Objective-C / Swift / SwiftUI 规范、需求拆分与过程追踪、提交前自动审查与去重、Release 压缩包分发。

从 [使用说明](.agents/skills/ios-team-flow/references/README.md) 开始；先阅读 [UI 规范](.agents/skills/ios-team-flow/references/standards/ui.md)。

本地验证与生成分发包：

```sh
python3 scripts/validate_workflow.py
python3 -m unittest discover -s tests -v
python3 scripts/package_release.py
```

分发时将 ZIP 内容合入项目 Git 根目录，包含 AGENTS.md、.agents 和 .github。工程、.agents、requirements、logs、scripts 同级。规范和工具实现只在 .agents/skills/ios-team-flow 内维护。完整规则见 [工作流](.agents/skills/ios-team-flow/references/WORKFLOW.md)，参考项目与官方资料见 [调研记录](.agents/skills/ios-team-flow/references/SOURCES.md)。

采用项目级独立安装：使用 `ios-team-flow-skill-v1.3.0.zip`，将完整目录放入目标项目 `.agents/skills/`，再从项目根目录运行一次：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

此后直接提需求，无需每次点名 Skill。完整 Skill 与入口随项目提交，团队克隆即可获得相同版本，不需要个人安装。详见 [项目安装与接入](.agents/skills/ios-team-flow/references/INSTALL.md)。

## 空项目：创建文件夹并接入

1. 创建并进入项目根目录，再创建 Skill 存放目录。将 `MyApp` 替换为你的项目目录名；已有空项目文件夹时直接进入该目录。

```sh
mkdir -p ~/Desktop/MyGit/MyApp
cd ~/Desktop/MyGit/MyApp
mkdir -p .agents/skills
```

2. 下载并解压 `ios-team-flow-skill-v1.3.0.zip`，将其中完整的 `ios-team-flow` 文件夹复制到刚创建的 `.agents/skills/`。最终路径必须是 `.agents/skills/ios-team-flow/SKILL.md`，不要只复制 SKILL.md，也不要多套一层目录。macOS Finder 可按 `Command + Shift + .` 显示隐藏文件夹。

3. 在项目根目录执行一次接入命令：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

4. 在 Codex 打开该项目根目录并开始新会话，直接描述产品需求。无需提前创建 Xcode 工程；先整理需求文档，团队确认后再在 `App/` 中创建工程。

接入脚本会创建 `AGENTS.md`、`.agents/teamflow.json`、`scripts/review_gate.py`、`requirements/` 和 `logs/reviews/`。首次提交审查前，若该目录尚未属于任何 Git 仓库，在项目根目录运行 `git init`；已有仓库使用既有 Git 根目录，不创建嵌套仓库。

完整说明见 [空项目接入](.agents/skills/ios-team-flow/references/INSTALL.md#空项目接入没有-agentsskills-时)。

升级项目内 Skill 后，仍运行同一条 `setup_project.py --project .` 命令。脚本自动更新版本和未定制的托管文件，保留团队规则，并在替换已有文件前备份。支持从 1.2.1 接入记录迁移；具体见 [升级说明](.agents/skills/ios-team-flow/references/INSTALL.md#团队共享与升级)。

已有业务工程按 [已有项目流程](.agents/skills/ios-team-flow/references/EXISTING-PROJECT.md) 处理：首次记录项目现状，后续增量实施并验证相关路径，保留实际架构和配置。

业务项目可配置 [构建与测试入口](.agents/skills/ios-team-flow/references/PROJECT-CHECKS.md)，通过 [交付追踪](.agents/skills/ios-team-flow/references/DELIVERY.md) 关联需求、提交、PR 和 Release。

[可选 Git 检查](.agents/skills/ios-team-flow/references/GIT-CHECKS.md) 提供保留原 Hook 的安装/卸载，以及按明确 base/head 核验的 PR 工作流。本仓库已配置 PR 检查模板；团队按需将该检查设为分支必需项。本地 Hook 需每个克隆目录显式安装。
