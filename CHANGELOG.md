# 版本记录

## 未发布

## 1.6.2

来源：用户要求修复完整工作流审查发现，并按影响范围测试；证据漏洞已用源码回归复现，尚未在真实消费项目验证提速。

- CI 历史证据按交付版本与当前检查输入复核，不再放行同路径后续未测修改、删除或依赖变化。
- AC 确认绑定范围和条件文字，改写后取消旧勾选及用户确认；旧卡保守兼容，未变化的确认保留。
- 新 v6 部分证据只绑定已选检查的完整依赖；保留 v4/v5 证据复核。
- 拆分 CLI 输出、参数定义与检查历史模块，补齐共享依赖触发及分发清单。
- Godot 示例改为一次导入加串行模块测试，全套测试仅手动运行；新增 `--test-only` 跳过重复导入。
- 统一局部视觉验收范围，分离日常验证与配置迁移路由，补齐 UIKit/SwiftUI 等上下文预算场景。

## 1.6.1

来源：用户要求发布已合并的工作流精确触发与验收修复（REQ-20261025-1f64）。

- 按 check covers 精确触发 workflow 检查，配置语义变化精确触发受影响检查。
- 阻断未覆盖工程改动，修复 profile covers 验收边界漏洞。
- 文档改动纳入 token 预算检查，纯 Markdown/RST 文档提交可直接通过。
- 合并 workflow-docs，拆分检查模块并清理 CHECKS 与 WORKFLOW 的重复规则。


来源：用户反馈改首页效果时视觉检查与构建耗时很长（REQ-20261025-5427），未实测。

- iOS 视觉证据优先安装同一代码已构建的 Debug 产物，否则复用同一 DerivedData 增量构建，不 clean；调样式期间可用 Preview 迭代，定稿后只构建安装一次；启动参数直达目标页面。
- 视觉 AC 截一轮后用 `--wait-user` 交用户确认，只在发现实际缺陷时补截受影响页面。
- `doctor`「验证配置形态」对日常 profile 中最近实际执行超过 180 秒的检查给出拆分提示（不计需处理，来源 REQ-20261025-b778：颜见 `debug-unit` 全套测试 489/538 秒）；CHECKS 与 iOS Skill 写明日常用编译加按模块测试，全套单元/UI 测试放 manual profile 并约定运行时机。
- 本地化：目标语言惯用的外文词、缩写和品牌名（如中文里的“Ta”“App”）可以保留，不因值含其他文字或与开发语言相同判为漏译；整句未翻译仍须修正（用户要求，REQ-20261025-7c38）。
- iOS 设计变量改为【团队强制】：字体、圆角、颜色、间距只在设计变量模块写字面量；安装包新增 `check_design_tokens.py` 与 DESIGN-TOKENS 说明，支持模块路径、规则子集、自定义正则与基线（用户要求，REQ-20261025-d172）。
- 本仓库 `workflow` 日常检查按模块拆为 7 组（需求 CLI、项目检查、诊断与安装、模块索引、iOS 脚本、Godot 脚本、打包与分发），各配 covers/inputs 并以 4 路并行运行；`run_workflow_checks.py` 支持按测试文件运行，回归测试要求每个测试文件恰好归属一组（来源 REQ-20261025-50aa：原单组 194 个测试串行约 73 秒，改任意文件都整组执行）。
- 打包函数支持输出目录，测试改为打包到临时目录，不再写入或覆盖仓库 `dist/`；Godot 扩展测试的临时工程不再建在仓库根。`workflow-release` 打包行为不变。
- 按模块精确触发：profile 可设 `trigger: "covers"`，检查只按自身 covers 触发，inputs 仅用于证据指纹与缓存；修改验证配置只触发执行语义变化的检查；check covers 自动并入其 inputs，不再要求重复声明。本仓库 `workflow` 启用该模式并重分 8 组，`workflow-docs` 并入为 `tests-docs`（含 token 预算），改模块索引只跑 tests-module、改单个平台脚本只跑对应平台组、改文档只跑 tests-docs（来源 REQ-20261025-1f64：此前 tests-package 依赖整个仓库，任意改动必跑，改任一核心脚本触发 5 组）。
- 修复验收漏洞：显式使用未声明 check covers、但有 profile covers 的 profile 时，范围外工程改动不再能通过 `req complete`（此前可用 `--profile workflow-docs` 完成含代码改动的需求）；需求模板与 VERSION 不再被路由为纯文档验证；文档改动会运行 token 预算护栏。
- 提交钩子对仅含 `.md`/`.rst` 的暂存（不含需求卡）直接放行，规则不再引导用 `git commit --no-verify` 整体绕过钩子；`.txt` 仍须证据。
- CHECKS 删去与 WORKFLOW 重复的规则句（后台等待、提交不升级全量、Release 仅显式、证据复用）。
- CHECKS 拆出[验证配置与迁移](.agents/teamflow-core/references/CHECKS-CONFIG.md)（配置字段、示例与「从全量脚本迁移」），常读的 CHECKS 只保留运行、验证强度与证据；`doctor` 迁移提示改指 CHECKS-CONFIG。

## 1.6.0

来源：用户纠正——升级到 1.5.0 后 Slipwise 的日常 profile 仍是单个全量检查（`check_app.py` 内含 Release 模拟器构建，与 `cloud-release` 重复），未声明 check covers，每次整组执行（REQ-20261025-1ec0）。

- `doctor` 新增「验证配置形态」：日常（非 manual）profile 的命令或其引用的项目脚本含 Release 构建为需处理，并列出同样含 Release 构建的其他 profile；未声明 check covers 为提示。
- `upgrade` 完成后用新核心复核，旧形态时报告“验证配置待迁移”；升级仍不改写项目脚本，INSTALL 规定在同一次升级任务中另建卡迁移，CHECKS 新增「从全量脚本迁移」步骤。从旧版升级时由旧核心执行升级，本次提示需升级后运行 `doctor` 看到。

## 1.5.0

来源：颜见会话实测（{{ACCOUNT_15skr24k}}）：01:35–03:18 UTC 长耗时约 76 分钟，约 64 分钟为 Agent 固定时长 sleep 轮询，约 10 分钟为绕过 TeamFlow 直接运行全套 xcodebuild test，TeamFlow 验证约 11 分钟；尚未在消费项目复测；合并方式规则来自用户纠正（REQ-20261024-2f7a）。

- 同一 profile 上次运行失败后，再次运行只执行失败项与指纹变化项，通过项复用；不要求 `incremental`，`cache: false` 与 `--rerun` 例外。
- `verify run` 与 `req complete` 开始前输出执行/复用检查、按最近实际耗时估算的预计时间与结果路径；报告记录 `estimated_seconds`。
- 合并 PR 默认使用 Merge（保留合并提交），不 squash 或 rebase，用户明确指定其他方式时除外（用户纠正，REQ-20261024-2f7a）。
- 规则：长验证后台运行并等待完成通知，不用固定时长 sleep 轮询；调试只运行失败用例，不在 TeamFlow 外重复全套测试。

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
