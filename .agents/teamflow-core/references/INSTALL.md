# 安装与接入

三种模式共用同一套工具和同一个 AGENTS 托管区块：iOS 原生、Godot、Godot + iOS。安装包以项目 Git 根为解压目标。

| 安装包 | 模式 | 内容 |
| --- | --- | --- |
| `teamflow-ios-v<版本>.zip` | iOS 原生 | `.agents/teamflow-core/`、`.agents/skills/iOS/` |
| `teamflow-godot-v<版本>.zip` | Godot | `.agents/teamflow-core/`、`.agents/skills/Godot/` |
| `teamflow-godot-ios-v<版本>.zip` | Godot + iOS | 核心与两个 Skill |

每个包另含对应模式的 `AGENTS.md`、命令入口 `scripts/teamflow.py`、可选[宿主权限模板](#宿主权限)（默认不激活）和安装清单 `.agents/teamflow-core/references/MANIFEST.json`（升级时识别本地改动）。目录区分大小写：`iOS`、`Godot`。

## 新项目与已有项目

新项目解压即可使用，验证日志目录自带忽略规则：

```sh
unzip ~/Downloads/teamflow-ios-v1.5.0.zip -d .
python3 scripts/teamflow.py doctor
```

已有 `AGENTS.md` 或 `scripts/` 的项目不覆盖解压，再由 setup 合并托管区块：

```sh
unzip -n ~/Downloads/teamflow-ios-v1.5.0.zip -d .
python3 .agents/teamflow-core/scripts/teamflow.py setup --mode ios
```

setup 写入 AGENTS 托管区块和 `scripts/teamflow.py`，在 `.gitignore` 忽略验证日志（Godot 模式另忽略 `.godot/`），创建 `requirements/`；`--plan` 只输出 diff。它不初始化 Git、不提交，也不连接外部平台。不传 `--mode` 时沿用已有选择，首次默认 iOS 原生；所选模式缺少 Skill 时报错。

## 升级

```sh
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v1.5.0.zip --plan
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v1.5.0.zip
```

按安装清单替换未改动的核心与 Skill 文件，移除新版不再包含的文件，然后刷新入口。有本地改动时拒绝并列出文件，核对后可加 `--force`。`--mode` 同时切换模式，例如用 `teamflow-godot-ios` 包加 `--mode godot-ios` 给 Godot 项目补装 iOS Skill。`.agents/team/`、需求卡、验证配置和模块索引不触碰。已安装的项目不要用 `unzip -n` 升级。升级提交只含 TeamFlow 安装文件，不建卡，提交消息写明版本，例如“升级 TeamFlow 至 1.5.0”；与业务改动分开提交。

## 团队定制

`.agents/team/` 随项目提交，升级不覆盖：

- `RULES.md`：团队规则，入口要求 Agent 读取；可细化规范，不突破 WORKFLOW 的授权边界。
- `toolchain.json`：工具链锁定，如 `{"xcode": "26.4", "godot": "4.7.2"}`，`doctor` 按模式核对本机版本。

不要直接修改 `.agents/teamflow-core/` 或 `.agents/skills/`，改过的文件会让 upgrade 拒绝执行。

## 宿主权限

默认安装不向 `.claude/settings.json` 或 `.codex/rules/teamflow.rules` 写入规则；授权边界由 WORKFLOW 约束，实际执行仍服从宿主权限。默认模式不代表命令自动放行。

需要每次外部动作都由宿主审批时，显式启用严格模式：

```sh
python3 scripts/teamflow.py permissions --mode strict --plan
python3 scripts/teamflow.py permissions --mode strict
```

模板保留在 `.agents/teamflow-core/assets/permissions/`，涵盖推送、PR 写操作、Release 和上传。已有自定义配置时整次启用拒绝写入，需人工合并；不会覆盖或追加重复规则。

旧版迁移或停用严格模式：

```sh
python3 scripts/teamflow.py permissions --mode default --plan
python3 scripts/teamflow.py permissions --mode default
```

只删除与模板逐字节一致的两个文件；含用户修改的文件完整保留并列出，需人工核对。`--plan` 不写文件。普通 setup 和 upgrade 不改宿主权限，升级发现现有文件时提示显式迁移；`--force` 也不覆盖这些自定义配置。

Codex 的 `prompt` 规则需要可交互的审批策略（如 `on-request`）；与 `never` 组合可能直接拒绝。聊天授权不等于工具审批。修改项目规则后需重启宿主以加载新配置，不承诺解除当前会话限制；Claude Code 也以当前宿主权限模式为准。

升级不自动重写项目验证配置。启用逐项触发需配置 check covers 与完整 inputs；Release 放入 manual profile。旧单个大脚本仍整段执行，详见 [验证配置](CHECKS.md)。

## 提交前检查（可选）

```sh
python3 scripts/teamflow.py setup --git-hook
python3 scripts/teamflow.py setup --no-git-hook
```

为本机安装 pre-commit，复核覆盖暂存内容且仍有效的已绑定需求证据（自动证据或仅含文档的人工证据，不限定 profile；优先核对本次暂存与进行中的卡）；检查源码指纹、暂存快照和实际通过 checks 的覆盖，找不到覆盖整个暂存区的有效证据时拒绝并提示验收命令，不执行测试，支持 worktree 与项目内的 `core.hooksPath`；不覆盖非 TeamFlow 管理的 Hook，`git commit --no-verify` 可临时跳过。Hook 不随仓库提交。升级核心不会自动替换本机旧 Hook（1.2 及更早的 Hook 带 `--profile`，仍可运行）；`doctor` 提示旧版时，核对后重执行 `setup --git-hook` 迁移。轻量无卡修改不会凭扩展名自动放行：钩子识别到仅文档暂存时提示核对后用 `git commit --no-verify` 提交。TeamFlow 源码仓库只管理钩子，不写入托管入口。

`AGENTS.md` 只在托管区块之外的项目规则未改动时视为安装文件；`.claude/settings.json` 与 `.codex/rules/teamflow.rules` 只在与原版模板一致时视为安装文件。项目自己的规则与权限改动须由验证 profile 覆盖。

## Claude Code Skill 链接

setup 追加 `--claude-skill-link` 时创建 `.claude/skills/ios` 或 `.claude/skills/godot`，可用 `/ios`、`/godot` 调用。AGENTS 路由始终有效，链接可选。

## 诊断

`python3 scripts/teamflow.py doctor` 只读核对核心、所选 Skill、AGENTS 区块、命令入口、验证配置与需求证据；Godot 模式另核对引擎版本锁定和 `.godot/` 忽略。版本只保存在 `.agents/teamflow-core/references/VERSION`。
