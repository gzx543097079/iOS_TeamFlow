# 验收对象与交付同步

需求卡是当前状态和 AC 结果的唯一人工入口。delivery 保存验收对象绑定及 PR/Release 等外部事实；Requirement 提交关联和交付概览从 Git 与当前卡片动态生成，不手填第二套 development 或 Git 状态，也不维护 `requirements/DELIVERY.md`。

## 验收绑定

这些命令由 Codex 执行，成员无需背诵编号和参数。实际验收完成后更新卡片，再选择一种方式：

```sh
# 自动检查：引用已通过的真实结果，可重复 --result；复用 profile 的输入范围
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-实际编号 finish --accept --result logs/project-checks/运行编号/result.json
# 人工验收：范围覆盖源码、工程配置、资源、锁文件及相关脚本
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-实际编号 finish --accept --inputs App tests
```

--result 会核对测试与当前输入一致，不能引用失败或过期结果；不能同时 --inputs 重复指定范围。混合验收时，profile 输入应覆盖受影响范围，人工/团队确认记在 AC。没有测试结果的人工验收才直接选范围，未指定则使用 Git 可见工作区；后续沿用原范围。测试与验收共用目录选择规则，排除 Git 元数据、缓存、忽略的生成文件和证据；requirements 下管理记录不参与实施指纹。AC 或证据真实性仍由语义审查负责。

普通 finish 不批准或覆盖验收，也不用于同步卡片状态或提交 SHA；未提交验收仍比较工作区，变化必须实际复核并更新 AC 后 --accept。代码变化但 AC 证据未更新时拒绝接受。

实施提交含已验收内容时，工具根据 Requirement trailer 和内容指纹动态定位确切提交，无需把 SHA 回写记录。其他需求随后修改同目录不影响原验收；新增本需求实施提交需匹配已验收内容，否则复核。明确续接或发现回归时先重开卡片，只复核实际受影响 AC。历史验收证明当时版本，不代表当前产品永远正确。

## 同步时机

状态和 AC 直接更新完整需求卡，不调用 finish；轻量卡始终不调用 finish。完整卡实际验收完成时执行一次 --accept，它已包含绑定和写后核验，不再追加普通 finish/--check。只有 PR、Release、人工关联纠错等外部事实变化时再写交付记录；--check 仅用于独立只读排错。

```sh
# 实际远端交付变化后（先 fetch 所需提交与 tags）
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-实际编号 finish --github
```

产品/App 需求用 create --title 生成；新缺陷使用 create --template bug-fix --title，见 [Bug 修复与历史](BUGFIX.md)。仅低风险文档、版本号或纯记录调整可用 create --template lightweight --title；轻量卡不得用于产品行为、App 源码、Bug、权限、数据、商业规则或重要交互。续接原卡不要重复创建。历史需求不补同步，--all 只处理需要验收绑定的结构化 v3 卡。

## 提交与远端证据

实施提交写独立尾注 `Requirement: REQ-实际编号`；完整卡与轻量卡均可关联。提交须按 [REVIEW](REVIEW.md) 审查并获授权。提交后无需 finish：status 和动态概览直接查询 trailer，验收封存通过内容指纹定位提交，不产生纯归档提交。

实际 PR 使用 `link-pr --url https://github.com/团队/仓库/pull/123` 关联。--github 通过 gh 只读核对 PR 状态、提交集合和 merge SHA；squash 使用已核实的合并提交判断发布包含关系。无 PR 的直接提交不冒充 PR 已合并。

本地标签只是候选；只有远端同名标签与本地一致、正式非草稿/非预发布 Release 包含全部实施提交（或核实的合并提交）才标已发布。网络、权限或对象缺失如实标未核实；同一提交集合的普通本地同步保留上次远端证据及时间，不代表本轮联网核对。工具不自动 fetch、commit、push 或发布。

GitHub Release 与 App Store/TestFlight 分开，业务发布见 [APP-RELEASE](APP-RELEASE.md)。编号关联纠错可用 link-commit / exclude-commit --commit 确切SHA --reason 原因，不改共享历史；仅按明确需求使用，不作为日常步骤。

## 日常读取与历史

`delivery.py --requirement REQ-实际编号 status` 只读组合当前卡片、Git trailer 和已保存外部事实，不改状态或联网；只有需要追溯验收/外部事实事件时加 --history。新增事件保存字段变化与删除项；历史可按顺序重建，既有完整事件不改写。日常不要把全部 JSON 历史加载进上下文。


## 需求编号与排序

新编号示例：`REQ-20260912-103015123Z-a1b2c3d4`，表示 UTC 2026-09-12 10:30:15.123 创建；末尾 8 位随机码用于降低多人同毫秒创建的冲突概率。同目录创建使用排他写入，撞号自动重试，不覆盖文件。不需要共享递增计数器；跨分支仍是概率去重，并非中心化唯一性保证。

文件名按字典序即创建时间升序，同毫秒按随机码确定稳定顺序。各机器需校准时钟；此顺序不保证跨机器的严格因果先后，也不代表优先级或依赖关系。时间一经生成不因更新或验收而改变。

```sh
python3 .agents/skills/ios-team-flow/scripts/delivery.py list
python3 .agents/skills/ios-team-flow/scripts/delivery.py list --reverse
python3 .agents/skills/ios-team-flow/scripts/delivery.py list --json
python3 .agents/skills/ios-team-flow/scripts/delivery.py list --type bug-fix
python3 .agents/skills/ios-team-flow/scripts/delivery.py list --type lightweight
python3 .agents/skills/ios-team-flow/scripts/delivery.py list --delivery
```

列表直接读取当前需求卡，未执行 finish 的新卡也可见；支持 Git 初始化前查看。`--type` 可筛选普通需求、Bug Fix 或轻量卡；Markdown 输出的卡片链接相对项目根。标题和状态随卡片更新，不维护人工索引。默认按创建时间升序，--reverse 仅反转显示，保留升序序号。`list --delivery` 只读生成交付概览，提交事实来自当前 Git trailer，PR/Release 来自最近一次外部核对。

序号为当前集合中的浏览位置，合并更早需求后可能变化；文件名、引用、父子关系及 Requirement 尾注使用固定完整编号，不能使用序号。所有 list 形式都不写文件或联网；动态概览不维护第二套人工状态，也不产生合并热点。

本次直接采用新编号，不提供旧数字/UUID 编号兼容或自动迁移。旧需求及交付原始文件保留，当前列表和动态概览只收录新格式；旧 `requirements/DELIVERY.md` 可从 Git 历史查看，不再更新。不要批量重命名旧文件后声称其历史提交关联仍有效。

单张新格式需求卡日期无效、内容无法解码或读取被拒绝时，列表跳过该卡并在标准错误中提示具体文件与原因；标准输出保持 Markdown 表格或 JSON 数组，查询退出码为 0。全部卡异常时返回空列表并保留警告，空列表不代表没有异常需求。动态概览末尾保留异常清单，修复后重新查询。根目录错误仍使查询失败；直接操作无效编号仍拒绝，异常卡不会因此获得验收。
