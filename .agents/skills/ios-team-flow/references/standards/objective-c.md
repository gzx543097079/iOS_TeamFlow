# Objective-C 代码规范

适用 `.h/.m/.mm`；UI 同时执行 UI 规范。以已有工程约定优先，新增无约定代码采用以下团队默认。参考 [Apple Objective-C 编程指南](https://developer.apple.com/library/archive/documentation/Cocoa/Conceptual/ProgrammingWithObjectiveC/Introduction/Introduction.html) 与 [NYTimes 风格指南](https://github.com/NYTimes/objective-c-style-guide)；后者已归档，仅借鉴稳定风格。

- 类型用团队前缀和 UpperCamelCase，方法/变量 lowerCamelCase；方法片段表达参数含义。4 空格缩进，花括号不省略，指针靠变量，避免无关格式改动。
- 头文件只公开必要接口；使用 forward declaration 降低依赖。私有属性放 class extension；枚举用 NS_ENUM / NS_OPTIONS，常量优先有类型的 static const 或 FOUNDATION_EXPORT。
- ARC 为默认。对象属性明确 nonatomic 和 strong/copy/weak；NSString、可变来源集合的不可变快照及 block 按语义用 copy，delegate 通常 weak。不能机械地把所有引用改成 weak。
- 公开接口在适合时使用 NS_ASSUME_NONNULL_BEGIN/END，并显式标注真实 nullable；集合使用轻量泛型，跨 Swift 桥接核对空值和名称。禁止用错误非空标注掩盖实际 nil。
- weakSelf / strongSelf 根据 block 生命周期和所有权决定。排查 owner→block→owner、NSTimer、CADisplayLink、通知 block token、KVO、代理和异步回调；解绑应在实际生命周期结束时完成，不能只依赖可能永远不执行的 dealloc。
- UIKit 更新在主线程；I/O、解码和重计算离开主线程。共享可变状态明确同步策略，nonatomic 不提供线程安全。
- 错误通过现有 NSError/回调约定传递；不要吞错或用 NSException 处理常规业务错误。判断集合边界、对象类型、nil、重复回调和取消。
- Core Foundation 创建/复制对象确认释放；桥接明确 __bridge / __bridge_transfer 等所有权，不混用 ARC 与 CF 管理。
- `.mm` 的 C++ 对象释放、RAII、异常边界沿用已有 C++ 规范；OC 规则不能替代 C++ 审查。
- 变更验证：使用工程现有 clang-format 配置检查改动文件；运行相关构建和测试，涉及所有权时用 Xcode Analyze、Memory Graph / Instruments 补证据。没有工具记录未验证，不声称零泄漏。

- 新生成和本次修改的代码按 [中文注释规范](comments.md) 补充职责、接口契约与关键逻辑说明。
