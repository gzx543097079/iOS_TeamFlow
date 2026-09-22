import Foundation

struct BagItem {
    let id: String
    let name: String
    let detail: String
    let symbol: String
}

/// 将购物袋模型转换成列表快照；逐件减少使用稳定商品 ID，避免位置变化操作错商品。
final class BagViewModel: DemoViewModel {
    private let bag: DemoBag
    init(preferences: PreferencesStore, bag: DemoBag) {
        self.bag = bag
        super.init(preferences: preferences)
    }
    var items: [BagItem] {
        bag.products.map {
            let item = ProductItem(product: $0, preferences: preferences)
            return BagItem(id: item.id, name: item.name, detail: "\(bag.quantities[item.id] ?? 0) × \(item.price)", symbol: item.symbol)
        }
    }
    var header: String { bag.count == 0 ? text("bag.empty") : String(format: text("bag.items"), bag.count) }
    var footer: String { "\(text("bag.total")) \(ProductItem.formatPrice(bag.totalCents, locale: preferences.locale))\n\(text("bag.help"))" }
    func removeOne(id: String) {
        guard let product = bag.products.first(where: { $0.id == id }) else { return }
        bag.removeOne(product)
    }
}
