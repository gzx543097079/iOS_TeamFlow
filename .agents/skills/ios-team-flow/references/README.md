# iOS TeamFlow 中文工作流

可放入项目 Git 根目录的 Codex 团队工作流，支持 OC、Swift、SwiftUI，先定义 UI 基线，再完成需求追踪、代码生成、改动审查与版本分发。

## 快速使用

把压缩包内部文件合入项目根目录（包含隐藏目录），在 Codex 打开该根目录。已有同名文件先合并；保留完整 Skill 和项目入口。详细说明见 [分发与发布](RELEASE.md)。

然后直接说：

> 给我做一个订阅管理页，包含当前套餐、续费时间和恢复购买。

Codex 会建需求卡、判断拆分、读取 UI / 对应语言规范，实施并记录过程，提交前审查当前改动。新产品则先整理 PRD 草案交团队确认，再生成工程。也可显式调用 `$ios-team-flow`。

## 内容导航

| 内容 | 入口 |
| --- | --- |
| UI 标准（Apple 来源与团队约定） | [UI 规范](standards/ui.md) |
| 需求处理、拆分与状态 | [工作流](WORKFLOW.md) |
| Objective-C / Swift / SwiftUI | [OC](standards/objective-c.md) · [Swift](standards/swift.md) · [SwiftUI](standards/swiftui.md) |
| 业务构建与测试入口 | [配置与执行](PROJECT-CHECKS.md) |
| 需求与交付状态 | [交付追踪](DELIVERY.md) |
| 可选 Hook 与 PR 范围检查 | [Git 检查](GIT-CHECKS.md) |
| 提交审查及去重 | [Review](REVIEW.md) |
| 已有项目增量开发 | [处理流程](EXISTING-PROJECT.md) · [项目现状模板](templates/project-context.md) |
| 新项目 PRD 与需求卡 | [PRD 模板](templates/new-project.md) · [需求模板](templates/requirement.md) |
| GitHub 对比与官方来源 | [调研记录](SOURCES.md) |
| ZIP 与 GitHub Release | [发布规程](RELEASE.md) |

## 自动化边界

Codex 依据入口自动执行流程和语义审查；脚本提供可验证的暂存指纹与门禁。普通 Git 客户端需将 check 命令接入现有 pre-commit hook 才有拦截；没有 AI 的 hook 不会生成代码审查意见。工作流工具只依赖 Python 3.10+ 与 Git，实际 App 构建仍需匹配的 macOS/Xcode 与工程配置。

需求和日志可随项目提交；发布 zip 排除 App、需求和日志等项目数据。已配置 GitHub Actions 校验与 Release 附件上传，需推送后才在 GitHub 生效。

## 项目级独立安装（v1.3.0）

使用 `ios-team-flow-skill-v1.3.0.zip`，将完整 ios-team-flow 目录放入目标项目 `.agents/skills/`，再在项目根目录运行一次 `python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .`。之后直接提 iOS 需求；规则与版本随项目提交，不需要个人安装。详细步骤见 [项目安装说明](INSTALL.md)。

空项目先创建并进入项目文件夹，再创建 Skill 目录（将 MyApp 替换为你的项目目录名；已有文件夹直接进入）：

```sh
mkdir -p ~/Desktop/MyGit/MyApp
cd ~/Desktop/MyGit/MyApp
mkdir -p .agents/skills
```

然后放入完整 Skill 并执行上面的接入命令。在 Codex 打开项目根目录，不需要预先生成 iOS 工程，先确认需求文档再创建。逐步操作见 [空项目接入](INSTALL.md#空项目接入没有-agentsskills-时)。
