# 安装与接入

接入仅维护项目内的 Skill 路由和命令入口。

1. 将完整 `ios-team-flow` 目录放入项目 `.agents/skills/`。
2. 确认当前目录是项目 Git 根。
3. 执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/teamflow.py setup
```

命令生成或更新带标记的 `AGENTS.md` 区块和 `scripts/teamflow.py`，在 `.gitignore` 忽略本地验证日志，并创建 `requirements/`。它不初始化 Git、不安装 Hook、不创建 App、不提交代码，也不连接外部平台。之后统一使用 `python3 scripts/teamflow.py`。

使用 Claude Code 时可追加 `--claude-skill-link`，创建 `.claude/skills/ios-team-flow` 软链接，让 Skill 以原生方式被发现（可用 `/ios-team-flow` 调用）；AGENTS.md 路由在两种 Agent 中都有效，该软链接是可选项。

只读诊断：

```sh
python3 scripts/teamflow.py doctor
```

诊断直接核对 Skill、AGENTS 托管区块和命令入口的实际内容，不维护重复版本清单。

可选的只读预览（直接输出待修改文本的 diff，无变化时无输出）：

```sh
python3 .agents/skills/ios-team-flow/scripts/teamflow.py setup --plan
```
