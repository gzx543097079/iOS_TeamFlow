import Foundation

final class AppearanceViewModel: DemoViewModel, ChoicePresenting {
    var title: String { text("settings.appearance.title") }
    var backTitle: String { text("common.navigation.backButton") }
    var footer: String? { text("settings.appearance.footer") }
    var items: [ChoiceItem] {
        DemoAppearance.allCases.map { ChoiceItem(title: text($0.titleKey), identifier: "appearance-\($0.rawValue)", isSelected: preferences.appearance == $0) }
    }
    func select(at index: Int) {
        guard DemoAppearance.allCases.indices.contains(index) else { return }
        preferences.appearance = DemoAppearance.allCases[index]
        TFLog.info("Demo 外观设置已更新")
    }
}
