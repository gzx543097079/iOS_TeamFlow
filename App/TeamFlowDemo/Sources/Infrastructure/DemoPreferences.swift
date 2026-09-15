import Foundation

/// 保存用户选择；系统语言变化在下次启动时由 Bundle 重新解析。
final class DemoPreferences: NSObject, PreferencesStore {
    static let appearanceDidChange = Notification.Name("DemoAppearanceDidChange")

    typealias Appearance = DemoAppearance
    typealias Language = DemoLanguage

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
    init(defaults: UserDefaults) { self.defaults = defaults; super.init() }

    var language: Language {
        get { Language(rawValue: defaults.string(forKey: "demo.language") ?? "") ?? .system }
        set { defaults.set(newValue.rawValue, forKey: "demo.language") }
    }

    /// 未保存或非法值均跟随系统；切换时通知窗口立即更新。
    var appearance: Appearance {
        get { Appearance(rawValue: defaults.string(forKey: "demo.appearance") ?? "") ?? .system }
        set {
            defaults.set(newValue.rawValue, forKey: "demo.appearance")
            NotificationCenter.default.post(name: Self.appearanceDidChange, object: self)
        }
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

