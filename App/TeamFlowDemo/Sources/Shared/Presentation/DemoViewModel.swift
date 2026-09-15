import Foundation

/// 页面共享本地化能力；依赖由初始化注入，ViewModel 不持有视图或导航控制器。
class DemoViewModel {
    let preferences: PreferencesStore
    init(preferences: PreferencesStore) { self.preferences = preferences }
    func text(_ key: String) -> String { preferences.text(key) }
}
