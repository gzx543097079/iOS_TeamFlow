import UIKit

/// 保存用户选择；系统语言变化在下次启动时由 Bundle 重新解析。
final class DemoPreferences {
    enum Language: String, CaseIterable {
        case system, english = "en", chinese = "zh-Hans"
        var titleKey: String { "language.\(rawValue)" }
    }

    static let shared: DemoPreferences = {
        #if DEBUG
        // UI 测试使用独立存储，重置操作不会影响真实用户偏好。
        if ProcessInfo.processInfo.arguments.contains("-demo-ui-testing"),
           let defaults = UserDefaults(suiteName: "TeamFlowDemo.UITests") {
            if ProcessInfo.processInfo.arguments.contains("-reset-demo-preferences") {
                defaults.removePersistentDomain(forName: "TeamFlowDemo.UITests")
            }
            return DemoPreferences(defaults: defaults)
        }
        #endif
        return DemoPreferences(defaults: .standard)
    }()

    private let defaults: UserDefaults
    init(defaults: UserDefaults) { self.defaults = defaults }

    var language: Language {
        get { Language(rawValue: defaults.string(forKey: "demo.language") ?? "") ?? .system }
        set { defaults.set(newValue.rawValue, forKey: "demo.language") }
    }

    var locale: Locale {
        Locale(identifier: resolvedLanguage)
    }

    private var resolvedLanguage: String {
        language == .system ? (Bundle.main.preferredLocalizations.first ?? "en") : language.rawValue
    }

    /// 从指定语言资源读取文案，缺失时使用主包，避免全局修改 AppleLanguages。
    func text(_ key: String) -> String {
        let bundle = Bundle.main.path(forResource: resolvedLanguage, ofType: "lproj")
            .flatMap(Bundle.init(path:)) ?? .main
        return bundle.localizedString(forKey: key, value: nil, table: nil)
    }
}
