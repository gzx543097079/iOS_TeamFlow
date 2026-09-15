# Scene 生成规则核对

- 源仓库全量工具检查：115 项通过，见 workflow-checks.log。
- 完整包和独立 Skill 包：新专题及入口/模板/项目检查/提交审查文件均存在，专题字节与源码一致，见 distribution-check.json；打包输出见 package.log。
- 静态路径：新 UIKit（Swift/OC）→ WORKFLOW/启动模板 → APP-LIFECYCLE → 有效 Scene Manifest、真实代理和 UIWindowScene 窗口；SwiftUI App → App/Scene，不强加手工 SceneDelegate。
- 生成后验证：Debug/Release 成品配置及实际窗口、冷启动/前后台/重启、启动日志；不足时未验证。提交审查 correctness 引用同一专题。
- 范围边界：普通既有页面变更不强制迁移，扩展 Target 不套用主 App 配置，多窗口与最低系统依已确认范围；无额外人工审批。
- 本次为规则、链接、分发及静态适用路径验证，不是模型自动遵守证明，也未新建 OC/SwiftUI App 实测。已修复 UIKit Demo 的实际证据见 logs/project-checks/20260915T022354Z-251063a1/result.json；本轮 App 输入未改变，不重复运行。
