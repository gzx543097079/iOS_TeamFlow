# Godot 工作流扩展

Godot 4.x + GDScript 与 iOS 原生使用同一套 TeamFlow 核心，按安装模式选择入口。从 [5.0.0 Release](https://github.com/gzx543097079/iOS_TeamFlow/releases/tag/teamflow-v5.0.0) 获取对应安装包。

## 共用与分工

| 层 | 唯一来源 | 处理内容 |
| --- | --- | --- |
| 共用协作核心 | [WORKFLOW](../.agents/teamflow-core/references/WORKFLOW.md)、CHECKS、BOUNDARIES 与 TeamFlow Python 工具 | 需求、AC、状态、证据、模块索引和 Git 交付 |
| Godot 工程 | [Godot](../.agents/skills/Godot/SKILL.md) | GDScript、场景／资源、游戏 UI、玩法、性能与检查入口 |
| iOS 平台 | [Godot 与 iOS](../.agents/skills/Godot/references/IOS.md) + 原有 APP-RELEASE | 导出与原生桥接、设备验收、签名、隐私、TestFlight 和审核 |

共用核心独立放在 `.agents/teamflow-core/`，包含需求、验证、安装、模块索引与交付工具，以及共用架构、本地化规则和模板。两个 Skill 只维护各自工程规范；版本统一由核心维护。

## 接入一个项目

先在本源码仓库运行 `python3 scripts/package_release.py`，生成完整源码、原生 Skill 和 `teamflow-godot-v5.0.0.zip` 三类 ZIP 及校验文件。扩展包包含两个 Skill，自带全部共用依赖，不包含演练游戏、使用项目的数据或日志。

在目标项目 Git 根解压扩展包到 `.agents/`，确认 `teamflow-core/` 和 `skills/` 下的两个 Skill 均存在；已有核心或 Skill 先核对定制与升级差异。然后执行：

```sh
unzip ~/Downloads/teamflow-godot-v5.0.0.zip -d .agents
python3 .agents/teamflow-core/scripts/teamflow.py setup --mode godot-ios --plan
python3 .agents/teamflow-core/scripts/teamflow.py setup --mode godot-ios
```

`--mode godot-ios` 将唯一入口指向 Godot Skill，原生插件按其路由读取原生规范；`--mode ios` 选择原生入口。重复 setup 不传 mode 会沿用已选入口，首次默认原生模式。安装选择保存在 AGENTS 托管区块，不另建状态配置。Claude 可选链接按模式选择对应 Skill，详见[安装说明](../.agents/teamflow-core/references/INSTALL.md)。

项目根有 `project.godot` 或游戏位于子目录都可使用，Agent 必须先定位真实游戏根。之后统一使用 `python3 scripts/teamflow.py`。

合并[检查配置示例](../.agents/skills/Godot/assets/project-checks.example.json)，修改 `game/` 为实际目录，并提供项目真实测试脚本。项目 `.gitignore` 忽略 `.godot/` 缓存，保留场景、源资源、导入配置和持久 UID。不要覆盖已有 profile 或把示例中的空测试当作项目验收。

```sh
python3 scripts/teamflow.py req create --title "暂停后恢复本局游戏"
# 填写生成需求卡的范围与可观察 AC，再实施
python3 scripts/teamflow.py req complete REQ-YYYYMMDD-xxxx --profile godot-check --wait-user
# 实际核对对应条件后，使用 --confirm-ac AC-01 确认
```

示例编号必须替换为实际编号。Godot 自动检查通过只确认自动范围；画面、触控、声音和真机 AC 保留待用户验证。

## 本仓库验证

[演练场景](../examples/TeamFlowGame/README.md) 用两个按钮验证计分、暂停／恢复和重新进入场景。检查入口会拒绝缺失测试、引擎错误和超时，不因为进程退出 0 就忽略错误。

```sh
python3 scripts/teamflow.py req complete REQ-20261013-9a5d --profile workflow-godot-review
```

该 profile 组合工具回归、三个分发包和真实 Godot 样例测试；样例检查锁定本次机器已有的 Godot 4.7.2，其他机器需按自己的实际版本核对后调整，不自动安装或升级。

Godot iOS 导出、Xcode 最终 App、真机触控／性能和 TestFlight 尚未验证；实际游戏接入后按目标配置对应 profile。
