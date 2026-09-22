# Bug Fix 历史入口

本页只链接已有真实记录，不复制当前状态或验收结论。单个 Bug 的新增处理过程写在对应 `requirements/REQ-实际编号.md` 的“处理历史”；旧记录保留原结构，不补造过去的操作。

## 已有缺陷处理记录

| 主题 | 原始记录 |
| --- | --- |
| Demo Release 单测无法访问内部类型 | [日志接入卡：过程与决策](REQ-20260914-093346895Z-af337132.md#过程与决策) |
| 切换中文后返回按钮仍为英文 | [商城整合卡：过程与决策](REQ-20260914-093347091Z-29ecd886.md#过程与决策) |
| 商城横屏安全区约束问题 | [商城整合卡](REQ-20260914-093347091Z-29ecd886.md) · [审查发现](../logs/reviews/4e4a1a9950f70a8786000c15b89ea344cd29113bab4d7f7aab7e6475d12782f3.json) · [复核记录](../logs/reviews/5ace650c9e0cca0634fcaca6deeeb6e335a63cc6c74e21c2928b549321cc7e81.json) |

## 当前缺陷列表

从项目根执行 `python3 .agents/skills/ios-team-flow/scripts/delivery.py list --type bug-fix`，直接从缺陷卡生成最新标题、状态和链接；新建、改名及重开均无需维护本页。上表仅保留旧结构历史参考，不再追加新卡。

模板：[bug-fix.md](../.agents/skills/ios-team-flow/references/templates/bug-fix.md)；规程：[BUGFIX.md](../.agents/skills/ios-team-flow/references/BUGFIX.md)。
