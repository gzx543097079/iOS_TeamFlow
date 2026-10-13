# Godot 工作流演练

最小 GDScript + Control 场景：计分按钮、暂停／恢复、重进场景。用于验证场景引用、信号连接和状态行为，不是完整游戏模板。样例按钮使用英文，以免依赖额外 CJK 字体资产；中文游戏文案应另按实际字体与翻译资源验收。

从仓库根运行：

```sh
python3 .agents/skills/Godot/scripts/verify_godot.py \
  --project examples/TeamFlowGame --test-script tests/run_tests.gd
```

用 Godot 编辑器打开本目录的 `project.godot` 可查看场景。开发时可运行主场景进行交互，自动测试通过不证明实际触控、渲染或音频正确。

验证环境为 Godot 4.7.2。没有 iOS 导出预设、签名、原生插件或商业 SDK；iOS 导出、真机和发布未验证。项目不会写入用户存档。检查日志位于项目内 `.godot/teamflow-checks/`。
