# iOS TeamFlow

面向 Codex 驱动开发的中文 iOS 工作流。当前版本为 **3.3.3**。

需求、实施、验证与显式交付的规则见 [WORKFLOW](.agents/skills/ios-team-flow/references/WORKFLOW.md)；[Skill 入口](.agents/skills/ios-team-flow/SKILL.md) 按任务加载工程专题。

## 安装

需要 Python 3.10+、Git；业务 App 构建还需要相应 Xcode 环境。

新项目只有空目录时，先创建并进入自己的项目根目录：

```sh
mkdir -p ~/Desktop/MyGit/MyApp
cd ~/Desktop/MyGit/MyApp
mkdir -p .agents/skills
```

先运行 `git rev-parse --show-toplevel` 核对是否已属于 Git 仓库；只有不属于任何仓库时才运行 `git init`。如果显示的是上级仓库根，改在该仓库根接入，或另选仓库外的目录，不创建嵌套仓库。已有 Git 项目直接进入其根目录，仅执行 `mkdir -p .agents/skills`。

从 [v3.3.3 Release](https://github.com/gzx543097079/iOS_TeamFlow/releases/tag/teamflow-v3.3.3) 下载独立 Skill 包 `ios-team-flow-skill-v3.3.3.zip`。例如下载到 `~/Downloads` 后，在项目根解压并接入：

```sh
unzip ~/Downloads/ios-team-flow-skill-v3.3.3.zip -d .agents/skills
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

确认最终路径是 `.agents/skills/ios-team-flow/SKILL.md`，不要只复制 `SKILL.md`，也不要多套一层同名目录。已有同名 Skill 时先按 [安装说明](.agents/skills/ios-team-flow/references/INSTALL.md) 核对差异和定制，再升级；已接入的团队项目无需重复安装。

接入后可只读检查入口：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project . --doctor
```

创建业务工程后，如尚无 `.agents/project-checks.json`，按实际构建与测试命令配置验证：

```sh
python3 scripts/teamflow.py verify init
```

`verify init` 只生成待填写的 `.agents/project-checks.json`；按 [项目构建与测试](.agents/skills/ios-team-flow/references/PROJECT-CHECKS.md) 填入真实检查命令，再运行对应 profile。接入脚本生成项目入口和需求目录，不创建业务 App。详情见 [INSTALL](.agents/skills/ios-team-flow/references/INSTALL.md)。

## 常用命令

```sh
python3 scripts/teamflow.py req create --title "登录失败提示优化"
python3 scripts/teamflow.py req list
# 以下为按需使用的只读辅助
python3 scripts/teamflow.py doctor
python3 scripts/teamflow.py verify suggest
python3 scripts/teamflow.py req resume REQ-0001
python3 scripts/teamflow.py req complete REQ-0001 --profile change
# 核对实际证据后，确认指定条件并复用验证结果
python3 scripts/teamflow.py req complete REQ-0001 --confirm-ac AC-01
```

`change` 是项目自行配置的 profile 名。需求跟踪见 [WORKFLOW](.agents/skills/ios-team-flow/references/WORKFLOW.md)，命令配置与输入绑定见 [PROJECT-CHECKS](.agents/skills/ios-team-flow/references/PROJECT-CHECKS.md)。

参数和证据复用见 [命令参考](.agents/skills/ios-team-flow/references/COMMANDS.md)。旧人工证据缺少文件快照时须重新实际核对；App 发布记录现在必须指定 Bundle ID、环境、完整 commit 和执行结果。

## 资料与工具

- [Git 动作](.agents/skills/ios-team-flow/references/GIT-ACTIONS.md) 与 [App 外部动作](.agents/skills/ios-team-flow/references/APP-RELEASE.md)。
- [已有工程](.agents/skills/ios-team-flow/references/EXISTING-PROJECT.md)；大型项目可按需启用 [模块索引](.agents/skills/ios-team-flow/references/MODULE-CONTEXT.md)。
- [本地化](.agents/skills/ios-team-flow/references/LOCALIZATION.md)、[架构](.agents/skills/ios-team-flow/references/ARCHITECTURE.md)、[日志组件](.agents/skills/ios-team-flow/references/LOGGING.md)。
- [数据迁移与恢复](.agents/skills/ios-team-flow/references/DATA-MIGRATION.md)、[敏感信息与外部服务边界](.agents/skills/ios-team-flow/references/SECURITY-BOUNDARIES.md) 按涉及范围加载。
- [源码验证与分发](.agents/skills/ios-team-flow/references/RELEASE.md)。Demo、测试和 ZIP 发布工具属于源码仓库，不进入独立 Skill 包。

## 源码仓库验证范围

本仓库按改动选择 profile（接入业务项目时自行配置）：

| 改动 | profile | 执行内容 |
| --- | --- | --- |
| 仅文档措辞或链接 | `workflow-docs` | 文档链接、版本与分发入口检查 |
| 工作流脚本、行为规则或测试 | `workflow` | 工作流完整测试，包含文档检查及包内消费测试 |
| 分发清单或正式打包 | `workflow-release` | 工作流测试及两个 ZIP 的生成 |
| Demo 业务代码 | `ios-demo` | Debug 单元/UI 与 Release 单元测试 |

例如 `python3 scripts/teamflow.py req complete REQ-0001 --profile workflow`。选择覆盖改动的一个 profile；`workflow-release` 已包含 `workflow`，无需再跑一遍。Demo 测试脚本和项目模块索引不参与工作流 profile 的输入绑定；索引维护按 MODULE-CONTEXT 专题核对。
