# 分级日志与生成接入验证

时间：2026-09-14T17:20:15+08:00

- `python3.12 scripts/run_workflow_checks.py --full`：113 项通过，39.974 秒，退出码 0。新增 3 项真实独立 ZIP 安装测试覆盖 Swift/OC/混编选择、幂等不重写、冲突预检、目录和外部工具限制。
- `python3.12 scripts/check_logging.py`：Swift 6 严格并发下 Debug/Release 原生编译运行通过（混编桥接头同时导入）；OC 与 OC++ Debug、无 DEBUG、DEBUG=0 实际编译运行通过；各配置 iOS 14 模拟器 SDK 编译通过。Debug 五级全量、中文和百分号消息、真实调用位置；6 次调用，Debug 求值 6 次，Release 0 次且 stderr 为空。
- 原生测试首轮发现测试夹具全局计数器的 Swift 6 主 actor 隔离错误；为夹具函数显式添加 @MainActor 后重跑通过，未给日志实现添加不安全并发豁免。
- 临时消费项目通过项目内 install_logging.py 安装 mixed，XcodeGen 生成真实 iOS 工程：sources 自动纳入 .swift/.m，桥接 OC 测试入口，实际调用两套日志；核对 resolved build settings 的 Swift DEBUG 与 OC DEBUG=1/0，Debug 和 Release xcodebuild 模拟器构建均通过。未改变仓库 Demo，也未声称业务 App 真机验收。
- 生成工程演练脚本 /tmp/teamflow-generated-logging-check.py；先复制当前 Skill，再安装到 Sources/Logging，工程名 LoggingIntegration，目标 iOS 14，关闭签名。环境使用本机 Xcode 与 XcodeGen；临时工程和产物已清理。
- Skill 校验与 diff 格式检查通过，组件、安装工具、规程及原生检查入口登记分发清单。CI 增加原生组件检查，Release 附件上传依赖原生检查成功；未推送，不声称远端 CI 已执行。

- /tmp/teamflow-logging-full.log，SHA256：6287afdc6bb27a9d89fd707407b1ebdfce24e6642ad0f774d00e773694a9e656。
- /tmp/teamflow-logging-native.log，SHA256：3d3e13fc934e020d57e634e704d7781b2eea67168e5a17ca6aeb86033d8078b6。
- /tmp/teamflow-generated-logging.log，SHA256：9e328fca472acb7a08815ad417c2f8a1f58aa12d845e57543c2924ac4f1beda1。

## 语义审查范围

组件使用 Foundation NSLog，无第三方运行时依赖、文件存储、上报或可变全局配置；中文注释覆盖职责、求值和格式串约束。Swift 固定格式串与非逃逸 autoclosure 保持调用现场；OC 宏单语句、Release 移除实参，C 链接兼容 .mm。日志不替代错误处理，敏感数据需调用方脱敏；Release 关闭只覆盖本组件。

安装预检全部文件后排他写入，保留相同内容及已有定制，失败撤销本次文件；源码复制后仍由生成流程加入目标并验证，setup_project 不提前生成 App。之前注释需求的生成提交记录随本次提交归档，不增加第三次归档提交。
