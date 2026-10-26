# 安装与接入

三种模式共用同一套工具和同一个 AGENTS 托管区块：iOS 原生、Godot、Godot + iOS。推荐用命令一键接入，不必人工把 ZIP 整包解压进项目根。

| 安装包 | 模式 | 内容 |
| --- | --- | --- |
| `teamflow-ios-v<版本>.zip` | iOS 原生 | `.agents/teamflow-core/`、`.agents/skills/iOS/` |
| `teamflow-godot-v<版本>.zip` | Godot | `.agents/teamflow-core/`、`.agents/skills/Godot/` |
| `teamflow-godot-ios-v<版本>.zip` | Godot + iOS | 核心与两个 Skill |

每个包另含根目录 `install_teamflow.py`、对应模式的 `AGENTS.md`、命令入口 `scripts/teamflow.py`、可选[宿主权限模板](#宿主权限)（默认不激活）和安装清单 `.agents/teamflow-core/references/MANIFEST.json`。目录区分大小写：`iOS`、`Godot`。Agent 接入与迁移总步骤写在仓库根 README；命令细节以本文件为准。

## 一键安装（推荐）

在业务项目 Git 根、已下载安装包时：

```sh
unzip -p ~/Downloads/teamflow-ios-v1.6.6.zip install_teamflow.py | python3 - ~/Downloads/teamflow-ios-v1.6.6.zip --mode ios
# 项目内已有 scripts/teamflow.py 时也可用：
python3 scripts/teamflow.py install ~/Downloads/teamflow-ios-v1.6.6.zip --mode ios
```

`install` 写入核心与所选 Skill、刷新 AGENTS 入口与 `scripts/teamflow.py`、创建 `requirements/`、忽略验证日志，并在缺失时生成验证资产（不覆盖已有文件）：

- 共用：`.agents/project-checks.json`
- iOS：另生成 `.agents/design-tokens.json`、`scripts/check_debug.py`、`scripts/check_release.py`
- Godot / Godot+iOS：从 Godot 示例生成 `project-checks.json`

iOS 首次跑检查前写入 `.agents/team/ios-verify.json`（如 `{"scheme":"YourScheme"}`）或设置 `TEAMFLOW_IOS_SCHEME`。生成的日常 profile 已按「编译 + 设计变量 + manual 全量/Release」拆分，勿再改回单脚本全量。`--plan` 只预览；已安装时拒绝，需升级用 `upgrade`，或显式 `--force` 覆盖安装文件后重新接入。

## setup

已解压或仅需刷新入口时：

```sh
python3 scripts/teamflow.py setup --mode ios
python3 scripts/teamflow.py verify init   # 仅补生成缺失的验证资产
```

setup 合并 AGENTS 托管区块、写入入口与 `.gitignore`、创建 `requirements/`，并调用与 `install` 相同的验证资产生成逻辑。不传 `--mode` 时沿用已有选择，首次默认 iOS 原生；所选模式缺少 Skill 时报错。不初始化 Git、不提交、不连接外部平台。

## 升级

```sh
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v1.6.6.zip --plan
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v1.6.6.zip
```

按安装清单替换未改动的核心与 Skill 文件，移除新版不再包含的文件，然后刷新入口。有本地改动时拒绝并列出文件，核对后可加 `--force`。`--mode` 同时切换模式。`.agents/team/`、需求卡、验证配置和模块索引不触碰。不要用 `unzip -n` 升级。升级提交只含 TeamFlow 安装文件，不建卡，提交消息写明版本；与业务改动分开提交。输出“验证配置待迁移”或 `doctor` 报告「验证配置形态」时，Agent 须按仓库 README「验证配置迁移」在同一次升级任务中建卡迁移，细则见 [CHECKS-CONFIG](CHECKS-CONFIG.md#从全量脚本迁移)；用户明确暂缓时在卡中记录原因。

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

升级不自动重写项目验证配置；旧单个大脚本仍整段执行，需按上方升级规则迁移，详见[验证配置](CHECKS-CONFIG.md#从全量脚本迁移)。

## 提交前检查（可选）

```sh
python3 scripts/teamflow.py setup --git-hook
python3 scripts/teamflow.py setup --no-git-hook
```

为本机安装 pre-commit，复核覆盖暂存内容且仍有效的已绑定需求证据（自动证据或仅含文档的人工证据，不限定 profile；优先核对本次暂存与进行中的卡）；检查源码指纹、暂存快照和实际通过 checks 的覆盖，找不到覆盖整个暂存区的有效证据时拒绝并提示验收命令，不执行测试，支持 worktree 与项目内的 `core.hooksPath`；不覆盖非 TeamFlow 管理的 Hook，`git commit --no-verify` 可临时跳过。Hook 不随仓库提交。升级核心不会自动替换本机旧 Hook（1.2 及更早的 Hook 带 `--profile`，仍可运行）；`doctor` 提示旧版时，核对后重执行 `setup --git-hook` 迁移。轻量无卡修改的暂存只含 `.md`/`.rst` 文档（不含需求卡）时直接放行，无需 `--no-verify`；`.txt` 可能是依赖清单等工程输入，仍须证据。TeamFlow 源码仓库只管理钩子，不写入托管入口。

`AGENTS.md` 只在托管区块之外的项目规则未改动时视为安装文件；`.claude/settings.json` 与 `.codex/rules/teamflow.rules` 只在与原版模板一致时视为安装文件。项目自己的规则与权限改动须由验证 profile 覆盖。

## Claude Code Skill 链接

setup 追加 `--claude-skill-link` 时创建 `.claude/skills/ios` 或 `.claude/skills/godot`，可用 `/ios`、`/godot` 调用。AGENTS 路由始终有效，链接可选。

## 诊断

`python3 scripts/teamflow.py doctor` 只读核对核心、所选 Skill、AGENTS 区块、命令入口、验证配置与需求证据；Godot 模式另核对引擎版本锁定和 `.godot/` 忽略。版本只保存在 `.agents/teamflow-core/references/VERSION`。
