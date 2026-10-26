# Godot 验证与证据

沿用[共用验证和证据机制](../../../teamflow-core/references/CHECKS.md)。profile 名称由项目配置决定；不增加独立状态表。

## 检查选择

| 变化 | 验证 |
| --- | --- |
| 脚本、场景和资源 | 资源导入／加载 + 受影响的逻辑或场景测试 |
| 输入、UI、渲染、动画和声音 | 上述检查 + 有画面的实际运行及受影响操作 |
| 性能或加载 | 按[性能与稳定性](PERFORMANCE.md)在目标设备测量并记录前后结果 |
| 导出预设或原生插件 | Godot 检查 + iOS 导出与 Xcode 构建 + 适用真机场景 |
| 发布 | 目标最终产物核对、必要设备验证及明确外部动作 |

`--headless --editor --import` 只证明导入检查，不能当作玩法、视觉或 iOS 验收。测试脚本由项目维护，失败须显式 `quit(1)`；捕获引擎错误，即使进程退出 0 也不能标通过。退出超时按失败处理，不无限等待。

## 可复用检查入口

[verify_godot.py](../scripts/verify_godot.py) 接受实际游戏根与项目测试脚本，执行导入和测试。默认查找 PATH 中 godot／godot4 或 macOS 既有 Godot 安装；可传 `--godot` 指定已有可执行文件。不安装引擎或插件。

```sh
python3 .agents/skills/Godot/scripts/verify_godot.py \
  --project game --test-script tests/run_tests.gd
```

测试故意触发的引擎错误（如损坏存档的解析错误）用 `--allow-error 正则` 逐条放行，只作用于测试阶段且只匹配该行，其他错误仍判失败。测试脚本相对游戏资源根，必须存在，写法与框架选择见[测试脚本](TESTING.md)。`--import-only` 只检查导入；`--test-only --test-script …` 只执行测试，须在同次串行检查中先成功导入，不能单独作为完整验收。日志写入游戏根 `.godot/teamflow-checks/`；串行测试会覆盖 `tests.log`，各 check 的完整输出另由核心保存。缓存不提交，工具不伪造不存在的项目测试。

默认读取 `project.godot` 的 `config/features` 主次版本：引擎须同主版本且次版本不低于工程，升级引擎不失败。需要固定精确版本时传 `--expect-version`（如 `4.7.2`），或由团队在 `.agents/team/toolchain.json` 锁定（见[团队协作](TEAM.md)），不一致即失败；显式参数优先。每个阶段默认最多 120 秒，可用 `--timeout` 按实际项目调整。

[配置示例](../assets/project-checks.example.json) 假定 `game/modules/{combat,inventory}/` 各自包含模块脚本、场景和专用资源，`game/tests/{combat,inventory}/run_tests.gd` 各跑一个模块；共享源码、资源和测试辅助分别位于 `game/shared/`、`game/assets/`、`game/tests/helpers/`。先替换为真实目录与入口，再合并进已有 `.agents/project-checks.json`（字段见[验证配置](../../../teamflow-core/references/CHECKS-CONFIG.md)）。不存在的示例目录应删除或替换，不新建空目录凑配置。

- `godot-check` 先导入一次，再按模块的 `covers` 和完整 `inputs` 触发测试。战斗改动只跑导入和战斗测试；共享依赖改动触发所有依赖它的模块。跨模块调用要把被依赖模块加入对应 check 的 inputs。
- 导入 check 继承整个 profile 的 inputs，保证任一模块测试触发时导入也执行；其 covers 仅认领共享文件，不能写成整个 `game/` 来掩盖未配置测试的新模块。新增模块要同时补齐测试入口、covers 和依赖。导出预设、原生插件按实际验证入口配置对应 check，不能只认领为导入已覆盖。
- 保持导入排第一、`parallelism: 1`、所有步骤 `cache: false`；共享 `.godot/` 和日志时不得并发运行这些 profile，也不使用会跳过导入的 `trigger: "covers"`。核心可能在导入失败后继续后项，后项通过不能抵消导入失败或作为验收证据。
- `godot-full` 仅显式指定时运行 `game/tests/run_tests.gd` 全套入口；不得继承进日常 profile，项目另行约定全套运行时机。

inputs 须包含实际脚本、场景、资源、导入配置与工具链依赖；将 `.godot/` 加入项目 `.gitignore`，保留持久 UID 与源资源。

iOS 构建 profile 必须运行真实导出和构建脚本，可通过 `extends` 包含游戏检查；尚未配置就记未验证，不能用空命令代替。混合原生／Godot 改动使用覆盖两部分的组合 profile。人工视觉、设备或平台条件保持未勾选，等待真实证据后确认。

依据：[官方命令行参考](https://docs.godotengine.org/en/stable/tutorials/editor/command_line_tutorial.html)。
