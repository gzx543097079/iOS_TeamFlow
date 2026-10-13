import UIKit

/// 持有当前场景的窗口与主题绑定，避免依赖全局屏幕尺寸创建界面。
final class SceneDelegate: UIResponder, UIWindowSceneDelegate {
    var window: UIWindow?
    private var coordinator: DemoCoordinator?
    private var appearanceBinding: DemoAppearanceBinding?

    func scene(
        _ scene: UIScene,
        willConnectTo session: UISceneSession,
        options connectionOptions: UIScene.ConnectionOptions
    ) {
        guard let windowScene = scene as? UIWindowScene else { return }
        let window = UIWindow(windowScene: windowScene)
        let coordinator = DemoCoordinator(preferences: DemoPreferences.shared)
        coordinator.start()
        self.coordinator = coordinator
        window.rootViewController = coordinator.navigationController
        // 首帧显示前应用已保存的外观；绑定随场景持有，后台切换不重建页面。
        appearanceBinding = DemoAppearanceBinding(window: window, preferences: .shared)
        self.window = window
        window.makeKeyAndVisible()
        TFLog.debug("Demo 窗口场景已连接")
    }
}
