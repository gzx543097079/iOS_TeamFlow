# Demo 页面预览（模拟器）

来源：iPhone 17 Pro / iOS 26.5，实际 XCTest 截图。对应验证 [result.json](../../project-checks/20260914T095703Z-529053dd/result.json)。Debug 7 单元 + 3 UI，Release 7 单元通过。Codex 已检查中英文排版、浅色/暗黑对比和导航返回文案；不代替团队视觉验收。

| 页面 | 截图 |
| --- | --- |
| 中文商城 | [查看](shop-chinese.png) |
| 横屏安全区 | [查看](shop-landscape.png) |
| 英文商城 | [查看](shop-light.png) |
| 暗黑商城 | [查看](shop-dark.png) |
| 设置 | [查看](settings-chinese.png) |
| 外观选项 | [查看](appearance-dark.png) |
| 关于我们 | [查看](about-chinese.png) |
| 商品详情 | [查看](product-detail.png) |

支持的操作：商城分类 → 商品详情 → 加入演示购物袋 → 返回查看/左滑移除；首页右上角设置 → 语言/外观/关于我们。购物袋仅本次运行有效；无真实订单或支付。

验证范围为此模拟器；未声明已经在最低 iOS 14 真机运行，也未测试超大字号。
