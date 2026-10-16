# 安装与接入

三种模式共用同一套工具和同一个 AGENTS 托管区块：iOS 原生、Godot、Godot + iOS。安装包以项目 Git 根为解压目标。

| 安装包 | 模式 | 内容 |
| --- | --- | --- |
| `teamflow-ios-v<版本>.zip` | iOS 原生 | `.agents/teamflow-core/`、`.agents/skills/iOS/` |
| `teamflow-godot-v<版本>.zip` | Godot | `.agents/teamflow-core/`、`.agents/skills/Godot/` |
| `teamflow-godot-ios-v<版本>.zip` | Godot + iOS | 核心与两个 Skill |

每个包另含对应模式的 `AGENTS.md`、命令入口 `scripts/teamflow.py`、[宿主权限](#宿主权限)配置和安装清单 `.agents/teamflow-core/references/MANIFEST.json`（升级时识别本地改动）。目录区分大小写：`iOS`、`Godot`。

## 新项目与已有项目

新项目解压即可使用，验证日志目录自带忽略规则：

```sh
unzip ~/Downloads/teamflow-ios-v1.1.0.zip -d .
python3 scripts/teamflow.py doctor
```

已有 `AGENTS.md` 或 `scripts/` 的项目不覆盖解压，再由 setup 合并托管区块：

```sh
unzip -n ~/Downloads/teamflow-ios-v1.1.0.zip -d .
python3 .agents/teamflow-core/scripts/teamflow.py setup --mode ios
```

setup 写入 AGENTS 托管区块和 `scripts/teamflow.py`，在 `.gitignore` 忽略验证日志（Godot 模式另忽略 `.godot/`），创建 `requirements/`；`--plan` 只输出 diff。它不初始化 Git、不提交，也不连接外部平台。不传 `--mode` 时沿用已有选择，首次默认 iOS 原生；所选模式缺少 Skill 时报错。

## 升级

```sh
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v1.1.1.zip --plan
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v1.1.1.zip
```

按安装清单替换未改动的核心与 Skill 文件，移除新版不再包含的文件，然后刷新入口。有本地改动时拒绝并列出文件，核对后可加 `--force`。`--mode` 同时切换模式，例如用 `teamflow-godot-ios` 包加 `--mode godot-ios` 给 Godot 项目补装 iOS Skill。`.agents/team/`、需求卡、验证配置和模块索引不触碰。已安装的项目不要用 `unzip -n` 升级。升级提交只含 TeamFlow 安装文件，不建卡，提交消息写明版本，例如“升级 TeamFlow 至 1.1.1”；与业务改动分开提交。

## 团队定制

`.agents/team/` 随项目提交，升级不覆盖：

- `RULES.md`：团队规则，入口要求 Agent 读取；可细化规范，不突破 WORKFLOW 的授权边界。
- `toolchain.json`：工具链锁定，如 `{"xcode": "26.4", "godot": "4.7.2"}`，`doctor` 按模式核对本机版本。

不要直接修改 `.agents/teamflow-core/` 或 `.agents/skills/`，改过的文件会让 upgrade 拒绝执行。

## 宿主权限

包内的 `.claude/settings.json` 与 `.codex/rules/teamflow.rules` 让 Claude Code 和 Codex 在推送、PR 创建/合并/评审/评论、GitHub Release、`xcrun altool`、`fastlane`、`butler push`、`steamcmd` 前请求人工确认。它们只兜底，授权范围仍以 WORKFLOW 为准；模板源文件在 `.agents/teamflow-core/assets/permissions/`。

- 随项目提交，团队共用；个人放行写在 `.claude/settings.local.json` 或 `~/.codex/rules/`。
- Claude Code 的 bypass permissions 模式（`--dangerously-skip-permissions`）会跳过确认，团队项目不使用。
- Codex 只在信任该项目后加载项目内 `.codex/rules/`，修改后需重启。
- 已有项目 `unzip -n` 不覆盖已有的 `.claude/settings.json`，需把模板中的 `permissions.ask` 合并进去；自建上传脚本在两个文件中追加同类规则。

## 提交前检查（可选）

```sh
python3 scripts/teamflow.py setup --git-hook change
python3 scripts/teamflow.py setup --no-git-hook
```

为本机安装运行所选 profile 的 pre-commit，支持 worktree 与项目内的 `core.hooksPath`；不覆盖非 TeamFlow 管理的 Hook，`git commit --no-verify` 可临时跳过。Hook 不随仓库提交。

## Claude Code Skill 链接

setup 追加 `--claude-skill-link` 时创建 `.claude/skills/ios` 或 `.claude/skills/godot`，可用 `/ios`、`/godot` 调用。AGENTS 路由始终有效，链接可选。

## 诊断

`python3 scripts/teamflow.py doctor` 只读核对核心、所选 Skill、AGENTS 区块、命令入口、验证配置与需求证据；Godot 模式另核对引擎版本锁定和 `.godot/` 忽略。版本只保存在 `.agents/teamflow-core/references/VERSION`。
