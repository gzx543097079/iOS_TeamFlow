# 大型项目模块增量读取工具

规则描述放在 PROJECT-CONTEXT，机器可核对的模块索引放在项目根 `.agents/project-modules.json`。工具只读取模块元数据、Git 对象和文件名，不读取源码正文；它把“该看哪里、哪些路径已变化、是否需要扩大范围”变成可重复命令。索引不存在、无法命中或失效时明确扩大检查，不能静默退化为“无变化”。

## 建立模块索引

模块首次核对完成且相关路径已经提交、工作区干净时执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/module_context.py --project . record \
  --name account --responsibility "登录、会话与账号安全" \
  --trigger 登录 --trigger 账号 --trigger account \
  --path App/Features/Account --entry LoginViewController \
  --dependency Shared/Session --caller AppRouter \
  --verification ios-account \
  --cross-cutting Project.swift --cross-cutting Package.resolved
```

`record` 自动绑定当前完整 HEAD，拒绝未被 HEAD 跟踪的关注路径、路径穿越、Git 魔法 pathspec、符号链接索引以及关注路径内未提交改动。同名模块会被显式更新，其他模块保留。触发词用于初筛需求，不是产品语义的唯一来源；名称、页面、Target 或接口无法命中时由 Codex扩大检查并补充正确路由，不猜测最相近模块。

索引字段包含职责、触发词、关注路径、入口符号、依赖、调用方、验证入口和基准。PROJECT-CONTEXT 只链接该文件并保留无法机器化的稳定工程事实，不再复制同一模块表。

## 新需求只读检查

```sh
python3 .agents/skills/ios-team-flow/scripts/module_context.py --project . inspect --query "修改登录页错误提示"
python3 .agents/skills/ios-team-flow/scripts/module_context.py --project . inspect --module account
```

输出区分 baseline 到 HEAD 的已提交变化、暂存、未暂存和未跟踪文件，并返回入口符号、依赖、调用方、验证入口、建议读取文件及 `expand_scope`。`unchanged` 只表示已配置路径没有 Git 变化；实施仍需读取待改符号和必要调用者。`changed` 先读 `suggested_read_files` 和入口；`invalid`、未命中或横切路径变化时 `expand_scope` 为 true，必须扩大到实际影响面。

跨模块需求可重复传入 `--module`，`--all`/`validate` 用于索引维护和排错，不应成为每次需求的默认全仓入口。工具输出保存到需求证据时应脱敏，不把动态结果回写 PROJECT-CONTEXT。

## 前移基准

实现提交后，先人工核对模块职责、入口、依赖、调用方和验证入口；稳定事实有变化时先用 `record` 更新字段。只有关注路径及横切路径工作区干净，才执行：

```sh
python3 .agents/skills/ios-team-flow/scripts/module_context.py --project . refresh \
  --module account --accept-reviewed-changes
```

显式确认参数表示相关已提交变化已经复核，不代表测试通过。工具拒绝用含未提交变化的工作区前移基准，也拒绝 HEAD 不再覆盖关注路径；路径移动时必须重新记录模块。索引随项目提交和克隆，版本升级不覆盖项目数据。
