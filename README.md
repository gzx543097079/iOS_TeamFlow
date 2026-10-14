# TeamFlow

面向 AI Agent 驱动开发的中文工作流，支持 iOS 原生、Godot 和 Godot + iOS，面向团队分发，放入项目根目录即可使用。当前版本为 **6.0.0**。

需求、实施、验证与显式交付的规则见 [WORKFLOW](.agents/teamflow-core/references/WORKFLOW.md)；按安装模式进入 [iOS Skill](.agents/skills/iOS/SKILL.md) 或 [Godot Skill](.agents/skills/Godot/SKILL.md)。Agent 通过项目根 `AGENTS.md` 的托管区块找到所选入口，Codex 与 Claude Code 均可直接使用。

## 安装

需要 Python 3、Git。原生 iOS 构建使用 Xcode；Godot 开发使用项目指定的 Godot，导出 iOS 时还需要匹配的导出模板及 macOS + Xcode。不需要 CI 环境。

按项目类型选择安装包，从 [Releases](https://github.com/gzx543097079/iOS_TeamFlow/releases) 下载，或在本仓库运行 `python3 scripts/package_release.py` 生成到 `dist/`：

| 安装包 | 适用 | 包含 |
| --- | --- | --- |
| `teamflow-ios-v6.0.0.zip` | iOS 原生 App | 共用核心 + iOS Skill |
| `teamflow-godot-v6.0.0.zip` | Godot 游戏（不含 iOS 原生工作） | 共用核心 + Godot Skill |
| `teamflow-godot-ios-v6.0.0.zip` | Godot 游戏 + iOS 导出／原生插件 | 共用核心 + Godot 与 iOS Skill |

**新项目：解压到项目根即可使用。**

```sh
cd ~/Desktop/MyGit/MyGame        # 项目 Git 根；尚无仓库时先 git init
unzip ~/Downloads/teamflow-godot-v6.0.0.zip -d .
python3 scripts/teamflow.py doctor
```

包内已带对应模式的 `AGENTS.md` 和命令入口 `scripts/teamflow.py`，Codex 与 Claude Code 均可直接读取；验证日志目录自带忽略规则。

**已有项目**（已有 `AGENTS.md` 等文件）：用 `unzip -n` 不覆盖解压，再运行 setup 合并入口：

```sh
unzip -n ~/Downloads/teamflow-ios-v6.0.0.zip -d .
python3 .agents/teamflow-core/scripts/teamflow.py setup --mode ios
```

**升级**：用新版安装包运行 `upgrade`。工具依据安装清单替换未改动的文件；有本地改动时拒绝执行并列出这些文件。5.x 项目需要额外传 `--baseline 旧版安装包`。

```sh
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v6.0.1.zip --plan
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v6.0.1.zip
```

**团队定制**：团队规则写在 `.agents/team/RULES.md`，入口会要求 Agent 读取；工具链版本锁定写在 `.agents/team/toolchain.json`。该目录随项目提交，升级不会覆盖。不要直接修改 `.agents/teamflow-core/` 和 `.agents/skills/`。

**提交前检查（可选，每位成员在本机安装）**：

```sh
python3 scripts/teamflow.py setup --git-hook change
```

模式切换、Claude Code Skill 链接、升级细节和 Hook 规则见[安装说明](.agents/teamflow-core/references/INSTALL.md)，Godot 接入见 [Godot 说明](docs/GODOT.md)。首次使用只读取所选 Skill 和共用 WORKFLOW，其余资料按[按需读取](.agents/teamflow-core/references/WORKFLOW.md#按需读取)规则加载。

创建业务工程后，如尚无 `.agents/project-checks.json`，先生成空配置，再按 [CHECKS](.agents/teamflow-core/references/CHECKS.md) 填入真实的构建与测试命令。profile 可用 `extends` 继承另一个 profile 的输入与检查，例如“发布验证 = 日常验证 + 打包”。

```sh
python3 scripts/teamflow.py verify init
```

## 常用命令

所有命令统一从 `python3 scripts/teamflow.py` 进入，默认输出几行简短摘要，追加 `--json` 获取完整结构。

```sh
# 需求
python3 scripts/teamflow.py req create --title "登录失败提示优化"   # --bug 缺陷，--queued 排队
python3 scripts/teamflow.py req list                                 # 默认只列未完成，--all 含已完成和取消
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
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v6.0.1.zip --plan
python3 scripts/teamflow.py module inspect --query "修改登录页错误提示"
python3 scripts/teamflow.py logging install --language swift --destination App/MyApp/Sources/Support/Logging
```

`change` 是项目自行配置的 profile 名。参数、输出与证据复用见 [命令参考](.agents/teamflow-core/references/COMMANDS.md)。

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

Godot + GDScript（可选 iOS）扩展见 [接入与分工说明](docs/GODOT.md)。它与原生 Skill 共用需求和证据工具，另提供 [Godot Skill](.agents/skills/Godot/SKILL.md) 与 [演练场景](examples/TeamFlowGame/README.md)。

| 路径 | 内容 |
| --- | --- |
| `.agents/teamflow-core/` | 共用需求、验证、安装、升级与模块工具；流程、版本和模板 |
| `.agents/skills/iOS/` | 原生编码、UI、生命周期、日志与 iOS 平台规则 |
| `.agents/skills/Godot/` | Godot 工程、团队协作与 iOS 衔接规范、导入／测试入口；依赖同版核心 |
| `scripts/` | 入口、测试运行、文档校验、打包、Demo 测试 |
| `tests/` | 工具行为与包内消费测试 |
| `examples/TeamFlowDemo/` | [演练 Demo](examples/TeamFlowDemo/README.md)（UIKit + MVVM，CocoaPods） |
| `examples/TeamFlowGame/` | 最小 Godot 场景与行为测试；不包含 iOS 导出配置 |
| `docs/RELEASE.md`、`CHANGELOG.md` | [源码验证与分发](docs/RELEASE.md)、[版本记录](CHANGELOG.md) |
| `.github/workflows/release.yml` | 仅发布：推送 `teamflow-v*` 标签时打包并创建 GitHub Release |

Demo、测试和发布工具属于源码仓库，不进入独立 Skill 包。验证按下表在本地运行；CI 只负责发布，推送 `teamflow-v*` 标签后打包并创建 GitHub Release，见 [源码验证与分发](docs/RELEASE.md)。

本仓库按改动选择 profile（接入业务项目时自行配置）：

| 改动 | profile | 执行内容 |
| --- | --- | --- |
| 仅文档措辞或链接 | `workflow-docs` | 文档链接、版本与分发入口检查 |
| 工作流脚本、规则、测试或模块索引 | `workflow` | 工作流完整测试，包含文档检查及包内消费测试 |
| 分发清单或正式打包 | `workflow-release` | `extends: workflow`，另生成完整源码包与三个安装包 |
| Godot 扩展验证 | `workflow-godot-review` | `extends: workflow-release`，另运行实际 Godot 场景测试 |
| Demo 业务代码 | `ios-demo` | Debug 单元/UI 与 Release 单元测试 |

一次提交使用覆盖全部改动的 profile；现有 profile 不能覆盖混合改动时配置组合 profile，或按独立需求拆分提交。
