# 默认 RTL 与 2.1.2 源码验证

时间：2026-09-14T17:26:15+08:00

- `python3.12 scripts/run_workflow_checks.py --full`：113 项通过，36.677 秒，退出码 0；覆盖当前版本的分发、模板落地、消费升级与门禁。日志 /tmp/teamflow-2.1.2-full.log，SHA256：8982748a19472f1e79bdf8500d6d8266c0208c70c48801ac8dbaad578588c8a7。
- Skill 校验、diff 格式检查通过。VERSION、teamflow.json 与 README 当前版本对齐 2.1.2；README 区分源码版本与已有 2.1.0 Release 下载入口。
- 中文注释与日志在前两项需求中独立提交；日志组件和原生检查输入未变化，复用 validation-logging.md 中 OC/OC++/Swift Debug/Release 运行、iOS SDK 编译和实际混编工程两配置构建证据。

## 规则语义核对

| 场景 | 核对结果 |
| --- | --- |
| 新 App 仅启用 en、zh-Hans | 仍需 RTL 布局支持及验证，ar 行保持未启用，不增加翻译 |
| OC/Swift UIKit 页面 | 语义约束、方向边距、natural 文本对齐，手工绘制/手势读取实际界面方向 |
| SwiftUI 或混合容器 | 语义对齐及 layoutDirection，桥接不硬编码 LTR |
| 返回图标与照片/地图/播放内容 | 按语义决定镜像，不统一翻转或重复镜像系统资源 |
| 混合数字、邮箱、URL | 不反转字符串、不强制整页 LTR，按内容语义局部处理 |
| 未启用阿拉伯语，进行 UI 验证 | 用测试容器强制 RTL 并确认实际方向；不能仅改 locale 或将 RTL 标不适用 |
| 生产环境 | 不含验证用全局强制方向；正常按系统与界面语义决定方向 |

Apple 依据核对：UIView semanticContentAttribute、SwiftUI LayoutDirection、WWDC22 Get it right (to left)，链接已写入 UI 规范。上述为规则一致性检查，不宣称未生成的业务页面已通过 RTL 运行验收。本次只改工作流规范与模板，无 App UI 改动，不运行无关 Demo。

仅创建第三次需求提交，按用户授权推送，不创建 Release 或移动标签；本需求提交后生成交付记录待下次归档，不为归档额外增加提交。
