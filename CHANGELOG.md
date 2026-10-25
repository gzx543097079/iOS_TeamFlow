# 版本记录

## 未发布

来源：用户纠正（REQ-20261024-2f7a）。

- 合并 PR 默认使用 Merge（保留合并提交），不 squash 或 rebase，用户明确指定其他方式时除外（用户纠正，REQ-20261024-2f7a）。

## 1.4.0

来源：用户关于真实项目验证等待的反馈与“有触发才检查、日常不跑 Release”的明确纠正；回归验证不等同于消费项目提速实测。

- check `covers` 与依赖 `inputs` 决定触发；未触发明确跳过，未覆盖工程改动在运行前阻断。实际检查集合进入证据并用于提交、历史交付及 CI 覆盖，空选择不冒充通过。
- profile `manual: true` 排除自动选择，Release 只在显式指定时执行；旧大脚本须在项目中拆出日常/发布入口，升级不自动改写项目配置。
- `parallelism` 默认 1，独立检查显式并行；修正开发分支 c19114e 默认并行破坏产物依赖及后置短超时失效的问题。每项独立计时。
- 可选 `incremental` 复用未变检查，补齐命令、超时、可执行位、需求语义及全部检查依赖；最新失败不能回退旧通过，强制重跑绕缓存。suggest 显示触发、跳过与耗时。
- 源码 ZIP 补齐维护回归测试和验证配置；安装包仍不含维护测试。纠正 TRIAL 中“勾选 AC 或写决策导致失效”的错误解释。

## 1.3.0

来源：用户要求的工作流复查（REQ-20261024-b714），每项均有修复前失败、修复后通过的回归测试；尚无新的真实项目试用记录。

- 人工证据与 `git check` 统一使用文档白名单（`.md`、`.rst`、`.txt`）：Godot 脚本、场景、导出预设及各类配置不再能仅凭人工文字完成验收。
- 提交钩子不再绑定 profile：`setup --git-hook` 不带参数，钩子也接受仅含文档的人工证据，优先核对本次暂存与进行中的卡，不再逐张哈希历史卡；仅文档暂存时提示轻量改动用 `git commit --no-verify`。1.2 及更早的钩子仍可运行，`doctor` 提示迁移；源码仓库执行 `setup --git-hook` 只装钩子，不再写入托管入口。
- 自动选择 profile 计入本需求带 `Requirement:` 尾注的已提交改动，阶段提交后不再误选窄范围 profile，全部提交后也能选择；`verify suggest` 新增 `--requirement`。
- `req state --reopen-ac` 重开完成的需求：须填写原因，取消指定 AC 并移出 `user_confirmed`，避免下一次验收复用证据直接判回完成。
- `AGENTS.md` 只在托管区块外的项目规则未改动时、宿主权限文件只在与原版模板一致时视为安装文件；`git check` 列出暂存配置中未经本次证据执行的其他 profile 变化。
- `git ci` 要求 PR 内的非文档改动由本 PR 需求卡的有效证据覆盖，只有代码、没有卡的 PR 不再通过；`req pr` 为未完成的卡标注 `[阶段]`。
- WORKFLOW 准确描述工具对正文的写入范围；validate_workflow 新增文档命令参数与 CLI 一致性检查。

## 1.2.1

- 修复 v1.2.0 分发文档（INSTALL、COMMANDS、Godot 接入说明）残留旧版本示例的问题；validate_workflow 新增版本示例一致性检查，拦截发版时遗漏的旧版本示例。
- 提交钩子门禁不再限定单一 profile：复用仍有效且覆盖整个暂存区的自动证据，多 profile 仓库的发版与文档提交不再被误拦。

## 1.2.0

- 新增[产物存放](.agents/teamflow-core/references/ARTIFACTS.md)规则：实施中产生的非工程文件按类别存入项目内目录、随写随建，覆盖设计原稿与 UI 预览、生成素材、报告、发布素材、一次性脚本、构建导出产物、验证截图等常见类别；已有工程在项目现状模板登记自己的目录约定。

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
