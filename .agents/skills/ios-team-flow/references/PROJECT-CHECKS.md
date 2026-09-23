# 项目构建与测试

主流程与停止条件见 [WORKFLOW](WORKFLOW.md)。首次使用环境或环境变化时，低成本核对工具、依赖、Scheme/Target、设备及目标所需账号；命令来自实际工程或 CI，不猜测，也不把完整构建当预检。

## 配置与运行

首次配置项目的真实验证命令：

```sh
python3 scripts/teamflow.py verify init
# 编辑 .agents/project-checks.json
python3 scripts/teamflow.py verify run --profile change --requirement REQ-0001
```

配置由 `checks`、`profiles`、可选 `inputs` 和 `profile_inputs` 组成。检查使用 argv 数组，无 shell 展开；所选 profile 的每项均为必跑。测试已包含构建时不重复 build。

收尾前确认本次受验证输入稳定、用户改动已隔离，然后运行匹配范围的 profile。失败后修复并重跑相关验证，不限制验证次数。

## 证据范围

结果位于 `logs/project-checks/<运行编号>/result.json`，包含命令、退出码、时长、原始日志及输入指纹。失败、超时、工具缺失或运行期间输入变化均不算通过。

指纹绑定所选 profile 的命令、工作目录、超时、输入范围，以及相关源码、资源、锁文件和执行脚本。其他 profile 配置及 JSON 排版变化不影响当前结果；共享检查变化会影响所有使用它的 profile。

`--requirement` 额外绑定本次需求，忽略其他需求记录。需求范围与 AC 条件变化令证据失效；状态、AC 完成图标、验证证据和异常记录变化不影响它。不指定需求可执行独立工程检查，但该结果不能直接用于 `req complete`。配置输入应指向实际工程，避免纳入全部历史资料。

完成命令读取结果并核对其需求绑定及当前输入。commit 前按 [GIT-ACTIONS](GIT-ACTIONS.md) 额外核对暂存快照，包含本次需求卡及所选有效配置；该核对不重新运行测试。

工具测试不能代替真机、视觉、账号、购买或平台验证。人工证据应可定位；尚未确认的 AC 按主流程保留待验证。
