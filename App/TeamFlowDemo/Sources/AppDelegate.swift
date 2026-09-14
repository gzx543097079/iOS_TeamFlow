import UIKit

/// 组装 Demo 窗口与导航入口。
@main
final class AppDelegate: UIResponder, UIApplicationDelegate {
    var window: UIWindow?

    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        let window = UIWindow(frame: UIScreen.main.bounds)
        window.rootViewController = UINavigationController(rootViewController: DemoViewController())
        window.makeKeyAndVisible()
        TFLog.info("Demo 已启动")
        self.window = window
        return true
    }
}
