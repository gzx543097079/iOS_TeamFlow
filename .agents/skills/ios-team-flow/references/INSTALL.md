# 项目级安装：每个项目接入一次

本工作流只采用项目级安装。完整 Skill 随项目保存，不依赖用户级 Skill 目录或原始分发仓库。Codex 的项目发现机制见 [官方说明](https://learn.chatgpt.com/docs/build-skills)。

## 首次接入

1. 将 `ios-team-flow-skill-vX.Y.Z.zip` 解压到临时目录。
2. 把其中完整的 `ios-team-flow/` 文件夹放入目标项目根目录的 `.agents/skills/`；已有 Git 仓库时使用 Git 根目录。最终必须存在 `.agents/skills/ios-team-flow/SKILL.md`。已有同名目录先比较版本和项目定制，禁止直接叠加覆盖。
3. 在目标项目根目录运行一次：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

也可以在放好文件后请 Codex “接入当前项目的 iOS 工作流”。不需要每次提需求都重复这句话。

脚本会在实际生效的指令文件中追加带标记区块（非空 AGENTS.override.md 优先，否则 AGENTS.md），明确引用项目内 Skill，生成 .agents/teamflow.json 与 scripts/review_gate.py，创建 requirements/、logs/reviews/。保留原 AGENTS.md 正文；相同版本重复运行不重复追加。脚本拒绝从其他项目或用户级安装目录直接接入本项目。接入后自动显示只读诊断：Python、Git 根目录、版本与入口、项目验证配置、忽略规则及可选本地 Hook；“接入成功”不等于业务验证已就绪。

脚本支持版本升级：未修改的托管内容自动更新，新版未修改的内容保留团队定制；双方都修改同一托管部分且内容不同才报告冲突。来源未知的同名脚本、损坏的标记/接入记录、降级或符号链接会在写入前退出。非空 AGENTS.override.md 存在时自动接入该文件，版本记录保存 instruction_file。后续入口切换时重新运行接入，保留旧文件正文，不主动删除旧规则；有效入口的托管标记损坏仍需修复。项目需要使用 Git 审查时应已是 Git 仓库，脚本不自动 git init。

空目录先 mkdir -p .agents/skills，再按上述步骤接入；不用提前创建 App。首次收尾前在未纳入 Git 的项目根 git init，已有仓库不嵌套。接入不提交、不上传。

## 接入后的只读诊断

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project . --doctor
```

不写文件、不执行配置里的命令、不联网、不安装依赖或 Hook。缺 Git 时先确认项目根再初始化；新项目待工程生成后补实际 profile，已有项目从既有 CI/构建说明提取配置。未安装 Hook 是可选状态，不冒充强制门禁已启用。工具内部不依赖 Python 忽略规则，仍建议合并 `__pycache__/`、`*.pyc`、`.agents/teamflow-backups/` 和实际构建输出到项目 .gitignore，保留团队既有内容。

当前阻塞项：Git 根或入口错误先解决；已有业务工程实施前配置实际验证，新工程建成后配置。未安装可选 Hook 不阻塞接入；升级与恢复仅在对应事件发生时阅读后文。

## 后续使用

从项目根目录打开新的 Codex 会话。AGENTS.md 已要求在 iOS 实施与提交审查时读取本地 Skill，直接说“做一个订阅页”即可。构建、lint 和提交拦截仍需对应工具或 Hook；大型项目的模块路由与 Git 增量由 `module_context.py` 和 `.agents/project-modules.json` 提供可执行能力。

```text
项目根目录/
├── AGENTS.md
├── .agents/skills/ios-team-flow/
│   ├── SKILL.md
│   ├── references/       # UI、语言规范、流程与模板
│   └── scripts/          # Skill 自带工具
├── .agents/teamflow.json
├── .agents/project-modules.json # 大型项目按需由工具建立
├── App/                  # 新工程，既有工程保留原名
├── requirements/
├── logs/reviews/
└── scripts/review_gate.py
```

项目 A 和项目 B 各有一份 Skill，版本与定制互不影响。需求、PRD、审查记录及工程写在项目对应目录，不写入 Skill 资源目录。

## 团队共享与升级

将 `.agents/skills/ios-team-flow/`、AGENTS.md、.agents/teamflow.json、scripts/review_gate.py 及脱敏需求日志一同提交。确认项目的 .gitignore 没有忽略 `.agents/`、requirements/ 或整个 logs/。团队成员克隆项目后即可获得同一份规范，不需要额外个人安装。

升级只使用下文完整 Skill 包预览、应用与恢复路径；日常不执行升级。版本固定在项目内，团队克隆后无需重新安装。

## 已有业务项目接入后

接入成功只代表入口配置完成。首次提出业务需求时，Codex 按 [已有项目流程](EXISTING-PROJECT.md) 识别本次目标并整理 requirements/PROJECT-CONTEXT.md；大型项目在实际触达模块时用 [模块增量工具](MODULE-CONTEXT.md) 建立 `.agents/project-modules.json`。后续先由工具核对命中模块变化，再读取必要代码；沿用项目实际技术栈和产品配置，不套用新项目默认值。

## 可选提交检查

业务项目验证命令配置见 [项目验证](PROJECT-CHECKS.md)，需求与提交、可选 PR 事实及发布关联见 [交付追踪](DELIVERY.md)。本地 Hook 需团队在每个克隆中显式安装，见 [Git 检查](GIT-CHECKS.md)；升级脚本不自动更改现有 Hook。

## 接入中断与恢复

新版接入脚本在 `.agents/teamflow-backups/upgrade-*/transaction.json` 保存接入前内容（含原来不存在的文件）和权限，逐文件原子替换；普通写入异常自动恢复。进程被强制终止时下次接入会提示先恢复，不能把多文件更新称为文件系统整体原子事务。

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project . --recover .agents/teamflow-backups/upgrade-实际编号/transaction.json
```

将路径换成实际提示的记录。恢复会先预检全部目标；发现人工修改时停止，先将差异另存并人工合并，不能强行覆盖。自动恢复失败时保留记录，修复磁盘/权限原因后重试。成功恢复可重复执行；保留创建的空目录，避免删除团队文件。

setup_project.py 普通接入事务恢复范围仅是实际指令入口、版本记录和根门禁入口，不包含手动替换的 Skill 文件。回退整个版本时还需从 Git 或原 ZIP 恢复对应 Skill；先保存团队定制。备份可能含项目内部规则，请按项目访问范围保管。旧版无 transaction.json 的备份需要人工对比恢复，不能使用此命令。

## 完整 Skill 包升级（默认预览）

此能力自 1.5.0 起提供。旧版项目没有升级脚本时，先将新版独立 Skill 包解压到项目外临时目录，使用其中 scripts/upgrade_skill.py。保留项目内旧 Skill，先核对下载包来自可信 Release 并用其 SHA256 文件验证完整性。原包是可执行工具；预检会在临时项目运行新版 setup 的只读计划，不应使用未知来源的包。

```sh
python3 /临时目录/ios-team-flow/scripts/upgrade_skill.py --project /项目根目录 --archive /下载/ios-team-flow-skill-v新版.zip --base-archive /下载/ios-team-flow-skill-v旧版.zip
```

首次完整升级必须提供与当前版本匹配的旧版原包作为三方比较基线，不能拿团队定制目录冒充原包。输出新增/更新/删除与冲突；默认不改项目文件。核对后给同一命令加 `--apply` 执行。首次成功后保存 `.agents/teamflow-skill-baseline.json`，后续可省略 --base-archive。

团队单独修改、新版未修改的文件保留；项目未修改的文件跟随新版更新或删除；双方同时修改则停止。冲突先在项目外副本中合并，然后加 `--resolutions /合并目录`，目录内保持 Skill 相对路径，例如 references/standards/swift.md。只对冲突项采用显式提供的合并文件，基线仍记录新版原包，下一次升级继续识别团队定制。

`--apply` 在同一事务中备份完整 Skill、两种指令入口、根门禁入口和版本/基线，再应用更新。写入失败自动恢复；恢复入口仍为 setup_project.py --project ... --recover <transaction.json>，此时恢复范围包含完整 Skill。恢复也会检查升级后是否有人工修改，不强制覆盖。

始终保留新版临时工具直到升级验收完成。恢复到旧版本后如需再次执行恢复，使用临时新版 scripts/setup_project.py；旧版本可能不支持完整事务格式。强制中断时，先确认无升级进程，使用新版恢复工具处理 prepared 事务，再移除 `.agents/teamflow-upgrade.lock` 空锁目录。备份留在项目 .agents/teamflow-backups，不进入通用包；升级不会安装或覆盖 Git Hook。
