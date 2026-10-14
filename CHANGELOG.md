# 版本记录

## 1.0.0

首个正式版本。此前的内部迭代不再保留兼容与迁移路径。

- 三种安装模式：iOS 原生、Godot、Godot + iOS；安装包解压到项目根即可使用，已有项目用 `unzip -n` 加 `setup` 合并入口。
- 需求卡、AC、状态与证据：证据指纹绑定 profile 命令、输入文件内容与需求语义；`git check` 与 `git ci` 核对提交内容就是验证过的内容。
- 授权边界：Git 与 App／游戏外部动作只按用户明确目标执行；安装包附带 Claude Code 与 Codex 的[宿主权限](.agents/teamflow-core/references/INSTALL.md#宿主权限)配置兜底。
- iOS 新 App 默认使用 SwiftUI App 生命周期，需要时按页面嵌入 UIKit。
- 轻量改动通道、方案确认检查点、并行与子 Agent 规则；人工 AC 由用户确认并以 `--user-confirmed` 记录。
- `upgrade` 按安装清单识别本地改动；团队定制层 `.agents/team/` 不被覆盖。
- 本仓库不再内置 Demo，实际接入以独立试用项目验证，见[内测试用记录](docs/TRIAL.md)。
- 按两次真实项目试用修复：首次提交与自动选择 profile 不再要求覆盖 TeamFlow 安装文件；`doctor` 不重复报缺配置，进行中卡片不计为需处理；待用户验证时提示 `--user-confirmed`。
- Godot：新增 [iOS 导出构建脚本](.agents/skills/Godot/scripts/export_ios.py)，导出前一次列出图标、ETC2/ASTC、Team ID 等缺项，按模板真实架构做模拟器构建；`verify_godot.py` 支持 `--allow-error` 放行测试明确预期的引擎错误。
