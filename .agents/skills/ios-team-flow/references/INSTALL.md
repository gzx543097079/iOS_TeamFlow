# 安装与接入

接入仅维护项目内的 Skill 路由和命令入口。

1. 将完整 `ios-team-flow` 目录放入项目 `.agents/skills/`。
2. 确认当前目录是项目 Git 根。
3. 执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

脚本生成或更新带标记的 `AGENTS.md` 区块 和 `scripts/teamflow.py`，并创建 `requirements/`。它不初始化 Git、不安装 Hook、不创建 App、不提交代码，也不连接外部平台。

只读诊断：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project . --doctor
```

诊断直接核对 Skill、AGENTS 托管区块和命令入口的实际内容，不维护重复版本清单。
