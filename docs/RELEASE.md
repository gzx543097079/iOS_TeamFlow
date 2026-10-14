# 工作流源码分发

本文件只处理 TeamFlow ZIP，不处理业务 App。

发布时更新版本与 CHANGELOG；完成本次分发清单和测试变更后，源码仓库可用 `req complete REQ-20260101-a3f9 --profile workflow-release` 一次验证、打包并绑定需求证据（替换实际需求编号）。已运行该 profile 时不重复执行下面的独立命令；没有该项目配置时运行：

```sh
python3 scripts/run_workflow_checks.py
python3 scripts/package_release.py
```

输出完整仓库包，以及 `teamflow-ios`、`teamflow-godot`、`teamflow-godot-ios` 三个安装包和各自的 SHA256。完整源码包包含 Godot 演练源码；Skill 包不含 Demo、requirements、logs、Git 数据或密钥。包使用显式清单，本地打包不等于发布。Godot 接入方式参见 [扩展说明](GODOT.md)。

只有用户明确提出 Git 目标时才执行写操作。GitHub Release 目标可自动补齐验证、commit、push 和标签等最小必要前置；不执行 App Store 发布等可选或后续动作。CI 只负责发布：本地 `workflow-release` 通过并提交、推送后，推送与 `VERSION` 一致的标签 `teamflow-v<VERSION>`，[发布工作流](../.github/workflows/release.yml) 核对标签、打包并创建公开 Release。日常测试不在 CI 运行；改动日志组件或 Demo 时在 macOS 本地运行 `ios-demo` profile 与 `python3 scripts/check_logging.py`。GitHub Release 不代表 App Store 上线。

安装包以项目根为解压目标，内含对应模式的 `AGENTS.md`、`scripts/teamflow.py` 入口和打包时生成的安装清单 `MANIFEST.json`（升级时用来识别本地改动）；AGENTS 区块与 setup 使用同一份文本生成。版本读取共用核心的 `references/VERSION`。
