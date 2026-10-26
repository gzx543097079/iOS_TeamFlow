# TeamFlow

TeamFlow 是一套面向 AI Agent 辅助开发的中文工作流。它把需求拆解、实施边界、验证证据和交付记录串在一起，帮助小团队在 Codex 与 Claude Code 中保持一致的协作方式。

本仓库维护的是工作流本身：规则、Agent 专题、需求与验证工具，以及安装包的构建定义。它不包含业务 App 或游戏工程。当前版本为 **1.6.3**。

## 解决什么问题

- 以需求卡记录目标、范围、验收条件和进展，让 Agent 与团队成员围绕同一份任务记录协作。
- 按任务选择相关规则和验证方式，避免每次加载所有历史资料，也避免把自动化检查误当成人工验收。
- 为原生 iOS、Godot，以及 Godot 与 iOS 衔接场景提供对应的开发专题。
- 在完成时记录可复核的验证证据，并按所选模式交付可安装的工作流包。

主流程、需求卡状态和授权边界由[工作流规则](.agents/teamflow-core/references/WORKFLOW.md)定义。规则改进依据[内测试用记录](docs/TRIAL.md)；已知的检查与发布信息见[源码验证与分发](docs/RELEASE.md)。

## 分发模式

仓库提供三种面向项目的安装包。每种安装包都包含共用工作流核心，并按项目类型附带对应的 Agent 指南与开发专题。

| 安装包 | 适用项目 | 专题内容 |
| --- | --- | --- |
| `teamflow-ios-v1.6.3.zip` | 原生 iOS App | 共用核心、iOS 开发专题 |
| `teamflow-godot-v1.6.3.zip` | Godot 游戏 | 共用核心、Godot 开发专题 |
| `teamflow-godot-ios-v1.6.3.zip` | Godot 游戏及其 iOS 导出、原生插件 | 共用核心、Godot 与 iOS 专题 |

安装包可从 [GitHub Releases](https://github.com/gzx543097079/iOS_TeamFlow/releases) 获取。新项目选择对应模式；已有项目的接入、升级和定制说明见[安装与升级指南](.agents/teamflow-core/references/INSTALL.md)。

## 文件结构

```text
iOS_TeamFlow/
├── .agents/
│   ├── teamflow-core/
│   │   ├── references/       共用流程规则、检查证据、安装升级与专题资料
│   │   ├── scripts/          需求、项目检查、诊断、安装与升级实现
│   │   └── assets/           CI 与宿主权限配置模板
│   └── skills/
│       ├── iOS/              原生 iOS 开发专题与辅助工具
│       └── Godot/            Godot 开发、测试、发布及 iOS 衔接专题
├── scripts/                 源码仓库维护、规则检查与安装包构建入口
├── tests/                   工具、规则、安装消费与升级的回归测试
├── requirements/            本仓库自身的需求卡
├── docs/                    维护说明、Godot 接入与试用记录
├── .github/workflows/       GitHub Actions 发布流程
├── dist/                    本地生成的源码归档、安装包与校验文件
├── AGENTS.md                本源码仓库的 Agent 协作规则
├── README.md                项目介绍与目录概览
└── CHANGELOG.md             版本变更记录
```

共用主流程规则入口是 `.agents/teamflow-core/references/WORKFLOW.md`。`iOS/` 与 `Godot/` 是分发给业务项目的开发专题，不是本仓库自身的项目入口。

## 维护入口

源码仓库的协作规则写在根目录 `AGENTS.md`。工作流工具和规则有变更时，需要一起检查安装包清单、对应回归测试和相关文档；仅调整文档时，按 README 内容核对相关链接和版本信息即可。

源码验证：日常改动统一用 `workflow`，它按 covers 只运行负责所改模块的检查组（文档只跑 docs 组，单个平台脚本只跑对应平台组），不跑 Release 和全量；明确制作分发包用 `workflow-release`（包含 workflow，不另跑一次）。日常可用 `verify run --profile <名> --requirement <编号>` 按模块检查而不改需求卡；最终通过 `req complete <编号> --profile <名>` 确认 AC 并绑定证据，自动复用本需求有效且检查完整的最新结果。

版本变更历史见 [CHANGELOG](CHANGELOG.md)，第三方组件来源见[第三方说明](.agents/teamflow-core/references/THIRD-PARTY.md)。
