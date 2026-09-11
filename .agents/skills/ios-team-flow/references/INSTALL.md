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

脚本会追加 AGENTS.md 的带标记区块，明确引用项目内 Skill，生成 .agents/teamflow.json 与 scripts/review_gate.py，创建 requirements/、logs/reviews/。保留原 AGENTS.md 正文；相同版本重复运行不重复追加。脚本拒绝从其他项目或用户级安装目录直接接入本项目。

脚本支持版本升级：未修改的托管内容自动更新，新版未修改的内容保留团队定制；双方都修改同一托管部分且内容不同才报告冲突。来源未知的同名脚本、损坏的标记/接入记录、降级或符号链接会在写入前退出。非空 AGENTS.override.md 会覆盖普通入口，所以也先报告冲突，需要将入口合入实际生效的指令文件。项目需要使用 Git 审查时应已是 Git 仓库，脚本不自动 git init。

## 空项目接入（没有 .agents/skills 时）

空文件夹也可以作为项目根目录，不需要提前创建 Xcode 工程。在终端进入该文件夹后，先创建 Skill 存放目录：

```sh
mkdir -p .agents/skills
```

将独立安装包解压，把里面完整的 `ios-team-flow` 文件夹放入刚创建的 `.agents/skills/`。此时目录应为：

```text
项目根目录/
└── .agents/
    └── skills/
        └── ios-team-flow/
            ├── SKILL.md
            ├── references/
            └── scripts/
```

注意保留完整目录，不要只复制 SKILL.md，也不要多套一层 ios-team-flow。然后仍在项目根目录执行一次：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

脚本会生成 AGENTS.md、.agents/teamflow.json、scripts/review_gate.py，并创建 requirements/、logs/reviews/，不会提前创建业务工程。

接入后在 Codex 打开该项目根目录，开始新会话，直接描述要做的产品。新项目会先按模板整理需求文档交团队确认，确认后再在 App/ 下创建 iOS 工程。后续无需重复接入或每次点名 Skill。

尚未初始化 Git 不影响接入。第一次使用提交审查前，需要在该项目根目录初始化 Git：

```sh
git init
```

以上 git init 只适用于尚未纳入 Git 的新目录；若已有仓库或位于已有仓库内，使用既有 Git 根目录，不创建嵌套仓库。执行这些步骤不会自动提交或上传 GitHub。

## 后续使用

从项目根目录打开新的 Codex 会话。AGENTS.md 已要求在 iOS 实施与提交审查时读取本地 Skill，直接说“做一个订阅页”即可。规则属于指令约束，构建、lint 和提交拦截仍需对应工具或 hook。

```text
项目根目录/
├── AGENTS.md
├── .agents/skills/ios-team-flow/
│   ├── SKILL.md
│   ├── references/       # UI、语言规范、流程与模板
│   └── scripts/          # Skill 自带工具
├── .agents/teamflow.json
├── App/                  # 新工程，既有工程保留原名
├── requirements/
├── logs/reviews/
└── scripts/review_gate.py
```

项目 A 和项目 B 各有一份 Skill，版本与定制互不影响。需求、PRD、审查记录及工程写在项目对应目录，不写入 Skill 资源目录。

## 团队共享与升级

将 `.agents/skills/ios-team-flow/`、AGENTS.md、.agents/teamflow.json、scripts/review_gate.py 及脱敏需求日志一同提交。确认项目的 .gitignore 没有忽略 `.agents/`、requirements/ 或整个 logs/。团队成员克隆项目后即可获得同一份规范，不需要额外个人安装。

升级只针对当前项目，继续使用同一条命令，无需额外 `--upgrade` 参数：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

1. 先下载包含升级能力的新 Skill，比较并合并项目对 Skill 本身的定制，再放入当前项目。脚本不下载新版本，也不能恢复复制 Skill 时被覆盖的定制。
2. 在项目根目录运行上述命令。脚本读取已有 `.agents/teamflow.json`，更新版本并保存托管基线；保留记录中的其他团队字段。
3. `AGENTS.md` 标记区块外的内容原样保留。区块内与根门禁入口分别比较“上次生成基线、项目当前内容、新版内容”：项目未修改时自动更新；新版未修改时保留项目定制；项目已人工合并为新版内容也可通过。双方均改动且结果不同则提示具体冲突，不写入任何接入文件。
4. 更新已有文件前，脚本将即将替换的旧文件备份到 `.agents/teamflow-backups/upgrade-*/`，输出实际位置。检查差异、验证项目后提交接入记录、Skill 和入口；备份可能含团队规则，按项目管理要求保存，不加入通用分发包。
5. 同版本同内容重复运行不追加区块、不重复写文件或生成备份。不自动降级。不要手动删除或改写 `managed` 基线字段来绕过冲突。

**从 1.2.1 开始接入的项目可直接过渡**：即使旧接入记录没有基线，新脚本也内置了已发布 1.2.1 托管区块和门禁入口的指纹。首次升级会建立基线，后续版本继续使用该机制。

发生冲突时，先查看 Git 差异和团队定制，将团队专用规则移至托管区块外，或人工合并对应托管内容后重试；门禁的业务定制需合并到 Skill 内实际实现。保留备份，不删除整个 AGENTS.md。标记损坏、记录格式错误时从项目历史恢复再执行。升级命令使用当前项目本地 Skill，不切换至用户级或其他项目的版本。

源仓库和消费项目都直接维护 `.agents/skills/ios-team-flow/`，没有规范同步步骤。版本以 Skill 内 references/VERSION 为准，.agents/teamflow.json 记录项目接入版本。根 scripts/review_gate.py 只加载 Skill 内的门禁实现。

1.2.0 及更早的旧目录项目升级（不属于上述 1.2.1 基线迁移）：先比较旧 workflow/ 的定制规则与新 Skill，保留需要的修改；将原 workflow/teamflow.json 版本记录迁移到 .agents/teamflow.json，核对 AGENTS.md 入口和门禁加载脚本。接入脚本会报告旧入口或同名脚本冲突，不自动覆盖或删除旧目录。确认旧目录中没有项目资料、入口已改好并验证后，再删除旧 workflow/。历史需求和审查记录中的旧路径保留为当时的证据。

## 已有业务项目接入后

接入成功只代表入口配置完成。首次提出业务需求时，Codex 按 [已有项目流程](EXISTING-PROJECT.md) 识别本次目标并整理 requirements/PROJECT-CONTEXT.md；后续复用现状记录、核对相关变化，沿用项目实际技术栈和产品配置，不套用新项目默认值。
