# 安装与接入

本版本只支持全新 vNext 接入，不迁移旧版数据或入口。

1. 将完整 `ios-team-flow` 目录放入项目 `.agents/skills/`。
2. 确认当前目录是项目 Git 根。
3. 执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

脚本生成或更新带标记的 `AGENTS.md` 区块、`.agents/teamflow.json` 和 `scripts/teamflow.py`，并创建 `requirements/`。它不初始化 Git、不安装 Hook、不创建 App、不提交代码，也不连接外部平台。

只读诊断：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project . --doctor
```

检测到旧 schema 时脚本停止。要采用 3.0.0，应在新项目或明确清理旧托管入口后重新接入；历史需求和日志可作为只读资料保留，但新工具不会解析。
