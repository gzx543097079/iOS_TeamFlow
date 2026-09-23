# 项目构建与测试

主流程与停止条件见 [WORKFLOW](WORKFLOW.md)。首次使用环境或环境变化时，低成本核对工具、依赖、Scheme/Target、设备及目标所需账号；命令来自实际工程或 CI，不猜测，也不把完整构建当预检。

## 配置与运行

首次配置项目的真实验证命令：

```sh
python3 scripts/teamflow.py verify init
# 编辑 .agents/project-checks.json
python3 scripts/teamflow.py verify run --profile change --requirement REQ-0001
```

配置只维护 `profiles`：每项就近定义 `checks` 和可选 `inputs`，省略输入时使用 Git 可见文件。检查使用 argv 数组，无 shell 展开；所选 profile 的每项均为必跑。测试已包含构建时不重复 build。

```json
{
  "schema_version": 2,
  "profiles": {
    "change": {
      "inputs": ["App", "scripts/test_app.py"],
      "checks": {
        "tests": {"argv": ["python3", "scripts/test_app.py"], "timeout_seconds": 900}
      }
    }
  }
}
```

示例路径须替换为项目实际文件与命令；命令复用可放在项目脚本中。

收尾前确认本次受验证输入稳定、用户改动已隔离，然后运行匹配范围的 profile。失败后修复并重跑相关验证，不限制验证次数。

## 证据范围

结果位于 `logs/project-checks/<运行编号>/result.json`，包含命令、退出码、时长、原始日志、一份完整输入快照及结束指纹。仅输入变化时附带新增、删除和修改的差异，不重复保存整份快照。失败、超时、工具缺失或运行期间输入变化均不算通过。

指纹绑定所选 profile 的命令、工作目录、超时、输入范围，以及相关源码、资源、锁文件和执行脚本。其他 profile 配置及 JSON 排版变化不影响当前结果；每个 profile 独立保存命令及输入。

`--requirement` 额外绑定本次需求，忽略其他需求记录。需求读取与指纹共用解析器，只绑定范围、排除项和按编号排序的 AC 条件；这些内容变化令证据失效。标题、字段首尾空白、排版、状态、AC 完成图标、验证证据和异常记录不影响它。不指定需求可执行独立工程检查，但该结果不能直接用于 `req complete`。配置输入应指向实际工程，避免纳入全部历史资料。

收尾使用 `req complete REQ-0001 --profile change`，验证、`--confirm-ac` 指定条件确认与证据复用按 [WORKFLOW](WORKFLOW.md#实施与验收) 执行。命令会显示尚未完成的条件和下一步；只有 AC 全部确认后才报告完成。

完成命令读取结果并核对其需求绑定及当前输入。commit 前按 [GIT-ACTIONS](GIT-ACTIONS.md) 额外核对暂存快照，包含本次需求卡及所选有效配置；该核对不重新运行测试。

工具测试不能代替真机、视觉、账号、购买或平台验证。人工证据应可定位，内容绑定与复用范围按 [WORKFLOW](WORKFLOW.md#实施与验收)；尚未确认的 AC 按主流程保留待验证。

## 按需诊断与范围建议

`verify suggest` 按实际改动展示各 profile 的路径覆盖及遗漏；建议不代表测试充分性。`doctor` 只读检查配置和输入是否有效；详见 [命令参考](COMMANDS.md)。命令是受信任的项目代码，并非文件系统或网络沙箱，涉及时遵循 [敏感信息与外部服务边界](SECURITY-BOUNDARIES.md)。
