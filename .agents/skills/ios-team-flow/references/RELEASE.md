# 工作流分发与 Release

## 使用压缩包

1. 将 zip 解压到临时目录，检查内容后把内部根目录内容合入目标项目的 Git 根目录，必须包含隐藏的 `.agents/` 与 `.github/`。必须保留完整 Skill 和项目入口，才能按项目规则使用。
2. 新目录可整套复制；已有项目合并 AGENTS.md、.gitignore、.github 和同名脚本，保留团队规则、工作日志与业务配置。先看差异，禁止直接覆盖已有文件。工程目录不搬迁；新工程默认 `App/`。
3. 从项目根目录启动新 Codex 会话，确认识别 `ios-team-flow`；已打开会话若未刷新技能，重新打开会话。首次新产品按需求模板确认。
4. 可提交的需求/日志默认正常跟踪；将入口、规范、脚本及产生的脱敏记录随项目提交。dist zip 通过 Release 附件分发，不进源码历史。

## 本地生成

先更新 `<SKILL_ROOT>/references/VERSION`（语义版本 X.Y.Z）和 `<SKILL_ROOT>/references/CHANGELOG.md`，完成相关验证与本次审查，然后执行：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/package_release.py
```

输出 `dist/iOS-TeamFlow-vX.Y.Z.zip` 和 `.sha256`。zip 采用显式文件清单，只包含通用入口、规范、模板、工具、测试和 GitHub 工作流，不包含使用项目的 App、requirements、logs、.git 或密钥。脚本不会发布 GitHub Release。

修改要分发的文件时同步维护 `scripts/package_release.py` 的清单。打包拒绝符号链接/漏文件，路径从脚本定位，不依赖当前目录。版本不可重复覆盖线上发布；本地重复打包相同输入应得到相同校验和。

## GitHub 自动发布附件

本仓库 `.github/workflows/teamflow-release.yml` 监听 Release published：团队在已审核提交上发布 `teamflow-vX.Y.Z` 标签的 Release 后，校验版本、运行工具测试、生成 zip/校验和并上传到该 Release。其他名称的 App Release 跳过，不与业务版本冲突。

先将工作流文件提交并推送到仓库，GitHub 才能执行。需要仓库启用 Actions，job 使用 contents:write 上传附件；没有 app 签名或 App Store 权限。本地成功不能代表 GitHub 运行成功。若使用 GITHUB_TOKEN 从另一条 Action 创建 Release，事件可能不触发本 Action，需改为显式调用打包上传流程或使用适当凭据；不要重复发布碰运气。

分发到业务项目时可保留校验工作流；工作流 Release 名称与 App 发布分离。若团队只消费版本，可不复制 teamflow-release.yml，由工作流源仓库负责发布。

## 项目级独立 Skill 分发

现在同时输出 `ios-team-flow-skill-vX.Y.Z.zip` 及 SHA256，内含完整 `ios-team-flow/` 文件夹；它应安装到每个目标项目的 `.agents/skills/`，执行一次项目接入后随项目提交，无需个人安装或原始仓库。详见 [独立安装说明](INSTALL.md)。

直接维护 `.agents/skills/ios-team-flow/` 中的规则、模板、版本和工具实现，不再生成或同步第二份规范。根 scripts/review_gate.py 仅加载项目内 Skill 的门禁实现；根 scripts/ 中的校验与打包工具用于分发仓库。新增资源需登记打包清单，两个包均由 Release job 上传。
