import Foundation

/// 选择立即写入共享偏好，控制器在意图处理后重新渲染最新快照。
final class LanguageViewModel: DemoViewModel, ChoicePresenting {
    var title: String { text("settings.language.title") }
    var backTitle: String { text("common.navigation.backButton") }
    var footer: String? { nil }
    var items: [ChoiceItem] {
        DemoLanguage.allCases.map { ChoiceItem(title: text($0.titleKey), identifier: "language-\($0.rawValue)", isSelected: preferences.language == $0) }
    }
    func select(at index: Int) {
        guard DemoLanguage.allCases.indices.contains(index) else { return }
        preferences.language = DemoLanguage.allCases[index]
        TFLog.info("Demo 语言设置已更新")
    }
}
