import Foundation

/// 版本信息可注入，测试不依赖构建产物中的 Bundle 内容。
final class AboutViewModel: DemoViewModel {
    private let version: String
    private let build: String
    init(preferences: PreferencesStore, version: String, build: String) {
        self.version = version
        self.build = build
        super.init(preferences: preferences)
    }
    var name: String { text("settings.about.appName") }
    var description: String { text("settings.about.description") }
    var versionText: String { String(format: text("settings.about.version"), version, build) }
}
