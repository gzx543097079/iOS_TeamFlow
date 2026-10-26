# 验证配置与迁移

编辑 `.agents/project-checks.json` 或迁移旧全量验证脚本时加载；运行、结果输出与证据见 [CHECKS](CHECKS.md)。

## 配置格式

配置 `schema_version: 2`，维护 `profiles`。路径均为项目相对文件/目录，不支持 glob。

- profile `covers` 是验收范围上限，省略继承 `inputs`；`inputs` 是证据依赖，省略使用 Git 可见文件。`covers` 必须在依赖范围内。
- check `covers` 是该项负责的改动范围，省略继承 profile；check `inputs` 是该项的依赖，省略继承 profile，covers 自动并入，无需重复列出。共享脚本、依赖锁文件及生成器须纳入相关检查的 inputs；输入依赖不会扩大可验收范围。
- 声明 check `covers` 后启用逐项触发：改动命中该项 covers 或 inputs 才运行；profile 设 `trigger: "covers"` 时只看 covers，inputs 只进入证据指纹与缓存键，适合共享依赖多、需按模块精确触发的项目，此时每个文件须由负责它的检查列入 covers。改动含工作区、暂存、未跟踪及本需求带 `Requirement:` 尾注的阶段提交；需求卡不触发项目检查。修改验证配置时只触发该 profile 中执行语义变化的检查，profile 级字段变化或配置改动已在阶段提交中时触发全部。声明了 check 或 profile `covers` 时，未覆盖的工程改动在执行前报错；只有 inputs 的旧配置保留整组检查，范围由提交检查核对。
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

## 从全量脚本迁移

升级不改写项目脚本和验证配置；`upgrade` 输出“验证配置待迁移”或 `doctor` 报告「验证配置形态」时，按 [INSTALL](INSTALL.md#升级) 另建卡迁移：

1. 读懂现有脚本的步骤与产物依赖，给脚本加日常与发布入口（如 `--scope change|release`）；依赖构建产物的核对与其构建留在同一入口。
2. 日常 profile 按独立步骤拆成多个 check（如编译、静态检查、启动检查），各配 `covers` 与完整 `inputs`。依赖整个源码目录的全套单元/UI 测试命中即整项执行，日常改为编译加按模块测试（如 `-only-testing`，inputs 含该模块依赖的共享目录），全套测试放入 `manual` profile，并在项目规则或 CI 中约定运行时机（如提 PR 前）。
3. Release 构建移入 `manual: true` 的 profile；已有独立 Release 检查的，删去日常脚本中的重复构建，并给该 profile 设 `manual`。
4. 核对 `-parallel-testing-enabled NO` 等串行设置，确有共享状态才保留。
5. 用新的日常 profile 验收并绑定迁移卡证据，`doctor` 不再报需处理后单独提交。

「需处理」（日常 profile 的命令或引用脚本含 Release 构建）必须迁移；「提示」（未声明 check covers，或日常检查最近实际执行超过 180 秒）在脚本含多个独立步骤时拆分，确为单一步骤的可保留。新项目配置检查时同样按第 2 步拆分。
