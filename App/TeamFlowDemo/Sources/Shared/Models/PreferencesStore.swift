import Foundation

enum DemoAppearance: String, CaseIterable {
    case system, light, dark
    var titleKey: String { "settings.appearance.option.\(rawValue)" }
}
enum DemoLanguage: String, CaseIterable {
    case system, english = "en", chinese = "zh-Hans"
    var titleKey: String {
        switch self {
        case .system: return "settings.language.option.system"
        case .english: return "settings.language.option.english"
        case .chinese: return "settings.language.option.simplifiedChinese"
        }
    }
}

/// 功能层只依赖偏好接口，具体持久化由 Infrastructure 提供。
protocol PreferencesStore: AnyObject {
    var language: DemoLanguage { get set }
    var appearance: DemoAppearance { get set }
    var locale: Locale { get }
    func text(_ key: String) -> String
}

protocol DemoEventRecording: AnyObject {
    func record(_ name: String)
}
