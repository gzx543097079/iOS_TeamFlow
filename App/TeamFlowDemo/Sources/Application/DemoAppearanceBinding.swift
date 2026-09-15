import UIKit

extension DemoPreferences.Appearance {
    /// UIKit 外观值只在窗口适配层转换，偏好模型不依赖 UI 框架。
    var interfaceStyle: UIUserInterfaceStyle {
        switch self {
        case .system: return .unspecified
        case .light: return .light
        case .dark: return .dark
        }
    }
}

/// 窗口级外观覆盖统一作用于导航栏和所有页面，跟随系统不固定亮暗。
final class DemoAppearanceBinding {
    private var observer: NSObjectProtocol?
    init(window: UIWindow, preferences: DemoPreferences) {
        window.overrideUserInterfaceStyle = preferences.appearance.interfaceStyle
        observer = NotificationCenter.default.addObserver(
            forName: DemoPreferences.appearanceDidChange, object: preferences, queue: .main
        ) { [weak window] _ in
            window?.overrideUserInterfaceStyle = preferences.appearance.interfaceStyle
        }
    }
    deinit {
        if let observer = observer { NotificationCenter.default.removeObserver(observer) }
    }
}
