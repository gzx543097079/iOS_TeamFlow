import Foundation

/// 商品的展示快照，将货币格式化与本地化留在展示层。
struct ProductItem {
    let product: DemoProduct
    let name: String
    let description: String
    let price: String
    let accessibilityLabel: String
    var id: String { product.id }
    var symbol: String { product.symbol }

    init(product: DemoProduct, preferences: PreferencesStore) {
        let localizedName = preferences.text(product.nameKey)
        let localizedPrice = Self.formatPrice(product.priceCents, locale: preferences.locale,
                                              fallbackFormat: preferences.text("store.price.fallback"))
        self.product = product
        name = localizedName
        description = preferences.text(product.descriptionKey)
        price = localizedPrice
        accessibilityLabel = String(format: preferences.text("store.productCard.accessibilityLabel"), localizedName, localizedPrice)
    }

    static func formatPrice(_ cents: Int, locale: Locale, fallbackFormat: String) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "CNY"
        formatter.locale = locale
        let amount = NSDecimalNumber(value: cents).dividing(by: 100)
        return formatter.string(from: amount) ?? String(format: fallbackFormat, amount.stringValue)
    }
}
