# iOS 团队工作流入口

本仓库使用中文协作，是工作流工具仓库，不属于新建 iOS 产品。开始读取 `.agents/skills/ios-team-flow/references/WORKFLOW.md`；按本次范围加载专题，已读且未变化不重读。

<!-- ios-team-flow:start -->
## iOS 工作流

本项目采用仓库内的 `.agents/skills/ios-team-flow/SKILL.md`。开发变更维护一张需求卡和一份验证证据；问答、检查和只读分析不建卡。
项目空间是接入时确定的项目根及其目录树；把空间外文件、目录或其他项目作为工作对象前，必须先说明具体范围和操作并获得用户本次明确允许。
任务所需开发工具按官方或既有包管理器默认位置安装，不受项目空间限制；无法直接默认安装时必须停止，说明原因和解决方案，并给出安装及验证命令，不擅自改用其他位置。
需求卡和需求列表用固定彩色图标显示状态与 AC 进度；完整映射以 Skill 的 WORKFLOW 为准。
有实现与交付的任务按“完成全部改动 → 环境预检 → 针对性测试 → 文件冻结 → 一次完整验证 → 目标交付”执行；完整验证后受跟踪输入变化时必须重新冻结并验证。
新 App 只先整理启动阶段草案，功能和发布资料按需加载。commit、push、PR、合并、标签、GitHub Release，以及 Archive、TestFlight、Beta Review、App Store 审核、发布和下架只在用户明确目标时执行；目标若依赖尚未完成的前置步骤，自动执行最小必要前置，但不扩张到可选或后续动作。
普通 TestFlight 上传不启用 TestFlight Internal Only；只有用户明确要求仅内部测试时才允许写入 `testFlightInternalTestingOnly: true`。
使用 `python3 scripts/teamflow.py` 处理需求、验证和显式动作。未经明确指令不提交、不上传、不提审、不发布。版本见 `.agents/teamflow.json`。
<!-- ios-team-flow:end -->
