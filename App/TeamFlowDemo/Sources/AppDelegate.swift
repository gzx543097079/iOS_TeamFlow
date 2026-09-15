import UIKit

/// 处理进程级启动；界面与窗口由 SceneDelegate 随场景连接创建。
@main
final class AppDelegate: UIResponder, UIApplicationDelegate {
    func application(
        _ application: UIApplication,
        didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
    ) -> Bool {
        TFLog.info("Demo 已启动")
        return true
    }
}
