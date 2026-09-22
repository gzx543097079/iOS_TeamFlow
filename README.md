# iOS TeamFlow

面向单人开发者与 Codex 的中文 iOS 工作流。当前版本为 **3.0.1**。

核心路径只有：需求分析 → 一张需求卡 → 实施 → 一次验证 → 完成。需求完成不会自动触发 commit、push、PR、TestFlight、App Store 审核或发布。用户明确目标动作后，工作流会自动补齐该目标不可缺少的前置步骤，但不会执行可选配置或目标之后的动作。

## 安装

需要 Python 3.10+、Git，以及业务 App 对应的 macOS/Xcode。把完整 Skill 放到项目：

```text
.agents/skills/ios-team-flow/
```

然后从项目 Git 根执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

它生成 `AGENTS.md` 托管区块、`.agents/teamflow.json` 和 `scripts/teamflow.py`，并创建 `requirements/`。3.0.0 是断代版本，不迁移旧卡片、delivery、review receipt 或旧 CLI；已有旧接入项目应在新分支或新项目中重新接入。

## 日常使用

```sh
# 新需求
python3 scripts/teamflow.py req create --title "登录失败提示优化"

# 查看需求
python3 scripts/teamflow.py req list

# 运行项目验证
python3 scripts/teamflow.py verify run --profile change

# AC 完成后收尾
python3 scripts/teamflow.py req complete REQ-0001 --result logs/project-checks/运行编号/result.json
```

问答、审计和只读检查不建需求。Bug 使用 `req create --bug`。需求卡只记录范围、不包含内容、AC、验证证据，以及实际发生的重要决定或异常。

需求卡和需求列表（`req list`）使用固定彩色图标：`⚪` 待处理/尚未完成、`🟡` 待确认、`🔵` 进行中/部分完成、`🟣` 待用户验证、`✅` 完成/通过、`🔴` 阻塞、`🟠` 暂停、`⚫` 取消。AC 行以 `⚪` 或 `✅` 标识单项进度，列表显示 `⚪ 0/N`、`🔵 M/N` 或 `✅ N/N`。

有实现与交付的任务按“完成全部改动 → 环境预检 → 针对性测试 → 文件冻结 → 一次完整验证 → 目标交付”执行。完整验证只在输入冻结后运行；其后若代码、测试、文档、配置或版本变化，必须重新冻结并验证，不能复用失效证据。

## 显式动作边界

- “提交代码”只授权 commit，不包含 push。
- “推送”不包含 PR。
- “创建 PR”不包含合并。
- 发布当前 GitHub Release 时，可自动补齐验证、commit、push 和标签等必要前置；不触发 App Store 发布。
- “准备 TestFlight/提审”只做只读检查。
- Archive、TestFlight 上传、测试分发、Beta App Review、App Store 审核、发布、分阶段发布和下架互不授权。
- 普通 TestFlight 上传默认省略 `testFlightInternalTestingOnly`；只有明确要求 TestFlight Internal Only 时才启用。
- 用户可在一句话中明确列出多个动作；只执行列出的动作。

TestFlight 上传准备示例（均为只读，不会实际上传）：

```sh
# 普通上传：不写入 testFlightInternalTestingOnly
python3 scripts/teamflow.py release prepare upload-testflight --version 1.2.0 --build 123

# 只有用户明确要求仅内部测试时才使用
python3 scripts/teamflow.py release prepare upload-testflight --version 1.2.0 --build 123 --testflight-internal-only
```

具体规则见 [WORKFLOW](.agents/skills/ios-team-flow/references/WORKFLOW.md)、[Git 动作](.agents/skills/ios-team-flow/references/GIT-ACTIONS.md) 和 [App 外部动作](.agents/skills/ios-team-flow/references/APP-RELEASE.md)。

## 工程能力

- Objective-C、Swift、SwiftUI 和 UI 规范按改动加载。
- 新 App 使用精简启动模板；功能与发布资料分阶段加载。
- 已有大型工程可用模块索引执行增量读取。
- 构建和测试命令保存在 `.agents/project-checks.json`，真实输出保存到 `logs/project-checks/`。
- 新工程可按需接入内置分级日志组件与 Scene 生命周期规范。

源码仓库的 Demo、测试和 ZIP 发布工具不进入独立 Skill 包。分发说明见 [RELEASE](.agents/skills/ios-team-flow/references/RELEASE.md)。
