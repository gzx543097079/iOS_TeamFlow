# 工作流分发与 Release

## 使用压缩包

1. 将 zip 解压到临时目录，检查内容后把内部根目录内容合入目标项目的 Git 根目录，必须包含隐藏的 `.agents/` 与 `.github/`。必须保留完整 Skill 和项目入口，才能按项目规则使用。
2. 新目录可整套复制；已有项目合并 AGENTS.md、.gitignore、.github 和同名脚本，保留团队规则、工作日志与业务配置。先看差异，禁止直接覆盖已有文件。工程目录不搬迁；新工程默认 `App/`。
3. 从项目根目录启动新 Codex 会话，确认识别 `ios-team-flow`；已打开会话若未刷新技能，重新打开会话。首次新产品按需求模板确认。
4. 可提交的需求/日志默认正常跟踪；将入口、规范、脚本及产生的脱敏记录随项目提交。dist zip 通过 Release 附件分发，不进源码历史。

## 本地生成

先更新 `<SKILL_ROOT>/references/VERSION`（语义版本 X.Y.Z）和 `<SKILL_ROOT>/references/CHANGELOG.md`，完成相关验证与本次审查，然后执行：

```sh
python3 scripts/run_workflow_checks.py --full
python3 scripts/package_release.py
```

输出 `dist/iOS-TeamFlow-vX.Y.Z.zip` 和 `.sha256`。zip 采用显式文件清单，只包含通用入口、规范、模板、工具、测试和 GitHub 工作流，不包含使用项目的 App、requirements、logs、.git 或密钥。脚本不会发布 GitHub Release。

修改要分发的文件时同步维护 `scripts/package_release.py` 的清单。打包拒绝符号链接/漏文件，路径从脚本定位，不依赖当前目录。版本不可重复覆盖线上发布；本地重复打包相同输入应得到相同校验和。

## GitHub 验证后自动发布

本仓库 `.github/workflows/teamflow-release.yml` 监听 `teamflow-vX.Y.Z` 标签推送。团队在已审核提交上创建并推送标签后，先以只读权限运行 macOS 原生检查、版本核对、完整工具测试和打包；验证产物通过 Actions artifact 传给独立发布任务。发布任务才获得 `contents: write`，使用已存在的标签创建草稿、上传 ZIP/校验和，并在附件上传成功后公开 Release。不要先在网页创建公开 Release；其他名称的 App 标签不会触发本流程。

先将工作流文件提交并推送到仓库，GitHub 才能执行。需要仓库启用 Actions；验证与打包任务保持 `contents: read`，只有最终发布任务使用 `contents: write`。工作流没有 App 签名或 App Store 权限。本地成功不能代表 GitHub 运行成功。标签、版本或任一检查不通过时不会创建公开 Release；上传失败时 `gh release create` 保持草稿而不公开。修复后先处理同标签的失败草稿，再重跑，不删除或覆盖已经公开的历史 Release。

分发到业务项目时可保留校验工作流；工作流 Release 标签与 App 发布分离。若团队只消费版本，可不复制 teamflow-release.yml，由工作流源仓库负责发布。

## 项目级独立 Skill 分发

现在同时输出 `ios-team-flow-skill-vX.Y.Z.zip` 及 SHA256，内含完整 `ios-team-flow/` 文件夹；它应安装到每个目标项目的 `.agents/skills/`，执行一次项目接入后随项目提交，无需个人安装或原始仓库。详见 [独立安装说明](INSTALL.md)。

直接维护 `.agents/skills/ios-team-flow/` 中的规则、模板、版本和工具实现，不再生成或同步第二份规范。根 scripts/review_gate.py 仅加载项目内 Skill 的门禁实现；根 scripts/ 中的校验与打包工具用于分发仓库。新增资源需登记打包清单，两个包均由 Release job 上传。

## 按改动执行源仓库检查

日常 push CI 使用 `python3 scripts/run_workflow_checks.py --base 完整基准SHA` 比较推送前提交与 HEAD（已提交内容，不含工作区修改）。普通说明执行文档校验，模板增加生成/消费场景，工具脚本执行对应模块及关联门禁、验收与消费测试。文档校验由测试套件统一执行一次，不在 CI 重复调用。

CI 获取完整 Git 历史：push 使用 before；新分支、基准缺失/不可读、公共脚本、测试、版本、CI 或未知路径变化回退全量。随提交归档的 REQ 卡、交付索引和审查回执不扩大工具测试范围；其他未知文件仍回退全量。多类变化取并集并去重；删除/重命名包含原路径。`--list` 只显示计划，不表示验证通过。手动 workflow_dispatch 和正式 Release 始终全量。

打包校验继续在 CI 执行；首次执行、公共依赖变化或无法确定影响时用 --full。不要把此脚本作为业务 App 测试入口，也不要只为减少测试数量删除独立覆盖。

本文件只发布工作流 ZIP；业务 iOS App 使用 [App 发布流程](APP-RELEASE.md)。

源码包含原生日志组件时，正式发布先在 macOS/Xcode 上运行 `python3 scripts/check_logging.py`，通过后才生成和上传 ZIP；Linux 上的 Python 回归不能替代该检查。日志源码变化另由原生日志工作流验证 Debug/Release。
