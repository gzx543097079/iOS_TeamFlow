# 版本记录

## 1.1.2

- 验收优先复用有效证据，提交钩子仅复核暂存证据；profile 新增 covers 与 priority，分离改动适用范围和失效依赖，避免重复全量验证。

## 1.1.1

- 默认安装不再激活额外宿主审批规则；新增可选严格模式及旧模板显式迁移，保留自定义权限，升级提示已有规则。

- 修复零命令安装后 TeamFlow 生成 Python 字节码缓存、首次提交检查误报未覆盖文件的问题；源码与分发入口均禁止自身写缓存，消费测试不再依赖宿主缓存环境变量。
- 补强项目长期结论的按需读取、就地更新与失效处理：复用已有资料及项目现状索引，不新增记忆文件或全量历史加载步骤。

## 1.1.0

- 融合 [impeccable](https://github.com/pbakaus/impeccable) 的原生 UI 设计方法：新增 iOS [UI 评审与打磨](.agents/skills/iOS/references/UI-REVIEW.md)（五维度 0–4 评分、P0–P3 分级、打磨顺序、模拟器截图与外观核对）；UI 规范补充平台一致性与常见痕迹；Godot 增加游戏 UI 评审；工程现状模板增加产品与设计约定。来源与许可见[第三方说明](.agents/teamflow-core/references/THIRD-PARTY.md)。

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
