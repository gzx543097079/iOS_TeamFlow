# iOS TeamFlow

中文 Codex iOS 团队工作流：Apple UI 规范、Objective-C / Swift / SwiftUI 规范、需求拆分与过程追踪、提交前自动审查与去重、Release 压缩包分发。

从 [使用说明](workflow/README.md) 开始；先阅读 [UI 规范](workflow/standards/ui.md)。

本地验证与生成分发包：

```sh
python3 scripts/validate_workflow.py
python3 -m unittest discover -s tests -v
python3 scripts/package_release.py
```

分发时将 ZIP 内容合入项目 Git 根目录，包含 AGENTS.md、.agents 和 .github。工程、workflow、requirements、logs、scripts 同级。完整规则见 [工作流](workflow/WORKFLOW.md)，参考项目与官方资料见 [调研记录](workflow/SOURCES.md)。

采用项目级独立安装：使用 `ios-team-flow-skill-v1.1.0.zip`，将完整目录放入目标项目 `.agents/skills/`，再从项目根目录运行一次：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

此后直接提需求，无需每次点名 Skill。完整 Skill 与入口随项目提交，团队克隆即可获得相同版本，不需要个人安装。详见 [项目安装与接入](.agents/skills/ios-team-flow/references/INSTALL.md)。

空项目没有 `.agents/skills/` 时，先在项目根目录运行 `mkdir -p .agents/skills`，再放入完整 Skill 并执行上面的接入命令。无需提前创建 Xcode 工程；接入后先整理需求文档，确认后再创建工程。完整步骤见 [空项目接入](.agents/skills/ios-team-flow/references/INSTALL.md#空项目接入没有-agentsskills-时)。
