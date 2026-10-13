import UIKit

/// 整张卡片为一个可访问按钮，图标与文字不重复朗读。
final class ProductCard: UIControl {
    let product: DemoProduct
    init(item: ProductItem) {
        self.product = item.product
        super.init(frame: .zero)
        backgroundColor = .secondarySystemGroupedBackground
        layer.cornerRadius = 20
        let illustration = UIImageView(image: UIImage(systemName: item.symbol))
        illustration.contentMode = .center
        illustration.preferredSymbolConfiguration = UIImage.SymbolConfiguration(pointSize: 58, weight: .light)
        illustration.tintColor = StoreStyle.accent
        illustration.backgroundColor = StoreStyle.tile
        illustration.layer.cornerRadius = 14
        let name = StoreStyle.label(item.name, style: .headline)
        let price = StoreStyle.label(item.price, style: .subheadline, color: StoreStyle.accent)
        // 商品名称长短不同时，让价格仍对齐卡片底部。
        price.setContentHuggingPriority(.required, for: .vertical)
        let stack = UIStackView(arrangedSubviews: [illustration, name, price])
        stack.axis = .vertical
        stack.spacing = 10
        stack.isUserInteractionEnabled = false
        addSubview(stack)
        illustration.mas_makeConstraints { make in
            make?.height.equalTo()(108)
        }
        stack.mas_makeConstraints { make in
            make?.edges.equalTo()(self)?.insets()(UIEdgeInsets(top: 12, left: 12, bottom: 16, right: 12))
        }
        isAccessibilityElement = true
        accessibilityTraits = .button
        accessibilityIdentifier = "product-\(item.id)"
        accessibilityLabel = item.accessibilityLabel
    }
    required init?(coder: NSCoder) { nil }
    override var isHighlighted: Bool { didSet { alpha = isHighlighted ? 0.65 : 1 } }
}
