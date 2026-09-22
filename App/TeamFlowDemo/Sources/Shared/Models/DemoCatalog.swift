import Foundation

/// 本地展示商品，金额以分保存，避免购物袋汇总的浮点误差。
struct DemoProduct: Equatable {
    enum Category: String, CaseIterable { case all, audio, daily }
    let id: String
    let category: Category
    let symbol: String
    let priceCents: Int
    var nameKey: String { "product.\(id).name" }
    var descriptionKey: String { "product.\(id).description" }

    static let catalog = [
        DemoProduct(id: "headphones", category: .audio, symbol: "headphones", priceCents: 29900),
        DemoProduct(id: "bag", category: .daily, symbol: "bag.fill", priceCents: 8900),
        DemoProduct(id: "speaker", category: .audio, symbol: "hifispeaker.fill", priceCents: 19900),
        DemoProduct(id: "keyboard", category: .daily, symbol: "keyboard", priceCents: 15900)
    ]

    static func filtered(by category: Category) -> [DemoProduct] {
        catalog.filter { category == .all || $0.category == category }
    }

}

/// 购物袋仅在本次运行内保存，商品来自本地目录，不提交订单或调用支付。
final class DemoBag {
    private(set) var quantities: [String: Int] = [:]
    var products: [DemoProduct] { DemoProduct.catalog.filter { quantities[$0.id] != nil } }
    var count: Int { quantities.values.reduce(0, +) }
    var totalCents: Int { products.reduce(0) { $0 + $1.priceCents * (quantities[$1.id] ?? 0) } }
    func add(_ product: DemoProduct) {
        guard DemoProduct.catalog.contains(product) else { return }
        quantities[product.id, default: 0] += 1
        TFLog.debug("Demo 购物袋已添加商品")
    }
    /// 每次只减少一件；数量归零时再移除商品行。
    func removeOne(_ product: DemoProduct) {
        guard let quantity = quantities[product.id] else { return }
        if quantity > 1 {
            quantities[product.id] = quantity - 1
        } else {
            quantities.removeValue(forKey: product.id)
        }
    }
}
