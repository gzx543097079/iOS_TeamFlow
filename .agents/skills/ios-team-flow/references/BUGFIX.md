# Bug 修复与处理历史

收到明确缺陷时先定位已有需求。同一缺陷续接原卡；新缺陷由 Codex 创建专用卡：

```sh
python3 .agents/skills/ios-team-flow/scripts/delivery.py create --template bug-fix --title "缺陷标题"
```

命令返回 `requirements/REQ-实际编号.md`。使用 [Bug Fix 模板](templates/bug-fix.md)，保留统一编号、状态、AC、列表、审查与交付流程；普通需求的 create 默认行为不变。

## 修复与记录

1. 填写环境、最小复现步骤、实际/预期结果和影响；引用修复前证据。无法复现时写清已排查的条件、缺失信息及下一步，不把猜测作为根因或将缺陷标记完成。
2. 在“根因与修复”记录已验证原因、最小改动与回退方式；按真实风险选择关联回归。修复前后尽量使用同一复现条件；环境变化需明确说明。
3. 在卡片“处理历史”追加有时间、处理人和证据的事实，保留失败尝试、复核及回退。没有实际变化不写重复进度；当前状态和验收结果只维护顶部与 AC 表。
4. 同一缺陷重现时续接原卡并重开受影响 AC，保留旧处理历史；独立根因另建卡并双向引用。按 [DELIVERY](DELIVERY.md) 同步，提交前按 [REVIEW](REVIEW.md) 审查。涉及可复用流程缺陷时按需使用 [EVOLUTION](EVOLUTION.md)，普通业务 Bug 不自动修改通用规范。

## 历史在哪里

| 内容 | 位置 |
| --- | --- |
| 单个 Bug 的复现、根因、修复、失败尝试与复核历史 | `requirements/REQ-实际编号.md` 的“处理历史” |
| 测试原始日志、截图与测试对象 | `logs/`，卡片引用实际文件 |
| 提交前语义审查与修复复查 | `logs/reviews/` |
| 提交、PR、Release 事实及同步历史 | `requirements/delivery/REQ-实际编号.json`，由工具生成 |

需要集中浏览时在项目 `requirements/BUGFIX-HISTORY.md` 只维护标题和卡片链接，不复制状态、根因或验收结果。Codex 首次处理缺陷时按需创建该索引，新缺陷新增链接、续接原卡不重复插入；create 命令只生成卡片，不自动改写索引。历史需求只引用已有真实记录，不为补目录伪造旧过程或新建重复卡。

查阅某卡的交付同步历史（区别于人工修复过程）：

```sh
python3 .agents/skills/ios-team-flow/scripts/delivery.py --requirement REQ-实际编号 status --history
```

尚未 finish 的卡片没有交付同步记录，直接读取卡片中的处理历史即可。
