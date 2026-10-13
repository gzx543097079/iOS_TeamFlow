import Foundation

/// 商城拥有筛选状态；每次返回页面重新读取共享购物袋与偏好，保持显示一致。
final class StoreViewModel: DemoViewModel {
    private let bag: DemoBag
    private let events: DemoEventRecording
    private(set) var category: DemoProduct.Category = .all
    init(preferences: PreferencesStore, bag: DemoBag = DemoBag(), events: DemoEventRecording) {
        self.bag = bag
        self.events = events
        super.init(preferences: preferences)
    }
    var items: [ProductItem] { DemoProduct.filtered(by: category).map { ProductItem(product: $0, preferences: preferences) } }
    var categoryTitles: [String] { DemoProduct.Category.allCases.map { text("store.category.\($0.rawValue)") } }
    var selectedCategoryIndex: Int { DemoProduct.Category.allCases.firstIndex(of: category) ?? 0 }
    var countText: String { String(format: text("store.selectedSection.itemCount"), items.count) }
    var bagTitle: String { String(format: text("store.navigation.bagButton.title"), bag.count) }
    func selectCategory(at index: Int) {
        guard DemoProduct.Category.allCases.indices.contains(index) else { return }
        category = DemoProduct.Category.allCases[index]
    }
    func selectProduct(_ product: DemoProduct) {
        events.record("demo_product_open")
    }

}
