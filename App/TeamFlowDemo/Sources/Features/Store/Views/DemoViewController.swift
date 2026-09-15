import UIKit

/// 商城入口沿用单导航栈，所有商品与购物袋均为本地演示数据。
final class DemoViewController: UIViewController {
    let viewModel: StoreViewModel
    var onOpenProduct: ((DemoProduct) -> Void)?
    var onOpenSettings: (() -> Void)?
    var onOpenBag: (() -> Void)?
    private var content: UIStackView!
    private let grid = UIStackView()
    private var categories: UISegmentedControl!
    private let countLabel = UILabel()

    init(viewModel: StoreViewModel) {
        self.viewModel = viewModel
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
        title = viewModel.text("store.title")
        navigationItem.backButtonTitle = viewModel.text("common.back")
        navigationItem.largeTitleDisplayMode = .always
        navigationController?.navigationBar.tintColor = StoreStyle.accent
        let settings = UIBarButtonItem(image: UIImage(systemName: "gearshape"), style: .plain, target: self, action: #selector(openSettings))
        settings.accessibilityIdentifier = "openSettings"
        settings.accessibilityLabel = viewModel.text("settings.title")
        let cart = UIBarButtonItem(title: viewModel.bagTitle, style: .plain, target: self, action: #selector(openBag))
        cart.accessibilityIdentifier = "openBag"
        navigationItem.rightBarButtonItems = [settings, cart]
        content.arrangedSubviews.forEach { $0.removeFromSuperview() }
        content.addArrangedSubview(hero())
        categories = UISegmentedControl(items: viewModel.categoryTitles)
        categories.accessibilityIdentifier = "storeCategories"
        categories.selectedSegmentIndex = viewModel.selectedCategoryIndex
        categories.addTarget(self, action: #selector(changeCategory), for: .valueChanged)
        content.addArrangedSubview(categories)
        let section = UIStackView(arrangedSubviews: [StoreStyle.label(viewModel.text("store.selected"), style: .title2), countLabel])
        section.alignment = .center
        countLabel.font = .preferredFont(forTextStyle: .footnote)
        countLabel.textColor = .secondaryLabel
        countLabel.textAlignment = .right
        content.addArrangedSubview(section)
        content.addArrangedSubview(grid)
        content.addArrangedSubview(StoreStyle.label(viewModel.text("store.notice"), style: .footnote, color: .secondaryLabel))
        rebuildGrid()
    }

    private func hero() -> UIView {
        let panel = UIView()
        panel.backgroundColor = UIColor(red: 0.07, green: 0.27, blue: 0.24, alpha: 1)
        panel.layer.cornerRadius = 24
        let eyebrow = StoreStyle.label(viewModel.text("store.collection"), style: .caption1, color: UIColor(white: 0.85, alpha: 1))
        let heading = StoreStyle.label(viewModel.text("store.headline"), style: .title1, color: .white)
        heading.font = .systemFont(ofSize: 30, weight: .semibold)
        let description = StoreStyle.label(viewModel.text("store.subtitle"), style: .subheadline, color: UIColor(white: 0.9, alpha: 1))
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
        let products = viewModel.items
        countLabel.text = viewModel.countText
        for offset in stride(from: 0, to: products.count, by: 2) {
            let row = UIStackView()
            row.spacing = 14
            row.distribution = .fillEqually
            for product in products[offset..<min(offset + 2, products.count)] {
                let card = ProductCard(item: product)
                card.addTarget(self, action: #selector(openProduct(_:)), for: .touchUpInside)
                row.addArrangedSubview(card)
            }
            if row.arrangedSubviews.count == 1 { row.addArrangedSubview(UIView()) }
            grid.addArrangedSubview(row)
        }
    }

    @objc private func changeCategory() {
        viewModel.selectCategory(at: categories.selectedSegmentIndex)
        rebuildGrid()
    }
    @objc private func openProduct(_ card: ProductCard) { showProduct(card.product) }

    /// 只将用户选中的商品传给详情，不以列表位置猜测购买对象。
    func showProduct(_ product: DemoProduct) {
        viewModel.selectProduct(product)
        onOpenProduct?(product)
    }
    @objc private func openSettings() { onOpenSettings?() }
    @objc private func openBag() { onOpenBag?() }

}

