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
            let detail = String(format: text("bag.item.detail"), bag.quantities[item.id] ?? 0, item.price)
            return BagItem(id: item.id, name: item.name, detail: detail, symbol: item.symbol)
        }
    }
    var header: String { bag.count == 0 ? text("bag.empty.message") : String(format: text("bag.itemCount"), bag.count) }
    var footer: String {
        let price = ProductItem.formatPrice(bag.totalCents, locale: preferences.locale,
                                            fallbackFormat: text("store.price.fallback"))
        let total = String(format: text("bag.summary.total"), price)
        return total + "\n" + text("bag.help.swipeToRemove")
    }
    func removeOne(id: String) {
        guard let product = bag.products.first(where: { $0.id == id }) else { return }
        bag.removeOne(product)
    }
}
