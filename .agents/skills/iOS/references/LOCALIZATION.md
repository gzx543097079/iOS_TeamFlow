# iOS 本地化实现

用户可见文本范围、自然表达、语义键、资源同步和验收遵循[共用本地化规则](../../../teamflow-core/references/LOCALIZATION.md)。

原生资源使用工程已有 String Catalog、`.strings` 或 `.stringsdict`。Swift／SwiftUI／Objective-C 沿用既有 API；没有封装时分别使用 `String(localized:)`、明确本地化后的 SwiftUI 文本或 `NSLocalizedString`，传入语义键而非最终展示文案。变体和复数使用 String Catalog variation 或 `.stringsdict` 规则，不用英文单复数分支代替语言规则。
