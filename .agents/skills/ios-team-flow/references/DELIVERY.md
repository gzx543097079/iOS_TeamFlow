# 验收对象与交付同步

需求卡是当前状态和 AC 结果的唯一人工入口。delivery 生成验收对象绑定、Git 事实和总表，不手填第二套 development 或 Git 状态。

## 验收绑定

这些命令由 Codex 执行，成员无需背诵编号和参数。实际验收完成后更新卡片，再选择一种方式：

```sh
# 自动检查：引用已通过的真实结果，可重复 --result；复用 profile 的输入范围
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-实际编号 finish --accept --result logs/project-checks/运行编号/result.json
# 人工验收：范围覆盖源码、工程配置、资源、锁文件及相关脚本
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-实际编号 finish --accept --inputs App tests
```

--result 会核对测试与当前输入一致，不能引用失败或过期结果；不能同时 --inputs 重复指定范围。混合验收时，profile 输入应覆盖受影响范围，人工/团队确认记在 AC。没有测试结果的人工验收才直接选范围，未指定则使用 Git 可见工作区；后续沿用原范围。测试与验收共用目录选择规则，排除 Git 元数据、缓存、忽略的生成文件和证据；requirements 下管理记录不参与实施指纹。AC 或证据真实性仍由语义审查负责。

普通 finish 不批准或覆盖验收；未提交验收仍比较工作区，变化必须实际复核并更新 AC 后 --accept。代码变化但 AC 证据未更新时拒绝接受。

实施提交含已验收内容时，工具将基线封存到确切提交和本需求提交集合。封存后其他需求修改同目录不影响原验收；新增本需求实施提交需匹配已验收内容，否则复核。明确续接或发现回归时先重开卡片并同步，解除封存后只复核实际受影响 AC。历史验收证明当时版本，不代表当前产品永远正确。

## 同步时机

状态、AC 或交付事实变化后同步一次；无变化问答不调用。--accept 已包含同步和写后核验，不再追加 finish/--check。--check 供独立只读核对；批量 finish --all 不批量批准验收。

```sh
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-实际编号 finish
# 实际远端交付变化后（先 fetch 所需提交与 tags）
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-实际编号 finish --github
```

新需求用 create --title 生成，续接原卡不要重复创建。历史需求不补同步，--all 只处理结构化 v3 卡；日常只指定本需求。

## 提交与远端证据

实施提交写独立尾注 `Requirement: REQ-实际编号`；提交须按 [REVIEW](REVIEW.md) 审查并获授权。提交后同步关联 SHA；生成记录允许随下一次正常提交归档，需要立即归档时只审记录差异。归档不加实施尾注，不循环记录自身 SHA。最终说明未关联或未归档文件。

实际 PR 使用 `link-pr --url https://github.com/团队/仓库/pull/123` 关联。--github 通过 gh 只读核对 PR 状态、提交集合和 merge SHA；squash 使用已核实的合并提交判断发布包含关系。无 PR 的直接提交不冒充 PR 已合并。

本地标签只是候选；只有远端同名标签与本地一致、正式非草稿/非预发布 Release 包含全部实施提交（或核实的合并提交）才标已发布。网络、权限或对象缺失如实标未核实；同一提交集合的普通本地同步保留上次远端证据及时间，不代表本轮联网核对。工具不自动 fetch、commit、push 或发布。

GitHub Release 与 App Store/TestFlight 分开，业务发布见 [APP-RELEASE](APP-RELEASE.md)。编号关联纠错可用 link-commit / exclude-commit --commit 确切SHA --reason 原因，不改共享历史；仅按明确需求使用，不作为日常步骤。
