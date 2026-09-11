# 需求、提交、PR 与发布关联

需求的 ✅ 执行完成只表示适用验收完成。交付概览分别展示开发、已提交、PR 合并和 Release，不因其中一个完成就自动标记其他状态。

## 日常操作

从项目根目录执行，所有状态记录在 `requirements/delivery/REQ-*.json`，总表生成到 `requirements/DELIVERY.md`；需求卡保留产品需求与验收历史，不因关联当前提交 SHA 而循环修改自身。

提交时加入可机器识别的尾注，多个需求各一行：

```sh
git commit -m '具体改动' -m 'Requirement: REQ-20260911-001'
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-20260911-001 refresh
```

提交必须先经过审查和用户授权。refresh 从 HEAD 历史发现标注的实施提交；只包含交付记录或审查回执的归档提交不视为新的实施。旧提交无尾注时可用 `link-commit --commit 实际SHA` 补关联。工具不会修改 Git 历史。

验收完成后登记开发状态和证据：

```sh
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-20260911-001 development --state 开发完成 --evidence '需求卡验收及 logs/ 中的验证结果'
```

可登记未执行、执行中、待验证。开发完成记录绑定当时关联提交集合；出现新的实施提交时刷新会提示“提交变化，需复核开发验收”，不继续沿用旧完成结论。代码提交前仍由需求卡标注实际执行状态，完成后再登记对应提交的验收。

关联实际 PR，并只读核对远端：

```sh
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-20260911-001 link-pr --url https://github.com/团队/仓库/pull/123
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-20260911-001 refresh --github
```

`--github` 使用已登录的 gh，读取 PR 状态、提交列表和 merge SHA；关联提交全部得到合并证据才标已合并。squash merge 使用已核实的 PR 合并提交判断后续发布包含关系。先按团队流程 fetch 所需分支、合并提交和 tags；工具不主动改动远端或自动 fetch。

本地标签只作 Release 候选，发布前核对 origin 远端标签解析提交与本地一致；只有 gh 返回已发布的正式 Release 且标签包含全部相关实施提交（或已核实的合并提交）才标已发布；草稿、预发布、只打标签均不等同正式发布。工具验证发布记录与提交包含关系，不代替安装包内容/签名校验。没有网络、权限、对象或没有远端查询时明确未核实，不凭本地 main 推断 PR 已合并。直接提交主分支且没有 PR 时，合并状态可保持未核实，已提交和正式发布可独立核对。

## 维护与边界

刷新保留操作历史、核对时间、提交 SHA、PR URL、发布 tag/URL。总表是交付索引，细节看各 JSON 和需求卡；团队验收不是工具自动批准。发生 rebase/squash 后核对关联，必要时在 Git 可审查的 JSON 中纠正旧手工 SHA 并记录理由，不伪造远端状态。

使用新的工作流需求时 Codex 应在实施提交后 refresh，完成验收后登记 development；PR 合并/发布授权工作完成后再 refresh --github。交付记录可归档到下一次文档提交，归档不添加实施尾注；不为了修改记录中的自身 SHA 循环提交。用户只授权提交推送时，不由追踪工具自动创建 PR 或发布版本。

本工具的 release 状态指 GitHub Release；App Store/TestFlight 发布状态须另按 [App 发布流程](APP-RELEASE.md) 核验并记录。
