# TeamFlow

面向 AI Agent 驱动开发的中文工作流，支持 iOS 原生和 Godot + iOS。当前版本为 **5.0.1**。

需求、实施、验证与显式交付的规则见 [WORKFLOW](.agents/teamflow-core/references/WORKFLOW.md)；按安装模式进入 [iOS Skill](.agents/skills/iOS/SKILL.md) 或 [Godot Skill](.agents/skills/Godot/SKILL.md)。Agent 通过项目根 `AGENTS.md` 的托管区块找到所选入口，Codex 与 Claude Code 均可直接使用。

## 安装

两种安装都需要 Python 3、Git。原生 iOS 构建使用 Xcode；Godot 开发使用项目指定的 Godot，导出 iOS 时还需要匹配的导出模板及 macOS + Xcode。

新项目只有空目录时，先创建并进入自己的项目根目录：

```sh
mkdir -p ~/Desktop/MyGit/MyApp
cd ~/Desktop/MyGit/MyApp
mkdir -p .agents
```

先运行 `git rev-parse --show-toplevel` 核对是否已属于 Git 仓库；只有不属于任何仓库时才运行 `git init`。如果显示的是上级仓库根，改在该仓库根接入，或另选仓库外的目录，不创建嵌套仓库。已有 Git 项目直接进入其根目录，仅执行 `mkdir -p .agents`。

### iOS 原生

安装 `teamflow-ios-v5.0.1.zip`，包含共用核心和原生 Skill。本仓库打包命令为 `python3 scripts/package_release.py`，产物在 `dist/`；例如将包放到 `~/Downloads` 后，在目标项目根执行：

```sh
unzip ~/Downloads/teamflow-ios-v5.0.1.zip -d .agents
python3 .agents/teamflow-core/scripts/teamflow.py setup --mode ios
```

### Godot + iOS

安装 `teamflow-godot-v5.0.1.zip`，包含共用核心、Godot Skill 与 iOS 平台 Skill；包同样由本仓库打包生成。目标项目根执行：

```sh
unzip ~/Downloads/teamflow-godot-v5.0.1.zip -d .agents
python3 .agents/teamflow-core/scripts/teamflow.py setup --mode godot-ios
```

