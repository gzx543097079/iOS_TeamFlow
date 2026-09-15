import Foundation

/// 本地演练事件不上传，仅供导航验证及 Debug 排错。
final class DemoEvents: DemoEventRecording {
    private(set) var names: [String] = []
    func record(_ name: String) {
        names.append(name)
        TFLog.debug("Demo 事件：\(name)")
    }
}

