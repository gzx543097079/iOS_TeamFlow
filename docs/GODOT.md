# Godot 工作流扩展

Godot 4.x + GDScript 与 iOS 原生使用同一套 TeamFlow 核心，按安装模式选择入口。纯游戏项目使用 Godot 模式；需要 iOS 导出、原生插件或上架时使用 Godot + iOS 模式。

## 共用与分工

| 层 | 唯一来源 | 处理内容 |
| --- | --- | --- |
| 共用协作核心 | [WORKFLOW](../.agents/teamflow-core/references/WORKFLOW.md)、CHECKS、COMMANDS、REPAIR、BOUNDARIES 与 TeamFlow Python 工具 | 需求、AC、状态、证据、模块索引、升级和 Git 交付 |
| Godot 工程 | [Godot](../.agents/skills/Godot/SKILL.md) | GDScript、场景／资源、游戏 UI、玩法、性能、检查入口、[团队协作](../.agents/skills/Godot/references/TEAM.md)与[游戏发布](../.agents/skills/Godot/references/RELEASE.md) |
| iOS 平台（仅 Godot + iOS） | [Godot 与 iOS](../.agents/skills/Godot/references/IOS.md) + 原有 APP-RELEASE | 导出与原生桥接、设备验收、签名、隐私、TestFlight 和审核 |

共用核心独立放在 `.agents/teamflow-core/`，包含需求、验证、安装、升级、模块索引与交付工具，以及共用的架构、本地化规则和模板。各 Skill 只维护自己的工程规范；版本统一由核心维护。

## 接入一个项目

| 安装包 | 模式 | AGENTS 入口 |
| --- | --- | --- |
| `teamflow-godot-v1.6.2.zip` | `godot` | Godot Skill，跳过 iOS 路由；不含 iOS Skill |
| `teamflow-godot-ios-v1.6.2.zip` | `godot-ios` | Godot Skill，iOS 原生插件按路由加载原生规范 |

新项目在 Git 根解压即可使用：

```sh
unzip ~/Downloads/teamflow-godot-v1.6.2.zip -d .
python3 scripts/teamflow.py setup      # 可选：在根 .gitignore 补上 .godot/
python3 scripts/teamflow.py doctor
```

已有项目用 `unzip -n` 解压，再运行 `python3 .agents/teamflow-core/scripts/teamflow.py setup --mode godot`（或 `--mode godot-ios`）合并入口。重复运行 setup 时不传 mode 会沿用已选入口；后续加入 iOS 时运行 `python3 scripts/teamflow.py upgrade teamflow-godot-ios-v1.6.2.zip --mode godot-ios`，同版本也可以这样补装 iOS Skill 并切换入口。安装选择保存在 AGENTS 托管区块中，不另建状态配置。详见[安装说明](../.agents/teamflow-core/references/INSTALL.md)。

团队协作建议先完成两件事：

```sh
mkdir -p .agents/team
echo '{"godot": "4.7.2"}' > .agents/team/toolchain.json   # 按团队实际版本
python3 scripts/teamflow.py doctor                        # 核对本机引擎与 .godot/ 忽略
```

场景归属、`.tscn` 冲突处理和导出凭据边界见[团队协作](../.agents/skills/Godot/references/TEAM.md)。

项目根有 `project.godot` 或游戏位于子目录都可使用，Agent 必须先定位真实游戏根。之后统一使用 `python3 scripts/teamflow.py`。

合并[检查配置示例](../.agents/skills/Godot/assets/project-checks.example.json)，修改 `game/` 为实际目录，并提供项目真实测试脚本。项目 `.gitignore` 忽略 `.godot/` 缓存，保留场景、源资源、导入配置和持久 UID。不要覆盖已有 profile 或把示例中的空测试当作项目验收。

```sh
python3 scripts/teamflow.py req create --title "暂停后恢复本局游戏"
# 填写生成需求卡的范围与可观察 AC，再实施
python3 scripts/teamflow.py req complete REQ-YYYYMMDD-xxxx --profile godot-check --wait-user
# 实际核对对应条件后，使用 --confirm-ac AC-01 确认
```

示例编号必须替换为实际编号。Godot 自动检查通过只确认自动范围；画面、触控、声音和真机 AC 保留待用户验证。

## 验证范围

本仓库不内置演练工程；工具与安装包回归由 `workflow` / `workflow-release` profile 覆盖，Godot 实际接入在独立试用项目中核对，记录见[内测试用记录](TRIAL.md)。导出、真机触控与性能、TestFlight 按实际项目目标配置对应 profile。
