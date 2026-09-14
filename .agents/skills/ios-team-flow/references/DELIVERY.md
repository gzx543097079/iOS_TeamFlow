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

## 日常读取与历史

`delivery.py --requirement REQ-实际编号 status` 只读当前快照，不改状态或联网；只有需要追溯时加 --history。新增事件保存字段变化与删除项，当前快照保存完整状态；历史可按顺序重建，既有完整事件不改写，不丢失证据。日常不要把全部 JSON 历史加载进上下文。


## 需求编号与排序

新编号示例：`REQ-20260912-103015123Z-a1b2c3d4`，表示 UTC 2026-09-12 10:30:15.123 创建；末尾 8 位随机码用于降低多人同毫秒创建的冲突概率。同目录创建使用排他写入，撞号自动重试，不覆盖文件。不需要共享递增计数器；跨分支仍是概率去重，并非中心化唯一性保证。

文件名按字典序即创建时间升序，同毫秒按随机码确定稳定顺序。各机器需校准时钟；此顺序不保证跨机器的严格因果先后，也不代表优先级或依赖关系。时间一经生成不因更新或验收而改变。

```sh
python3 .agents/skills/ios-team-flow/scripts/delivery.py list
python3 .agents/skills/ios-team-flow/scripts/delivery.py list --reverse
python3 .agents/skills/ios-team-flow/scripts/delivery.py list --json
```

列表直接读取当前需求卡，未执行 finish 的新卡也可见；支持 Git 初始化前查看。默认按创建时间升序，--reverse 仅反转显示，保留升序序号。生成交付概览同样包含序号、创建时间、标题和当前状态；Git 事实仍取最近一次同步记录。

序号为当前集合中的浏览位置，合并更早需求后可能变化；文件名、引用、父子关系及 Requirement 尾注使用固定完整编号，不能使用序号。列表不写文件或联网，交付概览随 finish 更新，不维护第二套人工状态。

本次直接采用新编号，不提供旧数字/UUID 编号兼容或自动迁移。旧需求及交付原始文件保留，当前列表和交付概览只收录新格式；旧概览可从 Git 历史查看。不要批量重命名旧文件后声称其历史提交关联仍有效。
