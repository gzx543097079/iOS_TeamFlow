# 大型项目模块增量读取工具

工程约定保留在已有项目资料或按需建立的 PROJECT-CONTEXT 中，机器可核对的模块索引放在项目根 `.agents/project-modules.json`。工具只读取模块元数据、Git 对象和文件名，不读取源码正文；它把“该看哪里、哪些路径已变化、是否需要扩大范围”变成可重复命令。索引无法命中或失效时明确扩大检查，不能静默退化为“无变化”。

## 建立模块索引

模块首次核对完成后执行：

```sh
python3 scripts/teamflow.py module record \
  --name account --responsibility "登录、会话与账号安全" \
  --trigger 登录 --trigger 账号 --trigger account \
  --path App/Features/Account --entry LoginViewController \
  --dependency Shared/Session --caller AppRouter \
  --verification ios-account \
  --cross-cutting Project.swift --cross-cutting Package.resolved
```

`record` 拒绝未被 Git 跟踪（含已暂存）的关注路径、路径穿越、Git 魔法 pathspec 和符号链接索引。同名模块会被显式更新，其他模块保留。触发词用于初筛需求，不是产品语义的唯一来源；名称、页面、Target 或接口无法命中时由 Agent 扩大检查并补充正确路由，不猜测最相近模块。

索引字段包含职责、触发词、关注路径、入口符号、依赖、调用方和验证入口，不保存提交基准等需要人工推进的状态。基线分支默认取 `origin/HEAD`，否则依次尝试 `main`、`master`；可在索引顶层用 `base_branch` 指定。项目资料只链接该文件并保留无法机器化的稳定工程事实，不再复制同一模块表。

## 新需求只读检查

```sh
python3 scripts/teamflow.py module inspect --query "修改登录页错误提示"
python3 scripts/teamflow.py module inspect --module account
```

工具与基线分支的分叉点比较：输出本分支已提交、暂存、未暂存和未跟踪的改动，并返回入口符号、依赖、调用方、验证入口、建议读取文件及 `expand_scope`。在基线分支上且工作区干净时为 `unchanged`，只表示关注路径没有改动；实施仍需读取待改符号和必要调用者。`changed` 先读 `suggested_read_files` 和入口；`invalid`、未命中或横切路径变化时 `expand_scope` 为 true，必须扩大到实际影响面。

跨模块需求可重复传入 `--module`，`--all`/`validate` 用于索引维护和排错，不应成为每次需求的默认全仓入口。默认输出简短摘要，`--json` 输出完整结构；保存到需求证据时应脱敏，不把动态结果回写项目资料。

## 维护

模块职责、入口、依赖、调用方、验证入口或关注路径变化时，用 `record` 更新对应模块；路径移动或删除会使 `validate` 报 `invalid`，需重新记录。索引随项目提交和克隆，版本升级不覆盖项目数据。
