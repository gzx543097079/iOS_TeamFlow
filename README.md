# iOS TeamFlow

项目级中文 iOS 团队工作流。当前版本为 **1.8.0**。完整规则只维护在项目 .agents/skills/ios-team-flow，团队克隆后共用。

## 团队成员如何使用

成员负责提出需求、确认必要业务决定、实际验收和授权提交/推送/发布。Codex 负责建卡、实现、选择并运行验证、更新记录、提交前审查及交付同步。日常直接描述需求，无需手工维护编号或执行 finish 等命令。

**首次接入：** 放入完整 Skill → 执行一次接入及查看诊断 → 在 Codex 打开项目根的新会话。需要 Python 3.10+、Git；App 构建需要项目实际 macOS/Xcode。

1. 进入项目根，创建 .agents/skills；从 [1.8.0 Release](https://github.com/gzx543097079/iOS_TeamFlow/releases/tag/teamflow-v1.8.0) 下载 ios-team-flow-skill-v1.8.0.zip，将完整 ios-team-flow 文件夹放入其中，最终是 .agents/skills/ios-team-flow/SKILL.md。
2. 执行接入（也可让 Codex 接入当前项目）：

```sh
python3 .agents/skills/ios-team-flow/scripts/setup_project.py --project .
```

3. 处理诊断中的当前必要项；空目录首次收尾前初始化 Git，已有仓库保留原根。新产品先确认启动草案再建工程；已有项目只摸底相关入口。业务验证配置由 Codex 从实际工程/CI 提取。
4. 完整 Skill、入口及脱敏记录随项目提交。其他成员克隆即可使用；可选 Hook 每个克隆单独接入。

详细安装、冲突、升级及恢复见 [INSTALL](.agents/skills/ios-team-flow/references/INSTALL.md)。诊断只是接入检查，不代表业务测试通过。

## 日常最小路径

提出需求 → 一次确定范围与 AC → 实施和验证 → 更新唯一验收记录并绑定证据 → 一次最终提交门禁 → 授权交付后同步事实。

状态只在需求卡维护；测试命令只在验证配置维护；验收引用真实结果，无需再手填同一测试范围。已封存验收绑定当时提交，后续需求不会迫使原需求重验。无变化问答不执行收尾，生成交付记录可随下一次正常提交归档。

新项目只输出启动阶段适用内容，功能和发布阶段再展开；已有项目保留实际技术栈和目录，现状文档只保留稳定入口与约定。历史需求不补同步。

| 按需资料 | 入口 |
| --- | --- |
| Codex 执行顺序、记录归属和状态规则 | [WORKFLOW](.agents/skills/ios-team-flow/references/WORKFLOW.md) |
| 手动操作/排错：验收与同步命令 | [DELIVERY](.agents/skills/ios-team-flow/references/DELIVERY.md) |
| 验证命令与结果排错 | [PROJECT-CHECKS](.agents/skills/ios-team-flow/references/PROJECT-CHECKS.md) |
| 提交前审查、可选 Hook/PR | [REVIEW](.agents/skills/ios-team-flow/references/REVIEW.md) · [GIT-CHECKS](.agents/skills/ios-team-flow/references/GIT-CHECKS.md) |
| 其余规范、模板和 App 发布 | [内容导航](.agents/skills/ios-team-flow/references/README.md) |

## 源仓库维护

[变更记录](.agents/skills/ios-team-flow/references/CHANGELOG.md)记录版本变化。业务项目用独立 Skill 包；完整 iOS-TeamFlow ZIP 含分发仓库的测试与发布流水线，勿覆盖到业务仓库。

```sh
python3 scripts/validate_workflow.py
python3 -m unittest discover -s tests -v
python3 scripts/package_release.py
```

发布按 [RELEASE](.agents/skills/ios-team-flow/references/RELEASE.md)；App 示例仅在源码 App/TeamFlowDemo，工具测试不代替真实 App 验收。密钥、用户数据及大型构建产物不入库。参考来源见 [SOURCES](.agents/skills/ios-team-flow/references/SOURCES.md)。
