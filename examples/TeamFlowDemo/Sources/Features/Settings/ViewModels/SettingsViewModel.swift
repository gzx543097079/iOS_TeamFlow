import Foundation

struct SettingsItem {
    enum Destination { case language, appearance, about }
    let title: String
    let detail: String?
    let symbol: String
    let identifier: String
    let destination: Destination
}

final class SettingsViewModel: DemoViewModel {
    var items: [SettingsItem] {
        [SettingsItem(title: text("settings.language.title"), detail: text(preferences.language.titleKey), symbol: "globe", identifier: "settingsLanguage", destination: .language),
         SettingsItem(title: text("settings.appearance.title"), detail: text(preferences.appearance.titleKey), symbol: "moon.circle", identifier: "settingsAppearance", destination: .appearance),
         SettingsItem(title: text("settings.about.title"), detail: nil, symbol: "info.circle", identifier: "settingsAbout", destination: .about)]
    }

}
