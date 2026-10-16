# TeamFlow

面向 AI Agent 驱动开发的中文工作流，支持 iOS 原生、Godot 和 Godot + iOS，供小团队在 Codex 与 Claude Code 中共用。当前版本为 **1.1.0**。

需求、实施、验证与交付规则见 [WORKFLOW](.agents/teamflow-core/references/WORKFLOW.md)；按安装模式进入 [iOS Skill](.agents/skills/iOS/SKILL.md) 或 [Godot Skill](.agents/skills/Godot/SKILL.md)。Agent 通过项目根 `AGENTS.md` 的托管区块找到入口。

## 安装

需要 Python 3 与 Git。原生 iOS 使用 Xcode；Godot 使用项目指定版本，导出 iOS 另需导出模板与 Xcode。

| 安装包 | 适用 | 包含 |
| --- | --- | --- |
| `teamflow-ios-v1.1.0.zip` | iOS 原生 App | 共用核心 + iOS Skill |
| `teamflow-godot-v1.1.0.zip` | Godot 游戏（不含 iOS 原生工作） | 共用核心 + Godot Skill |
| `teamflow-godot-ios-v1.1.0.zip` | Godot 游戏 + iOS 导出／原生插件 | 共用核心 + Godot 与 iOS Skill |

从 [Releases](https://github.com/gzx543097079/iOS_TeamFlow/releases) 下载，或在本仓库运行 `python3 scripts/package_release.py` 生成到 `dist/`。新项目在 Git 根解压即可使用：

```sh
unzip ~/Downloads/teamflow-ios-v1.1.0.zip -d .
python3 scripts/teamflow.py doctor
python3 scripts/teamflow.py verify init     # 生成空验证配置，再按 CHECKS 填入真实构建与测试命令
```

包内带对应模式的 `AGENTS.md`、命令入口 `scripts/teamflow.py`，以及 Claude Code 与 Codex 的权限配置：推送、PR、Release 与上传类命令执行前须人工确认。已有项目、升级、团队定制、[宿主权限](.agents/teamflow-core/references/INSTALL.md#宿主权限)与提交前 Hook 见[安装说明](.agents/teamflow-core/references/INSTALL.md)，Godot 接入见 [Godot 说明](docs/GODOT.md)。

## 常用命令

统一从 `python3 scripts/teamflow.py` 进入，默认输出简短摘要，追加 `--json` 获取完整结构。

```sh
# 需求
python3 scripts/teamflow.py req create --title "登录失败提示优化"   # --bug 缺陷，--queued 排队
python3 scripts/teamflow.py req list                                 # 默认只列未完成，--all 含全部
python3 scripts/teamflow.py req status REQ-20260101-a3f9            # 状态、证据有效性、剩余 AC、下一步

# 验证与完成
python3 scripts/teamflow.py req complete REQ-20260101-a3f9 --profile change
python3 scripts/teamflow.py req complete REQ-20260101-a3f9 --confirm-ac AC-01      # Agent 按实际证据确认
python3 scripts/teamflow.py req complete REQ-20260101-a3f9 --user-confirmed AC-02  # 记录用户确认

# 提交与 PR
python3 scripts/teamflow.py git check REQ-20260101-a3f9
python3 scripts/teamflow.py req pr REQ-20260101-a3f9
python3 scripts/teamflow.py git ci --base origin/main
```

`change` 是项目自行配置的 profile 名。参数与证据复用见[命令参考](.agents/teamflow-core/references/COMMANDS.md)。

## 需求卡

需求卡位于 `requirements/`，编号形如 `REQ-20260101-a3f9`。头部元数据由工具读写，正文是普通 Markdown：范围、不包含、验收条件（`- [ ] AC-01：条件`）与决策与异常。

- 状态：🔵 进行中、🟣 待用户验证、🔴 阻塞、✅ 完成、⚫ 取消。
- 完成时证据摘要写入头部；验证日志只留本地，换机后仍可按摘要复核。
- 证据只绑定“范围”“不包含”和各 AC 文字，标题、排版、勾选与决策记录可自由修改。

跨需求仍有效的结论更新到已有项目资料，由 `PROJECT-CONTEXT.md` 按需索引；读取与失效处理见[项目现状模板](.agents/teamflow-core/references/templates/project-context.md)。不另建记忆文件，不在每个任务加载全部历史。

## 源码仓库

| 路径 | 内容 |
| --- | --- |
| `.agents/teamflow-core/` | 共用流程、需求与验证工具、安装与升级、权限模板 |
| `.agents/skills/iOS/` | 原生编码、UI、生命周期、日志与 iOS 平台规则 |
| `.agents/skills/Godot/` | Godot 工程、团队协作、测试、游戏发布与 iOS 衔接 |
| `scripts/`、`tests/` | 入口、测试运行、文档校验、打包；工具与安装包回归 |
| `docs/` | [源码验证与分发](docs/RELEASE.md)、[Godot 说明](docs/GODOT.md)、[内测试用记录](docs/TRIAL.md) |
| `.github/workflows/release.yml` | 推送 `teamflow-v*` 标签时打包并创建 GitHub Release |

本仓库按改动选择 profile：

| 改动 | profile | 执行内容 |
| --- | --- | --- |
| 仅文档措辞或链接 | `workflow-docs` | 文档链接、版本与分发入口检查 |
| 工作流脚本、规则或测试 | `workflow` | 完整工具测试，含文档检查与安装包消费测试 |
| 分发清单或正式打包 | `workflow-release` | `extends: workflow`，另生成源码包与三个安装包 |

日志组件改动另在 macOS 运行 `python3 scripts/check_logging.py`。版本记录见 [CHANGELOG](CHANGELOG.md)，第三方来源见[第三方说明](.agents/teamflow-core/references/THIRD-PARTY.md)。
