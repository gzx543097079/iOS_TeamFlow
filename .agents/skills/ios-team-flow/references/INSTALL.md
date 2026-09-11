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

脚本会追加 AGENTS.md 的带标记区块，明确引用项目内 Skill，生成 workflow/teamflow.json 与 scripts/review_gate.py，创建 requirements/、logs/reviews/。保留原 AGENTS.md 正文；相同版本重复运行不重复追加。脚本拒绝从其他项目或用户级安装目录直接接入本项目。

有同名脚本、版本差异、定制区块或符号链接时预检退出，不覆盖已有内容。非空 AGENTS.override.md 会覆盖普通入口，所以也先报告冲突，需要将入口合入实际生效的指令文件。项目需要使用 Git 审查时应已是 Git 仓库，脚本不自动 git init。

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

脚本会生成 AGENTS.md、workflow/teamflow.json、scripts/review_gate.py，并创建 requirements/、logs/reviews/，不会提前创建业务工程。

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
├── workflow/teamflow.json
├── App/                  # 新工程，既有工程保留原名
├── requirements/
├── logs/reviews/
└── scripts/review_gate.py
```

项目 A 和项目 B 各有一份 Skill，版本与定制互不影响。需求、PRD、审查记录及工程写在项目对应目录，不写入 Skill 资源目录。

## 团队共享与升级

将 `.agents/skills/ios-team-flow/`、AGENTS.md、workflow/teamflow.json、scripts/review_gate.py 及脱敏需求日志一同提交。确认项目的 .gitignore 没有忽略 `.agents/`、requirements/ 或整个 logs/。团队成员克隆项目后即可获得同一份规范，不需要额外个人安装。

升级只针对当前项目：比较新旧 Skill、保留定制，合并接入区块和审查门禁，更新 workflow/teamflow.json，再验证并提交。版本不匹配时不得静默切换至其他位置的版本；setup_project.py 不提供盲目覆盖参数。开发阶段曾生成的用户级接入区块应先按差异迁移为显式项目路径。

源仓库以 workflow/ 为规范单一源，scripts/build_skill.py 生成 Skill 内资源并在发布前校验；消费项目直接使用完整 Skill，不需要源仓库或其构建/发布工具。消费项目的规范定制随自己的 Skill 提交维护。
