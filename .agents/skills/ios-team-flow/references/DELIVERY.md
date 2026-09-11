# 需求、提交、PR 与发布关联

需求的 ✅ 执行完成只表示适用验收完成。交付概览分别展示开发、已提交、PR 合并和 Release，不因其中一个完成就自动标记其他状态。

## 新需求的唯一维护入口

带 `teamflow:requirement:v2` 标记的需求只在 `requirements/REQ-*.md` 维护状态、AC 条件/结果/证据、验收方式及必要确认。脚本校验状态、唯一字段、AC 编号及完成条件；不代替验收真实性判断。JSON 和总表均为生成的只读投影，不能手工登记第二套 development 状态。

```sh
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-实际编号 finish
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-实际编号 finish --check
```

阶段结束、最终回复前和已授权提交后运行；未提交也生成需求状态，提交显示未关联。每轮只处理本需求，不扫描历史。相同事实重复 finish 不改文件。`finish --all` 只选新版卡；历史卡和旧交付记录保留，不自动补登记或迁移。

新卡不写 Git 状态、提交 SHA、审查指纹或手写进度；finish 不回写新卡。回执通过 requirements 数组关联卡片，提交通过尾注关联：

```sh
git commit -m '具体改动' -m 'Requirement: REQ-20260911-020'
```

提交必须先审查并获得用户授权。提交后 finish 发现实施提交；生成记录留下一次已授权归档，不为记录自身 SHA 循环提交。只有生成交付记录/回执的提交不算实施。发生代码或环境变化时按影响重开 AC 并实际复核；新增实施提交的内容不同于上次验收工作区、且仍沿用上一套完成证据时会拒绝收尾；正常提交已验收内容复用证据，要求修正源卡，不生成矛盾状态。

旧卡仅在明确指定其编号时保留原有 refresh、development、link-commit 和回写 Git 状态的兼容行为；新卡执行 development 会报错并指向唯一入口。本次以后不要求补齐旧卡。

关联实际 PR，并只读核对远端：

```sh
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-20260911-001 link-pr --url https://github.com/团队/仓库/pull/123
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-20260911-001 refresh --github
```

`--github` 使用已登录的 gh，读取 PR 状态、提交列表和 merge SHA；关联提交全部得到合并证据才标已合并。squash merge 使用已核实的 PR 合并提交判断后续发布包含关系。先按团队流程 fetch 所需分支、合并提交和 tags；工具不主动改动远端或自动 fetch。

本地标签只作 Release 候选，发布前核对 origin 远端标签解析提交与本地一致；只有 gh 返回已发布的正式 Release 且标签包含全部相关实施提交（或已核实的合并提交）才标已发布；草稿、预发布、只打标签均不等同正式发布。工具验证发布记录与提交包含关系，不代替安装包内容/签名校验。没有网络、权限、对象或没有远端查询时明确未核实，不凭本地 main 推断 PR 已合并。直接提交主分支且没有 PR 时，合并状态可保持未核实，已提交和正式发布可独立核对。

## 维护与边界

刷新保留操作历史、核对时间、提交 SHA、PR URL、发布 tag/URL。总表是交付索引，细节看各 JSON 和需求卡；团队验收不是工具自动批准。发生 rebase/squash 后核对关联，必要时在 Git 可审查的 JSON 中纠正旧手工 SHA 并记录理由，不伪造远端状态。

使用新版需求时 Codex 应在阶段结束及实施提交后 finish，从卡片自动读取验收状态；PR 合并/发布授权工作完成后再 finish --github。交付记录可归档到下一次文档提交，归档不添加实施尾注；不为了修改记录中的自身 SHA 循环提交。用户只授权提交推送时，不由追踪工具自动创建 PR 或发布版本。

本工具的 release 状态指 GitHub Release；App Store/TestFlight 发布状态须另按 [App 发布流程](APP-RELEASE.md) 核验并记录。

## 统一交付收尾

```sh
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-实际编号 finish
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-实际编号 finish --github
python3 .agents/skills/ios-team-flow/scripts/delivery.py finish --all --github --check
```

单项使用实际需求编号；`--all` 仅扫描新版需求卡，不与 --requirement 同时使用。finish 刷新 JSON 和总表；新版卡不回写，旧卡兼容更新 Git 状态字段，保留历史和产品验收。--check 只核对，缺失/过期记录返回非零，不改文件。无实施提交的卡会单独列出，未授权提交的新需求可以合法处于该状态。

提交、推送、发布的收尾必须报告 finish 结果及 unarchived_changes；刷新后产生的记录改动仍需后续授权的归档提交。工具不自动 commit/push，不把提交或正式 Release 等同团队验收。新版需求本地 finish 在提交集合未变时保留上次远端证据与 github_checked_at，不将已核实状态退回未知；这不代表本轮查询。提交集合变化则失效，使用 --github 重新核对；网络或对象不足仍明确未核实。发布后可先更新记录再归档到下一次文档提交，避免修改发布标签或循环提交自己的 SHA。
