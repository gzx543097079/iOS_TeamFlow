# 工作流源码分发

本文件只处理 TeamFlow ZIP，不处理业务 App。

更新版本、CHANGELOG、分发清单和测试后运行：

```sh
python3 scripts/run_workflow_checks.py --full
python3 scripts/package_release.py
```

输出完整仓库包和独立 Skill 包及 SHA256。包使用显式清单，不包含 App、requirements、logs、releases、Git 数据或密钥。本地打包不等于发布。

只有用户明确提出 Git 目标时才执行写操作。GitHub Release 目标可自动补齐验证、commit、push 和标签等最小必要前置；不执行 App Store 发布等可选或后续动作。正式 Release 工作流在验证通过后创建草稿、上传附件并公开；GitHub Release 不代表 App Store 上线。
