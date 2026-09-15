import Foundation

enum DemoAppearance: String, CaseIterable {
    case system, light, dark
    var titleKey: String { "appearance.\(rawValue)" }
}
enum DemoLanguage: String, CaseIterable {
    case system, english = "en", chinese = "zh-Hans"
    var titleKey: String { "language.\(rawValue)" }
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
