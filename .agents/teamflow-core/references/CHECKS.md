# 验证与证据

主流程与停止条件见 [WORKFLOW](WORKFLOW.md)。首次使用环境或环境变化时，低成本核对工具、依赖、Scheme/Target、设备及目标所需账号；命令来自实际工程或 CI，不猜测，也不把完整构建当预检。

## 配置与运行

```sh
python3 scripts/teamflow.py verify init
# 编辑 .agents/project-checks.json
python3 scripts/teamflow.py verify suggest --requirement REQ-20260101-0001
python3 scripts/teamflow.py verify run --profile change --requirement REQ-20260101-0001
```

配置 `schema_version: 2`，维护 `profiles`。路径均为项目相对文件/目录，不支持 glob。

- profile `covers` 是验收范围上限，省略继承 `inputs`；`inputs` 是证据依赖，省略使用 Git 可见文件。`covers` 必须在依赖范围内。
- check `covers` 是该项负责的改动范围，省略继承 profile；check `inputs` 是该项的完整依赖，省略继承 profile。共享脚本、依赖锁文件及生成器须纳入相关检查的 inputs；输入依赖不会扩大可验收范围。
- 声明 check `covers` 后启用逐项触发：改动命中该项 covers 或 inputs 才运行。改动含工作区、暂存、未跟踪及本需求带 `Requirement:` 尾注的阶段提交；需求卡不触发项目检查。未覆盖的工程改动在执行前报错。旧配置没有任何 check covers 时保留整组检查行为。
- `priority` 为非负整数，默认 100，越小越优先；只在覆盖全部改动的候选中比较，同优先级要求显式选择。`manual: true` 的 profile 不参与自动选择，显式指定才执行完整检查，适用于 Release；普通代码改动、提交或 PR 不自动触发 Release。
- `extends` 继承父 profile，子 checks 追加或同名整项覆盖。argv 无 shell 展开。`parallelism` 默认 1，保留旧配置的顺序；仅互不依赖、不争用产物目录的检查才设置大于 1。每项从自身启动计算超时。
- `incremental: true` 显式开启检查缓存。命令、依赖和需求语义未变时可复用上次通过结果；最新失败不能越过查找旧通过。依赖生成产物的步骤放在同一顺序脚本中并设 `cache: false`，避免跳过构建后检查不存在的产物。

```json
{
  "schema_version": 2,
  "profiles": {
    "change": {
      "inputs": ["App", "scripts/check_debug.py", "docs", "scripts/check_docs.py"],
      "priority": 10,
      "parallelism": 2,
      "incremental": true,
      "checks": {
        "debug": {
          "argv": ["python3", "scripts/check_debug.py"],
          "covers": ["App", "scripts/check_debug.py"],
          "inputs": ["App", "scripts/check_debug.py"],
          "timeout_seconds": 900
        },
        "docs": {
          "argv": ["python3", "scripts/check_docs.py"],
          "covers": ["docs", "scripts/check_docs.py"],
          "inputs": ["docs", "scripts/check_docs.py"]
        }
      }
    },
    "release": {
      "manual": true,
      "inputs": ["App", "scripts/check_release.py"],
      "checks": {
        "release": {"argv": ["python3", "scripts/check_release.py"], "cache": false}
      }
    }
  }
}
```

示例须替换为项目实际命令和完整依赖。测试已包含构建时不重复 build；产物检查须在构建后执行。只升级 TeamFlow 不会拆开既有大脚本：项目需提供日常和发布入口，将 Release 构建移入显式 profile。不要未经核对直接开启 Xcode 测试并行或并发使用同一 DerivedData。

## 验证强度与结果输出

小改动按影响范围和风险选择最小有效检查；支付、认证、数据迁移、共享状态和工程配置仍须补齐专项验证。路径匹配只能提供选择线索，不能证明测试充分。测试命令必须能识别空套件，不能把“0 个测试”当通过。

同批相关改动定稿后统一验收。失败时先运行定位问题的必要检查，修复后复核受影响范围；不因提交、PR 或合并再跑全套。日常检查不含 Release，准备发布时明确运行发布 profile。

输出区分本次执行、复用通过及未触发；没有触发项时返回“无需检查”，不生成通过证据、不自动完成需求。已有有效证据继续复用，纯文档记录可使用实际人工核对。缺环境、工具、模拟器或账号是“未验证”，不能解释为未触发，更不能临时改 profile 绕过；需求保持进行中。

## 证据

- **运行**：`req complete --profile` 优先复用有效摘要，否则执行适用项；`verify run` 重新计算执行计划。两者的 `--rerun` 均强制执行显式 profile 的全部检查并绕过缓存。日志保存在 `logs/project-checks/<运行编号>/`，只作本地记录。
- **指纹**：绑定配置、输入内容与可执行位、实际检查名单及需求语义。check 的范围外依赖也进入总证据；未触发项不贡献覆盖。失败、超时或运行中输入改变不算通过。
- **需求语义**：绑定范围、不包含和按编号排序的 AC 文字；标题、状态、勾选、排版与决策不影响证据。范围或 AC 文字变化必须重新验证，不能只替换摘要。独立检查未绑定需求时不能直接用于完成卡片。
- **复核**：提交钩子与 CI 按实际检查覆盖核对，不执行测试、不依赖本地日志；提交另比较暂存快照。旧证据按旧完整 profile 规则复核，新部分证据不能借 profile 的宽范围放行。
- 工具测试不替代真机、视觉、账号或平台验收；人工 AC 按主流程保留待验证。安全与 Git 边界见 [BOUNDARIES](BOUNDARIES.md)，参数见 [COMMANDS](COMMANDS.md)。
