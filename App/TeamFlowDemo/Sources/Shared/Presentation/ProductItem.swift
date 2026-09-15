import Foundation

/// 商品的展示快照，将货币格式化与本地化留在展示层。
struct ProductItem {
    let product: DemoProduct
    let name: String
    let description: String
    let price: String
    var id: String { product.id }
    var symbol: String { product.symbol }

    init(product: DemoProduct, preferences: PreferencesStore) {
        self.product = product
        name = preferences.text(product.nameKey)
        description = preferences.text(product.descriptionKey)
        price = Self.formatPrice(product.priceCents, locale: preferences.locale)
    }

    static func formatPrice(_ cents: Int, locale: Locale) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "CNY"
        formatter.locale = locale
        return formatter.string(from: NSDecimalNumber(value: cents).dividing(by: 100)) ?? "CNY \(cents / 100)"
    }
}
