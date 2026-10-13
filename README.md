# iOS TeamFlow

面向 AI Agent 驱动开发的中文 iOS 工作流。当前版本为 **4.0.1**。

需求、实施、验证与显式交付的规则见 [WORKFLOW](.agents/skills/ios-team-flow/references/WORKFLOW.md)；[Skill 入口](.agents/skills/ios-team-flow/SKILL.md) 按任务加载专题。Agent 通过项目根 `AGENTS.md` 的托管区块找到 Skill，Codex 与 Claude Code 均可直接使用。

## 安装

需要 Python 3、Git；业务 App 构建还需要相应 Xcode 环境。

新项目只有空目录时，先创建并进入自己的项目根目录：

```sh
mkdir -p ~/Desktop/MyGit/MyApp
cd ~/Desktop/MyGit/MyApp
mkdir -p .agents/skills
```

先运行 `git rev-parse --show-toplevel` 核对是否已属于 Git 仓库；只有不属于任何仓库时才运行 `git init`。如果显示的是上级仓库根，改在该仓库根接入，或另选仓库外的目录，不创建嵌套仓库。已有 Git 项目直接进入其根目录，仅执行 `mkdir -p .agents/skills`。

从 [v4.0.1 Release](https://github.com/gzx543097079/iOS_TeamFlow/releases/tag/teamflow-v4.0.1) 下载独立 Skill 包 `ios-team-flow-skill-v4.0.1.zip`。例如下载到 `~/Downloads` 后，在项目根解压并接入：

```sh
unzip ~/Downloads/ios-team-flow-skill-v4.0.1.zip -d .agents/skills
python3 .agents/skills/ios-team-flow/scripts/teamflow.py setup
```

`setup` 生成或更新 `AGENTS.md` 托管区块和 `scripts/teamflow.py` 入口，在 `.gitignore` 忽略本地验证日志，并创建 `requirements/`；不创建业务 App、不提交代码。使用 Claude Code 时可追加 `--claude-skill-link`，让 Skill 以原生方式被发现（可用 `/ios-team-flow` 调用）。

确认最终路径是 `.agents/skills/ios-team-flow/SKILL.md`，不要只复制 `SKILL.md`，也不要多套一层同名目录。已有同名 Skill 时先按 [安装说明](.agents/skills/ios-team-flow/references/INSTALL.md) 核对差异和定制，再升级。**4.0.0 与 3.x 不兼容**：升级时删除旧需求卡（Git 历史保留）、移除模块索引中的 `baseline` 字段，并重新运行 `setup`。

接入后只读检查：

```sh
python3 scripts/teamflow.py doctor
```

创建业务工程后，如尚无 `.agents/project-checks.json`，按实际构建与测试命令配置验证：

```sh
python3 scripts/teamflow.py verify init
```

`verify init` 只生成空配置；按 [CHECKS](.agents/skills/ios-team-flow/references/CHECKS.md) 填入真实检查命令。profile 可用 `extends` 继承另一个 profile 的输入与检查，例如“发布验证 = 日常验证 + 打包”。

## 常用命令

所有命令统一从 `python3 scripts/teamflow.py` 进入，默认输出几行简短摘要，追加 `--json` 获取完整结构。

```sh
# 需求
python3 scripts/teamflow.py req create --title "登录失败提示优化"   # --bug 缺陷，--queued 排队
python3 scripts/teamflow.py req list
python3 scripts/teamflow.py req status REQ-20260101-a3f9            # 状态、证据有效性、剩余 AC、下一步
python3 scripts/teamflow.py req state REQ-20260101-a3f9 --state 阻塞 --blocked 待确认 --reason "等待选择登录方式"

# 验证与完成
python3 scripts/teamflow.py req complete REQ-20260101-a3f9          # 证据失效时自动选择覆盖改动的最小 profile
python3 scripts/teamflow.py req complete REQ-20260101-a3f9 --profile change
python3 scripts/teamflow.py req complete REQ-20260101-a3f9 --confirm-ac AC-01   # 核对实际证据后确认条件
python3 scripts/teamflow.py verify suggest

# 提交前
python3 scripts/teamflow.py git check REQ-20260101-a3f9

# 按需
python3 scripts/teamflow.py doctor
python3 scripts/teamflow.py module inspect --query "修改登录页错误提示"
python3 scripts/teamflow.py logging install --language swift --destination App/MyApp/Sources/Support/Logging
```

`change` 是项目自行配置的 profile 名。参数、输出与证据复用见 [命令参考](.agents/skills/ios-team-flow/references/CHECKS.md#命令参考)。

## 需求卡

需求卡位于 `requirements/`，编号形如 `REQ-20260101-a3f9`（日期 + 随机后缀），多分支并行创建不冲突。头部元数据由工具读写，正文是普通 Markdown：

```markdown
---
id: REQ-20260101-a3f9
type: feature
state: 进行中
created: 2026-01-01T10:00:00+08:00
---

# 登录失败提示优化

## 范围

登录接口返回错误时，在表单下方展示可读提示。

## 不包含

无

## 验收条件

- [ ] AC-01：密码错误时显示“账号或密码错误”

## 决策与异常
```

- 状态：🔵 进行中、🟣 待用户验证、🔴 阻塞（类型为待确认、外部或暂停）、✅ 完成、⚫ 取消。
- 完成时证据摘要（profile、结果、输入指纹、需求指纹、HEAD、时间）写入头部；验证日志只留本地，换机或删除日志后仍可按摘要复核。
- 证据只绑定“范围”“不包含”和各 AC 文字；标题、排版、勾选与决策记录可自由修改。

## 资料与工具

- [Git 动作与安全边界](.agents/skills/ios-team-flow/references/BOUNDARIES.md)、[App 外部动作](.agents/skills/ios-team-flow/references/APP-RELEASE.md)。
- [已有工程](.agents/skills/ios-team-flow/references/EXISTING-PROJECT.md)；大型项目可按需启用 [模块索引](.agents/skills/ios-team-flow/references/MODULE-CONTEXT.md)，与基线分支比较给出增量读取范围。
- [架构与数据迁移](.agents/skills/ios-team-flow/references/ARCHITECTURE.md)、[本地化](.agents/skills/ios-team-flow/references/LOCALIZATION.md)、[日志组件](.agents/skills/ios-team-flow/references/LOGGING.md)。

## 源码仓库

| 路径 | 内容 |
| --- | --- |
| `.agents/skills/ios-team-flow/` | 分发的 Skill：规则、模板、脚本与日志组件 |
| `scripts/` | 入口、测试运行、文档校验、打包、Demo 测试 |
| `tests/` | 工具行为与包内消费测试 |
| `examples/TeamFlowDemo/` | [演练 Demo](examples/TeamFlowDemo/README.md)（UIKit + MVVM，CocoaPods） |
| `docs/RELEASE.md`、`CHANGELOG.md` | [源码验证与分发](docs/RELEASE.md)、[版本记录](CHANGELOG.md) |
| `.github/workflows/teamflow.yml` | 唯一 CI：push 到 main、PR 与 `teamflow-v*` 标签触发 |

Demo、测试和发布工具属于源码仓库，不进入独立 Skill 包。CI 在 Ubuntu 运行工具测试与打包；原生日志组件与 Demo 测试仅在相关路径变化或发布标签时于 macOS 运行；标签在全部检查通过后创建 GitHub Release。

本仓库按改动选择 profile（接入业务项目时自行配置）：

| 改动 | profile | 执行内容 |
| --- | --- | --- |
| 仅文档措辞或链接 | `workflow-docs` | 文档链接、版本与分发入口检查 |
| 工作流脚本、规则、测试或模块索引 | `workflow` | 工作流完整测试，包含文档检查及包内消费测试 |
| 分发清单或正式打包 | `workflow-release` | `extends: workflow`，另生成两个 ZIP |
| Demo 业务代码 | `ios-demo` | Debug 单元/UI 与 Release 单元测试 |

一次提交只能由一个 profile 覆盖；同时改动 Demo 与工作流时按 profile 分开提交。
