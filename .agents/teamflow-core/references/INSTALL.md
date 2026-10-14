# 安装与接入

安装时从三种模式中选一种：iOS 原生、Godot、Godot + iOS。三者共用同一套工具，维护同一个 AGENTS 托管区块。安装包以项目根为解压目标，新项目解压即可使用；已有项目用不覆盖的方式解压，再运行 setup 合并入口。

## 安装包

| 安装包 | 模式 | 内容 |
| --- | --- | --- |
| `teamflow-ios-v<版本>.zip` | iOS 原生 | `.agents/teamflow-core/`、`.agents/skills/iOS/` |
| `teamflow-godot-v<版本>.zip` | Godot | `.agents/teamflow-core/`、`.agents/skills/Godot/` |
| `teamflow-godot-ios-v<版本>.zip` | Godot + iOS | 核心与两个 Skill |

每个包另含：对应模式的 `AGENTS.md`、命令入口 `scripts/teamflow.py`，以及安装清单 `.agents/teamflow-core/references/MANIFEST.json`（升级时用来识别本地改动）。这些包由源码仓库的 `python3 scripts/package_release.py` 生成，文件名中的版本以核心 VERSION 为准。目录区分大小写：原生 Skill 为 `iOS`，游戏 Skill 为 `Godot`。

## 新项目

先确认当前目录是项目 Git 根（`git rev-parse --show-toplevel`），然后解压到项目根：

```sh
unzip ~/Downloads/teamflow-godot-v6.0.0.zip -d .
python3 scripts/teamflow.py doctor
```

解压后入口即可使用，无需 setup。验证日志目录 `logs/project-checks/` 自带忽略规则，不依赖根 `.gitignore`。Godot 编辑器创建工程时通常会自带忽略 `.godot/` 的 `.gitignore`；`doctor` 会报告未忽略缓存的游戏根，运行一次 setup 即可补上。

## 已有项目

已有 `AGENTS.md`、`scripts/` 的项目，用 `-n` 解压，不覆盖已有文件，再由 setup 合并托管区块：

```sh
unzip -n ~/Downloads/teamflow-ios-v6.0.0.zip -d .
python3 .agents/teamflow-core/scripts/teamflow.py setup --mode ios --plan
python3 .agents/teamflow-core/scripts/teamflow.py setup --mode ios
```

setup 生成或更新带标记的 `AGENTS.md` 区块和 `scripts/teamflow.py`，在 `.gitignore` 忽略本地验证日志（Godot 模式另外忽略 `.godot/`），并创建 `requirements/`。它不初始化 Git、不创建 App、不提交代码，也不连接外部平台；只有显式传 `--git-hook` 才安装本机 Hook。`--plan` 只输出待修改内容的 diff，无变化时无输出。

不传 `--mode` 时沿用 AGENTS 中已有的选择，首次默认 iOS 原生。切换模式要显式传参；所选模式缺少对应 Skill 时报错，不会降级到其他模式。原生模式不会因为残留 Godot 目录而自动切换。

已安装 TeamFlow 的项目不要用 `unzip -n` 升级（已有文件不会被替换），改用下文的 upgrade。

## 升级

```sh
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v6.0.1.zip --plan
python3 scripts/teamflow.py upgrade ~/Downloads/teamflow-ios-v6.0.1.zip
```

upgrade 只替换当前模式需要的核心和 Skill 文件。处理规则：

- 依据安装清单判断文件是否被本地改过：未改动的直接替换，新版不再包含的旧文件同时移除。
- 有本地改动时拒绝升级并列出这些文件；核对后可加 `--force` 覆盖。
- 安装包缺少当前模式所需的 Skill 时拒绝；版本低于已安装版本时，需要 `--force` 才能降级。
- 完成后用新核心刷新入口，模式保持不变；传 `--mode` 可同时切换模式，例如用 `teamflow-godot-ios` 包和 `--mode godot-ios` 给 Godot 项目补装 iOS Skill。切换到依赖更少的模式时，原模式独有且未改动的文件会被移除。
- `.agents/team/`、需求卡、`.agents/project-checks.json` 和模块索引都不触碰。

5.x 项目没有安装清单，核心里也没有 upgrade 命令：先从新包取出核心脚本运行，并传入旧版安装包作为对照：

```sh
unzip ~/Downloads/teamflow-godot-ios-v6.0.0.zip '.agents/teamflow-core/scripts/*' -d /tmp/teamflow6
python3 /tmp/teamflow6/.agents/teamflow-core/scripts/teamflow.py upgrade ~/Downloads/teamflow-godot-ios-v6.0.0.zip \
  --baseline ~/Downloads/teamflow-godot-v5.0.3.zip
```

5.x 的 `teamflow-godot` 包含 iOS，对应 6.x 的 `teamflow-godot-ios`。新的 `teamflow-godot` 只含 Godot，用于纯 Godot 项目。

## 团队定制

团队自己的约定放在 `.agents/team/`，随项目提交，升级不会覆盖：

| 文件 | 作用 |
| --- | --- |
| `.agents/team/RULES.md` | 团队规则；入口要求 Agent 在该文件存在时一并读取。可细化编码、命名与流程，但不突破 WORKFLOW 的授权边界 |
| `.agents/team/toolchain.json` | 工具链锁定，如 `{"godot": "4.7.2"}`；`doctor` 与 Godot 检查按它核对本机引擎 |

不要直接修改 `.agents/teamflow-core/` 或 `.agents/skills/` 中的文件；直接改过的文件会让 upgrade 拒绝执行，需要逐个核对。

## 提交前检查（可选）

不使用 CI 时，每位成员可以在本机安装 pre-commit，提交前运行一个快速 profile：

```sh
python3 scripts/teamflow.py setup --git-hook change
python3 scripts/teamflow.py setup --no-git-hook
```

Hook 按 Git 实际解析的位置安装，支持 worktree，也支持指向项目内的 `core.hooksPath`；`core.hooksPath` 指向项目外的共享目录时拒绝安装。已有非 TeamFlow 管理的 pre-commit 时不覆盖，`--no-git-hook` 也只移除 TeamFlow 管理的 Hook。所选 profile 必须已经配置。Hook 检查的是工作区当前内容；`git commit --no-verify` 可临时跳过。Hook 不随仓库提交，每位成员自行选择是否安装。

## Claude Code

可追加 `--claude-skill-link`：iOS 原生创建 `.claude/skills/ios`，Godot 与 Godot + iOS 创建 `.claude/skills/godot`，分别对应 `/ios` 或 `/godot`。切换模式时会同步本工具创建的标准链接，非标准链接和用户自有文件不删除；目标存在冲突时先报错。AGENTS 路由始终有效，软链接可选。

## 诊断

```sh
python3 scripts/teamflow.py doctor
```

`doctor` 只读，直接核对共用核心、所选 Skill、AGENTS 托管区块和命令入口的实际内容，不维护重复的版本清单。Godot 模式另外核对引擎版本锁定和 `.godot/` 忽略；已安装托管 Hook 时核对其 profile 是否存在。VERSION 只保存在 `.agents/teamflow-core/references/VERSION`，两个 Skill 不各自复制。
