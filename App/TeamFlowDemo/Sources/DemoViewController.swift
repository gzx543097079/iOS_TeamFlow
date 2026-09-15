import UIKit

/// 商城入口沿用单导航栈，所有商品与购物袋均为本地演示数据。
final class DemoViewController: UIViewController {
    let events: DemoEvents
    let preferences: DemoPreferences
    let bag: DemoBag
    private var category: DemoProduct.Category = .all
    private var content: UIStackView!
    private let grid = UIStackView()
    private var categories: UISegmentedControl!
    private let countLabel = UILabel()

    init(events: DemoEvents = DemoEvents(), preferences: DemoPreferences = .shared, bag: DemoBag = DemoBag()) {
        self.events = events
        self.preferences = preferences
        self.bag = bag
        super.init(nibName: nil, bundle: nil)
    }
    required init?(coder: NSCoder) { nil }

    override func viewDidLoad() {
        super.viewDidLoad()
        view.backgroundColor = StoreStyle.background
        view.tintColor = StoreStyle.accent
        navigationController?.navigationBar.prefersLargeTitles = true
        content = StoreStyle.content(in: view)
        grid.axis = .vertical
        grid.spacing = 14
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        refresh()
    }

    private func refresh() {
        title = preferences.text("store.title")
        navigationItem.backButtonTitle = preferences.text("common.back")
        navigationItem.largeTitleDisplayMode = .always
        navigationController?.navigationBar.tintColor = StoreStyle.accent
        let settings = UIBarButtonItem(image: UIImage(systemName: "gearshape"), style: .plain, target: self, action: #selector(openSettings))
        settings.accessibilityIdentifier = "openSettings"
        settings.accessibilityLabel = preferences.text("settings.title")
        let cart = UIBarButtonItem(title: "\(preferences.text("bag.title")) · \(bag.count)", style: .plain, target: self, action: #selector(openBag))
        cart.accessibilityIdentifier = "openBag"
        navigationItem.rightBarButtonItems = [settings, cart]
        content.arrangedSubviews.forEach { $0.removeFromSuperview() }
        content.addArrangedSubview(hero())
        categories = UISegmentedControl(items: DemoProduct.Category.allCases.map { preferences.text("category.\($0.rawValue)") })
        categories.accessibilityIdentifier = "storeCategories"
        categories.selectedSegmentIndex = DemoProduct.Category.allCases.firstIndex(of: category) ?? 0
        categories.addTarget(self, action: #selector(changeCategory), for: .valueChanged)
        content.addArrangedSubview(categories)
        let section = UIStackView(arrangedSubviews: [StoreStyle.label(preferences.text("store.selected"), style: .title2), countLabel])
        section.alignment = .center
        countLabel.font = .preferredFont(forTextStyle: .footnote)
        countLabel.textColor = .secondaryLabel
        countLabel.textAlignment = .right
        content.addArrangedSubview(section)
        content.addArrangedSubview(grid)
        content.addArrangedSubview(StoreStyle.label(preferences.text("store.notice"), style: .footnote, color: .secondaryLabel))
        rebuildGrid()
    }

    private func hero() -> UIView {
        let panel = UIView()
        panel.backgroundColor = UIColor(red: 0.07, green: 0.27, blue: 0.24, alpha: 1)
        panel.layer.cornerRadius = 24
        let eyebrow = StoreStyle.label(preferences.text("store.collection"), style: .caption1, color: UIColor(white: 0.85, alpha: 1))
        let heading = StoreStyle.label(preferences.text("store.headline"), style: .title1, color: .white)
        heading.font = .systemFont(ofSize: 30, weight: .semibold)
        let description = StoreStyle.label(preferences.text("store.subtitle"), style: .subheadline, color: UIColor(white: 0.9, alpha: 1))
        let stack = UIStackView(arrangedSubviews: [eyebrow, heading, description])
        stack.axis = .vertical
        stack.spacing = 12
        panel.addSubview(stack)
        stack.mas_makeConstraints { make in
            make?.edges.equalTo()(panel)?.insets()(UIEdgeInsets(top: 24, left: 24, bottom: 24, right: 24))
        }
        return panel
    }

    private func rebuildGrid() {
        grid.arrangedSubviews.forEach { $0.removeFromSuperview() }
        let products = DemoProduct.filtered(by: category)
        countLabel.text = String(format: preferences.text("store.count"), products.count)
        for offset in stride(from: 0, to: products.count, by: 2) {
            let row = UIStackView()
            row.spacing = 14
            row.distribution = .fillEqually
            for product in products[offset..<min(offset + 2, products.count)] {
                let card = ProductCard(product: product, preferences: preferences)
                card.addTarget(self, action: #selector(openProduct(_:)), for: .touchUpInside)
                row.addArrangedSubview(card)
            }
            if row.arrangedSubviews.count == 1 { row.addArrangedSubview(UIView()) }
            grid.addArrangedSubview(row)
        }
    }

    @objc private func changeCategory() {
        category = DemoProduct.Category.allCases[categories.selectedSegmentIndex]
        rebuildGrid()
    }
    @objc private func openProduct(_ card: ProductCard) { showProduct(card.product) }

    /// 只将用户选中的商品传给详情，不以列表位置猜测购买对象。
    func showProduct(_ product: DemoProduct) {
        events.record("demo_product_open")
        navigationController?.pushViewController(ProductViewController(product: product, preferences: preferences, bag: bag), animated: true)
    }
    @objc private func openSettings() {
        let settings = SettingsViewController(preferences: preferences)
        settings.navigationItem.largeTitleDisplayMode = .never
        navigationController?.pushViewController(settings, animated: true)
    }
    @objc private func openBag() {
        navigationController?.pushViewController(BagViewController(preferences: preferences, bag: bag), animated: true)
    }
}

/// 整张卡片为一个可访问按钮，图标与文字不重复朗读。
private final class ProductCard: UIControl {
    let product: DemoProduct
    init(product: DemoProduct, preferences: DemoPreferences) {
        self.product = product
        super.init(frame: .zero)
        backgroundColor = .secondarySystemGroupedBackground
        layer.cornerRadius = 20
        let illustration = UIImageView(image: UIImage(systemName: product.symbol))
        illustration.contentMode = .center
        illustration.preferredSymbolConfiguration = UIImage.SymbolConfiguration(pointSize: 58, weight: .light)
        illustration.tintColor = StoreStyle.accent
        illustration.backgroundColor = StoreStyle.tile
        illustration.layer.cornerRadius = 14
        let name = StoreStyle.label(preferences.text(product.nameKey), style: .headline)
        let price = StoreStyle.label(DemoProduct.price(product.priceCents, preferences: preferences), style: .subheadline, color: StoreStyle.accent)
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
        accessibilityIdentifier = "product-\(product.id)"
        accessibilityLabel = "\(preferences.text(product.nameKey)), \(price.text ?? "")"
    }
    required init?(coder: NSCoder) { nil }
    override var isHighlighted: Bool { didSet { alpha = isHighlighted ? 0.65 : 1 } }
}
