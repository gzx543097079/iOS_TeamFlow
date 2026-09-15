import UIKit

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
    static func price(_ cents: Int, preferences: DemoPreferences) -> String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .currency
        formatter.currencyCode = "CNY"
        formatter.locale = preferences.locale
        return formatter.string(from: NSDecimalNumber(value: cents).dividing(by: 100)) ?? "CNY \(cents / 100)"
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
    func remove(_ product: DemoProduct) { quantities.removeValue(forKey: product.id) }
}

/// 本地演练事件不上传，仅供导航验证及 Debug 排错。
final class DemoEvents {
    private(set) var names: [String] = []
    func record(_ name: String) {
        names.append(name)
        TFLog.debug("Demo 事件：\(name)")
    }
}

/// 品牌色随系统外观调整，内容颜色仍采用系统语义颜色。
enum StoreStyle {
    static let accent = UIColor { $0.userInterfaceStyle == .dark
        ? UIColor(red: 0.40, green: 0.83, blue: 0.73, alpha: 1)
        : UIColor(red: 0.08, green: 0.36, blue: 0.31, alpha: 1) }
    static let background = UIColor { $0.userInterfaceStyle == .dark
        ? .systemBackground : UIColor(red: 0.97, green: 0.97, blue: 0.95, alpha: 1) }
    static let tile = UIColor { $0.userInterfaceStyle == .dark
        ? .secondarySystemGroupedBackground : UIColor(red: 0.91, green: 0.94, blue: 0.91, alpha: 1) }

    static func label(_ text: String, style: UIFont.TextStyle, color: UIColor = .label) -> UILabel {
        let label = UILabel()
        label.text = text
        label.font = .preferredFont(forTextStyle: style)
        label.adjustsFontForContentSizeCategory = true
        label.numberOfLines = 0
        label.textColor = color
        return label
    }

    /// 把内容装进可滚动的安全区，窄屏与横屏都能访问底部操作。
    static func content(in view: UIView) -> UIStackView {
        let scroll = UIScrollView()
        let stack = UIStackView()
        stack.axis = .vertical
        stack.spacing = 20
        view.addSubview(scroll)
        scroll.addSubview(stack)
        // 内容边界决定滚动高度，框架宽度约束避免横向溢出。
        scroll.mas_makeConstraints { make in
            make?.top.equalTo()(view.safeAreaLayoutGuide.masAttribute(.top))
            make?.leading.equalTo()(view.safeAreaLayoutGuide.masAttribute(.leading))
            make?.trailing.equalTo()(view.safeAreaLayoutGuide.masAttribute(.trailing))
            make?.bottom.equalTo()(view.safeAreaLayoutGuide.masAttribute(.bottom))
        }
        stack.mas_makeConstraints { make in
            make?.top.equalTo()(scroll.contentLayoutGuide.masAttribute(.top))?.offset()(20)
            make?.leading.equalTo()(scroll.contentLayoutGuide.masAttribute(.leading))?.offset()(20)
            make?.trailing.equalTo()(scroll.contentLayoutGuide.masAttribute(.trailing))?.offset()(-20)
            make?.bottom.equalTo()(scroll.contentLayoutGuide.masAttribute(.bottom))?.offset()(-28)
            make?.width.equalTo()(scroll.frameLayoutGuide.masAttribute(.width))?.offset()(-40)
        }
        return stack
    }
}
