# 安装与接入

安装明确选择 iOS 原生或 Godot + iOS；两者共用工具，维护同一个 AGENTS 托管区块。已有工程升级时先核对 Skill 定制，不直接覆盖。

接入仅维护项目内的 Skill 路由和命令入口。已有旧结构时，先核对旧目录中的定制，将共用文件迁入核心、保留平台专属文件，再按新包结构接入；不保留两份共用脚本或 VERSION。需求卡与项目验证配置继续沿用，不为目录迁移清空它们。

1. 准备对应安装包。两种安装都包含 `teamflow-core/`；iOS 原生包含 `skills/iOS/`，Godot + iOS 另外包含 `skills/Godot/`。解压目标是项目 `.agents/`，不要将整个包解压到 `.agents/skills/`。
2. 确认当前目录是项目 Git 根。
3. 按安装模式执行对应命令：

```sh
# iOS 原生
unzip ~/Downloads/teamflow-ios-v5.0.2.zip -d .agents
python3 .agents/teamflow-core/scripts/teamflow.py setup --mode ios
# Godot + iOS（已安装核心及两个 Skill）
unzip ~/Downloads/teamflow-godot-v5.0.2.zip -d .agents
python3 .agents/teamflow-core/scripts/teamflow.py setup --mode godot-ios
```

命令生成或更新带标记的 `AGENTS.md` 区块和 `scripts/teamflow.py`，在 `.gitignore` 忽略本地验证日志，并创建 `requirements/`。它不初始化 Git、不安装 Hook、不创建 App、不提交代码，也不连接外部平台。之后统一使用 `python3 scripts/teamflow.py`。

上述包由源码仓库的 `python3 scripts/package_release.py` 生成，文件名中的版本以核心 VERSION 为准。目录区分大小写：原生 Skill 为 `iOS`，游戏 Skill 为 `Godot`；命令参数仍是小写 `ios` 和 `godot-ios`。现有安装先核对定制与差异，不直接覆盖解压。

不传 `--mode` 时沿用 AGENTS 中已有选择，首次默认 iOS 原生。切换模式使用明确参数；Godot 模式缺少扩展时会报错，不降级为原生模式。原生模式不会因残留 Godot 目录自动切换。

setup 在托管区块写入首次读取边界，完整规则见 [WORKFLOW](WORKFLOW.md#按需读取)。已有项目更新核心和 Skill 后重新运行 setup 即可；模式、需求卡、项目检查配置及自有说明沿用。

使用 Claude Code 时可追加 `--claude-skill-link`：iOS 原生创建 `.claude/skills/ios`，Godot + iOS 创建 `.claude/skills/godot`，对应 `/ios` 或 `/godot`。切换模式会同步本工具创建的标准链接，非标准链接和用户自有文件不删除；目标存在冲突时先报错。AGENTS 路由始终有效，软链接可选。

只读诊断：

```sh
python3 scripts/teamflow.py doctor
```

诊断直接核对共用核心、所选 Skill、AGENTS 托管区块和命令入口的实际内容，不维护重复版本清单。VERSION 只保留在 `.agents/teamflow-core/references/VERSION`，两个 Skill 不各自复制。

可选的只读预览（直接输出待修改文本的 diff，无变化时无输出）：

```sh
python3 .agents/teamflow-core/scripts/teamflow.py setup --mode ios --plan
# 或 --mode godot-ios --plan
```
