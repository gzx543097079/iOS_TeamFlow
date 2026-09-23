# iOS TeamFlow

面向 Codex 驱动开发的中文 iOS 工作流。当前版本为 **3.1.2**。

需求、实施、验证与显式交付的规则见 [WORKFLOW](.agents/skills/ios-team-flow/references/WORKFLOW.md)；[Skill 入口](.agents/skills/ios-team-flow/SKILL.md) 按任务加载工程专题。

## 安装

需要 Python 3.10+、Git；业务 App 构建还需要相应 Xcode 环境。将完整 `ios-team-flow` 放入项目的 `.agents/skills/`，在 Git 根执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

接入生成项目入口和配置，详情见 [INSTALL](.agents/skills/ios-team-flow/references/INSTALL.md)。

## 常用命令

```sh
python3 scripts/teamflow.py req create --title "登录失败提示优化"
python3 scripts/teamflow.py req list
python3 scripts/teamflow.py req complete REQ-0001 --profile change
```

`change` 是项目自行配置的 profile 名。需求跟踪见 [WORKFLOW](.agents/skills/ios-team-flow/references/WORKFLOW.md)，命令配置与输入绑定见 [PROJECT-CHECKS](.agents/skills/ios-team-flow/references/PROJECT-CHECKS.md)。

## 资料与工具

- [Git 动作](.agents/skills/ios-team-flow/references/GIT-ACTIONS.md) 与 [App 外部动作](.agents/skills/ios-team-flow/references/APP-RELEASE.md)。
- [已有工程](.agents/skills/ios-team-flow/references/EXISTING-PROJECT.md)；大型项目可按需启用 [模块索引](.agents/skills/ios-team-flow/references/MODULE-CONTEXT.md)。
- [本地化](.agents/skills/ios-team-flow/references/LOCALIZATION.md)、[架构](.agents/skills/ios-team-flow/references/ARCHITECTURE.md)、[日志组件](.agents/skills/ios-team-flow/references/LOGGING.md)。
- [源码验证与分发](.agents/skills/ios-team-flow/references/RELEASE.md)。Demo、测试和 ZIP 发布工具属于源码仓库，不进入独立 Skill 包。
