# 业务项目构建与测试入口

工作流工具测试不能代替 App 验证。首次处理业务需求时，从实际工程/CI 提取命令，保存到项目 `.agents/project-checks.json`；已有配置先合并，不猜测 Scheme、设备 ID 或最低系统。脚本不自动安装依赖，也不自动向业务仓库注入 CI。

```sh
python3 .agents/skills/ios-team-flow/scripts/project_checks.py init
# 编辑生成的 .agents/project-checks.json：填入实际命令、profile 和输入路径后再运行
python3 .agents/skills/ios-team-flow/scripts/project_checks.py run --profile change
```

从项目根目录执行，或在子命令前传 `--project 项目路径`。init 仅创建空配置，不覆盖文件；没有有效 profile 时执行失败，不会把未配置当验证成功。工具要求 Python 3.10+，运行 iOS 命令还需项目实际 macOS/Xcode 环境。

配置示例（MyApp、Scheme 和设备需替换为实际值后使用）：

```json
{
  "schema_version": 1,
  "inputs": ["App", "scripts"],
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
  "profiles": {"build-only": ["build"], "change": ["unit-tests"]}
}
```

示例 change 由 test 完成测试及其构建，不机械重复 build；build-only 用于只需构建的改动。不同配置/Target 的额外构建有独立验证目的时再组合。list 仅用于查询配置，不是必经步骤。

可配置现有 lint、测试计划、脚本或其他工具的 argv。没有 shell 展开，空格保留为单个参数；需要 shell 的已有项目脚本用其解释器显式调用，先审阅配置及脚本。凭据通过已有环境管理提供，不写进 argv/配置。不因使用入口而擅自执行发布、删除数据等命令。

Codex 在需求卡明确本次选用的 profile 和原因；profile 内每项均为必跑。按改动选择必要构建、测试与静态检查，文档改动只选适用检查，不默认全量测试。新项目创建可运行工程后补齐配置；已有工程从 PROJECT-CONTEXT 引用的配置入口获取命令。未选项目注明范围理由，不能将关键验收缺失归为不适用。无明确要求不验证超大字号。

检查按执行顺序逐项输出名称与状态，最后输出验证证据路径，与 1.9.2 一致；完整结果及原始日志仍保存到文件。

结果保存至 `logs/project-checks/<运行编号>/result.json`，每项记录命令、工作目录、退出码、时长及原始日志。失败、工具缺失、超时都返回非零退出码，不算通过。报告同时保存运行前后源码/配置指纹；运行中输入变化会返回非零，不标通过。采用工作区实际文件，不以 HEAD 代替未提交源码。

原始日志可能含本地路径或敏感输出，提交前脱敏；可在项目 .gitignore 中排除原始 `.log`，保留脱敏摘要/受控 CI artifact 链接。CI 可使用同一命令并归档日志，但不要在有生产凭据的环境执行不可信外部改动提供的配置。对相关基线失败与新引入失败分别记录；工具只报告执行结果，不自行认定历史失败可忽略。

## 验证结果是否仍适用

```sh
python3 .agents/skills/ios-team-flow/scripts/project_checks.py verify --result logs/project-checks/实际运行编号/result.json --staged
```

提交前由 review_gate check 统一执行 verify --staged；独立命令仅用于提前排错，无需固定再跑一次。复用测试证据时，同时核对已测试工作区和暂存对象的内容、增删及执行权限（包括尚未暂存的新文件）；只在实施过程复用时可省略 --staged。暂存区不匹配时暂存正确内容或测试隔离的暂存快照，不能仅重跑当前工作区测试。源码增加、删除、内容/执行权限改变或验证配置改变都会令旧结果失效；没有源码指纹的旧报告需重测。工具校验所记录范围，不保证测试覆盖充分，也不是防伪签名。当前检测运行前后差异，不能发现运行中改动后又完全还原的瞬时变化；测试期间不要编辑输入文件。

`inputs` 是项目相对文件/目录列表（不支持 glob），应覆盖本次 App 的源代码、工程配置、资源、依赖锁文件和执行脚本；`.agents/project-checks.json` 始终纳入。Git 目录输入选择已跟踪及未忽略文件，与验收共用规则，排除 .git、缓存、DerivedData、.build、xcresult 和证据目录；拒绝符号链接。不要把构建输出目录纳入输入。

可用 `profile_inputs` 按 profile 指定输入列表，优先于全局 inputs，例如 `"profile_inputs": {"docs": ["requirements", ".agents/skills/ios-team-flow/references"]}`。

profile 范围按受影响模块和关联输入配置，包含共享代码、工程配置、资源、锁文件和执行脚本；不确定影响范围时扩大验证，不以节省 token 为由缩小覆盖。

省略 inputs 时，Git 项目按已跟踪及未忽略的新文件记录，默认排除 requirements/ 下的 Markdown/JSON 管理记录，避免更新状态触发业务重测（该目录不得放业务资源；需要验证需求文档时显式纳入 inputs/profile_inputs）。删除的跟踪文件也参与比较；非 Git 项目必须显式配置 inputs。自动排除 logs/project-checks、logs/reviews 和 .agents/teamflow-backups 的生成证据，其他生成产物由项目 .gitignore 或明确 inputs 排除。此处测试指纹与 review 暂存指纹用途不同：前者证明测试对象，后者证明审查对象。

实际验收优先向 delivery.py finish --accept 传 --result 结果路径（可重复），工具验证结果并复用对应 profile 输入，无需再手填 --inputs；result 不代替 AC 或团队确认。

## 文档验证与有效输入

输入必须至少匹配有效文件，或有 Git 跟踪历史可证明是合法删除；拼错、空目录和从未存在的路径明确报错。删除后暂存和后续复核不因此误重测。

requirements/delivery/ 是验收绑定及外部事实记录，始终排除；旧项目遗留的 requirements/DELIVERY.md 也继续排除但不再生成。显式验证 requirements 时，结构化 REQ 卡只绑定产品正文及 AC 编号/条件；状态、下一步、阻塞、确认记录、AC 结果/证据和“过程与决策”不进入源码指纹，它们由需求结构校验及提交语义审查核对。PRD 和其他文档仍绑定完整内容。不得把产品需求正文放在过程记录里。

因此先验证文档、再填写 AC 结果及 finish 不会让自己的证据失效；改变条件或产品正文仍必须重验。此规范用于产品文档验证；验证工作流状态解析器本身应使用独立测试夹具，不能依赖已排除的运行记录证明状态逻辑。

## 新工程启动验证

新建主 App 或修改启动生命周期时，按 [Scene 生命周期](APP-LIFECYCLE.md) 配置实际 App 检查：Debug/Release 成品配置、窗口归属、冷启动/前后台/重启及启动日志。SwiftUI App 不要求手写 SceneDelegate。源仓库工具回归、编译成功或日志文本检查不能单独代替实际 App 启动；缺少运行证据时保持未验证。
