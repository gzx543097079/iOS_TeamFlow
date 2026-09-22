# 项目构建与测试

## 默认执行顺序

有实现与交付的任务使用：完成全部改动 → 环境预检 → 针对性测试 → 文件冻结 → 一次完整验证 → 目标交付。

1. 完成全部改动：先同步代码、测试、资源、文档、配置、版本、需求范围和稳定项目记录。
2. 环境预检：低成本核对工具版本、依赖是否存在、Scheme/Target、可用模拟器或设备，以及目标动作所需账号；不把完整构建当预检。
3. 针对性测试：开发期间运行最小相关测试或复现路径，失败后修复并重复这一层，不提前消耗完整 profile。
4. 文件冻结：确认本次所有受跟踪输入不再计划修改，并核对用户已有改动仍被隔离。
5. 一次完整验证：执行覆盖本次范围的最终 profile，生成与当前输入指纹绑定的证据。
6. 目标交付：证据仍有效时才进入明确授权的提交、推送、Release 或 App 动作及其必要前置。

“一次”表示正常成功路径只安排一次最终完整验证，不是禁止纠错。完整验证失败，或之后任何受跟踪输入变化时，必须回到针对性测试/文件冻结并重新完整验证；不得为了节省时间沿用失效证据。只修改需求卡状态、验证证据或异常记录且指纹规范明确忽略时，不触发重跑。

首次实施业务代码时从实际工程或 CI 提取验证命令，保存到 `.agents/project-checks.json`。不猜测 Scheme、设备或平台环境，不自动安装依赖。

```sh
python3 scripts/teamflow.py verify init
# 编辑 .agents/project-checks.json
python3 scripts/teamflow.py verify run --profile change
```

配置由 `checks`、`profiles`、可选 `inputs` 和 `profile_inputs` 组成。每个检查使用 argv 数组，无 shell 展开；profile 中每项均为必跑。测试命令已经包含构建时不机械重复 build。

结果保存到 `logs/project-checks/<运行编号>/result.json`，包含命令、退出码、时长、原始日志和输入指纹。失败、超时、工具缺失或运行期间输入变化都不算通过。

完成需求时引用结果：

```sh
python3 scripts/teamflow.py req complete REQ-0001 --result logs/project-checks/运行编号/result.json
```

commit 前的显式 Git 动作会再次比较暂存对象：

```sh
python3 scripts/teamflow.py git check REQ-0001 --result logs/project-checks/运行编号/result.json
```

输入应覆盖源码、工程配置、资源、锁文件和执行脚本。自动排除 Git 元数据、缓存、DerivedData、xcresult、验证证据和发布动作记录。默认业务 profile 忽略需求卡；文档 profile 显式纳入 requirements 时，卡片只绑定范围和 AC 条件，状态、验证结果与异常历史不会令自己的证据失效。

工具测试不能代替真机、视觉、账号、购买或平台验证。缺少这些证据时将需求标为待用户验证，不伪填通过。
