# 业务项目构建与测试入口

工作流工具测试不能代替 App 验证。首次处理业务需求时，从实际工程/CI 提取命令，保存到项目 `.agents/project-checks.json`；已有配置先合并，不猜测 Scheme、设备 ID 或最低系统。脚本不自动安装依赖，也不自动向业务仓库注入 CI。

```sh
python3 .agents/skills/ios-team-flow/scripts/project_checks.py init
python3 .agents/skills/ios-team-flow/scripts/project_checks.py list
python3 .agents/skills/ios-team-flow/scripts/project_checks.py run --profile change
```

从项目根目录执行，或在子命令前传 `--project 项目路径`。init 仅创建空配置，不覆盖文件；没有有效 profile 时执行失败，不会把未配置当验证成功。工具要求 Python 3.10+，运行 iOS 命令还需项目实际 macOS/Xcode 环境。

配置示例（MyApp、Scheme 和设备需替换为实际值后使用）：

```json
{
  "schema_version": 1,
  "checks": {
    "build": {
      "argv": ["xcodebuild", "-project", "App/MyApp.xcodeproj", "-scheme", "MyApp", "-sdk", "iphonesimulator", "CODE_SIGNING_ALLOWED=NO", "build"],
      "cwd": ".",
      "timeout_seconds": 900
    },
    "unit-tests": {
      "argv": ["xcodebuild", "-project", "App/MyApp.xcodeproj", "-scheme", "MyApp", "-destination", "platform=iOS Simulator,id=实际设备ID", "test"],
      "cwd": ".",
      "timeout_seconds": 1800
    }
  },
  "profiles": {"change": ["build", "unit-tests"]}
}
```

可配置现有 lint、测试计划、脚本或其他工具的 argv。没有 shell 展开，空格保留为单个参数；需要 shell 的已有项目脚本用其解释器显式调用，先审阅配置及脚本。凭据通过已有环境管理提供，不写进 argv/配置。不因使用入口而擅自执行发布、删除数据等命令。

Codex 在需求卡明确本次选用的 profile 和原因；profile 内每项均为必跑。按改动选择必要构建、测试与静态检查，文档改动只选适用检查，不默认全量测试。新项目创建可运行工程后补齐配置；已有工程复用 PROJECT-CONTEXT 中的命令。未选项目注明范围理由，不能将关键验收缺失归为不适用。无明确要求不验证超大字号。

结果保存至 `logs/project-checks/<运行编号>/result.json`，每项记录命令、工作目录、退出码、时长及原始日志。失败、工具缺失、超时都返回非零退出码，不算通过。报告标明针对当前工作区及 HEAD，不能据此宣称未暂存内容与最终提交一致；提交前确认验证后的业务代码未改变，否则重跑受影响检查。

原始日志可能含本地路径或敏感输出，提交前脱敏；可在项目 .gitignore 中排除原始 `.log`，保留脱敏摘要/受控 CI artifact 链接。CI 可使用同一命令并归档日志，但不要在有生产凭据的环境执行不可信 PR 的配置。对相关基线失败与新引入失败分别记录；工具只报告执行结果，不自行认定历史失败可忽略。