游戏开发读取 Godot Skill，iOS 原生插件按需加载原生规范；详见 [Godot 接入说明](docs/GODOT.md)。从 [5.0.1 Release](https://github.com/gzx543097079/iOS_TeamFlow/releases/tag/teamflow-v5.0.1) 下载对应安装包，也可使用本仓库打包生成的文件。

安装后的目录对应：

| 安装模式 | 共用核心 | Skill 目录 |
| --- | --- | --- |
| iOS 原生 | `.agents/teamflow-core/` | `.agents/skills/iOS/` |
| Godot + iOS | `.agents/teamflow-core/` | `.agents/skills/iOS/`、`.agents/skills/Godot/` |

`setup` 生成或更新 `AGENTS.md` 托管区块和 `scripts/teamflow.py` 入口，在 `.gitignore` 忽略本地验证日志，并创建 `requirements/`。省略 `--mode` 时沿用已有选择，首次默认原生模式；已有 Godot 目录不会自动切换模式。两种模式使用同一套需求与验证工具。

使用 Claude Code 时可追加 `--claude-skill-link`，按模式创建对应 Skill 链接，可用 `/ios` 或 `/godot` 调用。

首次使用只读取所选 Skill 和共用 WORKFLOW；其余专题按实际操作和语言加载。Godot 普通玩法不预读 iOS 导出／发布资料，原生插件直接引用对应规范。平台列出可用 Skill 的元信息不代表读取全部正文；自动选择继续保留。同一会话已读且未变化的内容直接复用，只在变更、上下文缺失或进入新专题时补读必要文件。

确认共用核心在 `.agents/teamflow-core/`，原生 Skill 在 `.agents/skills/iOS/SKILL.md`，不要只复制 `SKILL.md`，也不要多套一层同名目录。已有同名 Skill 时先按 [安装说明](.agents/teamflow-core/references/INSTALL.md) 核对差异和定制，再升级。**4.0.0 与 3.x 不兼容**：升级时删除旧需求卡（Git 历史保留）、移除模块索引中的 `baseline` 字段，并重新运行 `setup`。

接入后只读检查：

从 4.x 升级到 5.0.0 时，先核对旧 Skill 的定制，将共用规则和工具迁到 `.agents/teamflow-core/`，平台 Skill 改为 `.agents/skills/iOS/` 和 `.agents/skills/Godot/`。安装包统一解压到 `.agents/`，再从核心入口运行对应模式的 setup；保留现有需求卡和项目验证配置，核对完成后移除旧路径的重复实现。setup 会迁移旧托管标记及本工具管理的 Claude 链接。

```sh
python3 scripts/teamflow.py doctor
```

创建业务工程后，如尚无 `.agents/project-checks.json`，按实际构建与测试命令配置验证：

```sh
python3 scripts/teamflow.py verify init
```

`verify init` 只生成空配置；按 [CHECKS](.agents/teamflow-core/references/CHECKS.md) 填入真实检查命令。profile 可用 `extends` 继承另一个 profile 的输入与检查，例如“发布验证 = 日常验证 + 打包”。

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

`change` 是项目自行配置的 profile 名。参数、输出与证据复用见 [命令参考](.agents/teamflow-core/references/CHECKS.md#命令参考)。

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

- [Git 动作与安全边界](.agents/teamflow-core/references/BOUNDARIES.md)、[App 外部动作](.agents/skills/iOS/references/APP-RELEASE.md)。
- [已有工程](.agents/skills/iOS/references/EXISTING-PROJECT.md)；大型项目可按需启用 [模块索引](.agents/teamflow-core/references/MODULE-CONTEXT.md)，与基线分支比较给出增量读取范围。
- [架构与数据迁移](.agents/skills/iOS/references/ARCHITECTURE.md)、[本地化](.agents/skills/iOS/references/LOCALIZATION.md)、[日志组件](.agents/skills/iOS/references/LOGGING.md)。

## 源码仓库

Godot + GDScript + iOS 扩展见 [接入与分工说明](docs/GODOT.md)。它与原生 Skill 共用需求和证据工具，另提供 [Godot Skill](.agents/skills/Godot/SKILL.md) 与 [演练场景](examples/TeamFlowGame/README.md)。

| 路径 | 内容 |
| --- | --- |
| `.agents/teamflow-core/` | 共用需求、验证、安装与模块工具；流程、版本和模板 |
| `.agents/skills/iOS/` | 原生编码、UI、生命周期、日志与 iOS 平台规则 |
| `.agents/skills/Godot/` | Godot 工程与 iOS 衔接规范、导入／测试入口；依赖同版核心 |
| `scripts/` | 入口、测试运行、文档校验、打包、Demo 测试 |
| `tests/` | 工具行为与包内消费测试 |
| `examples/TeamFlowDemo/` | [演练 Demo](examples/TeamFlowDemo/README.md)（UIKit + MVVM，CocoaPods） |
| `examples/TeamFlowGame/` | 最小 Godot 场景与行为测试；不包含 iOS 导出配置 |
| `docs/RELEASE.md`、`CHANGELOG.md` | [源码验证与分发](docs/RELEASE.md)、[版本记录](CHANGELOG.md) |
| `.github/workflows/teamflow.yml` | 唯一 CI：push 到 main、PR 与 `teamflow-v*` 标签触发 |

Demo、测试和发布工具属于源码仓库，不进入独立 Skill 包。CI 在 Ubuntu 运行工具测试与打包；原生日志组件与 Demo 测试仅在相关路径变化或发布标签时于 macOS 运行；标签在全部检查通过后创建 GitHub Release。

本仓库按改动选择 profile（接入业务项目时自行配置）：

| 改动 | profile | 执行内容 |
| --- | --- | --- |
| 仅文档措辞或链接 | `workflow-docs` | 文档链接、版本与分发入口检查 |
| 工作流脚本、规则、测试或模块索引 | `workflow` | 工作流完整测试，包含文档检查及包内消费测试 |
| 分发清单或正式打包 | `workflow-release` | `extends: workflow`，另生成三个 ZIP |
| Godot 扩展验证 | `workflow-godot-review` | `extends: workflow-release`，另运行实际 Godot 场景测试 |
| Demo 业务代码 | `ios-demo` | Debug 单元/UI 与 Release 单元测试 |

一次提交使用覆盖全部改动的 profile；现有 profile 不能覆盖混合改动时配置组合 profile，或按独立需求拆分提交。
