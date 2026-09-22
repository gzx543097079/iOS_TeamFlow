# 项目构建与测试

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
