import UIKit

/// 详情展示本地商品，添加操作只更新内存购物袋，不创建真实订单。
final class ProductViewController: UIViewController {
    let product: DemoProduct
    private let preferences: DemoPreferences
    private let bag: DemoBag
    private let feedback = UILabel()
    init(product: DemoProduct, preferences: DemoPreferences, bag: DemoBag) {
        self.product = product
        self.preferences = preferences
        self.bag = bag
        super.init(nibName: nil, bundle: nil)
    }
    required init?(coder: NSCoder) { nil }
    override func viewDidLoad() {
        super.viewDidLoad()
        title = preferences.text(product.nameKey)
        navigationItem.largeTitleDisplayMode = .never
        view.backgroundColor = StoreStyle.background
        let content = StoreStyle.content(in: view)
        let image = UIImageView(image: UIImage(systemName: product.symbol))
        image.contentMode = .center
        image.preferredSymbolConfiguration = UIImage.SymbolConfiguration(pointSize: 112, weight: .light)
        image.tintColor = StoreStyle.accent
        image.backgroundColor = StoreStyle.tile
        image.layer.cornerRadius = 24
        image.heightAnchor.constraint(equalToConstant: 240).isActive = true
        content.addArrangedSubview(image)
        content.addArrangedSubview(StoreStyle.label(preferences.text(product.nameKey), style: .title1))
        let price = StoreStyle.label(DemoProduct.price(product.priceCents, preferences: preferences), style: .title2, color: StoreStyle.accent)
        price.accessibilityIdentifier = "productPrice"
        content.addArrangedSubview(price)
        content.addArrangedSubview(StoreStyle.label(preferences.text(product.descriptionKey), style: .body, color: .secondaryLabel))
        let add = UIButton(type: .system)
        add.setTitle(preferences.text("bag.add"), for: .normal)
        add.backgroundColor = StoreStyle.accent
        add.setTitleColor(StoreStyle.background, for: .normal)
        add.titleLabel?.font = .preferredFont(forTextStyle: .headline)
        add.layer.cornerRadius = 16
        add.heightAnchor.constraint(greaterThanOrEqualToConstant: 54).isActive = true
        add.accessibilityIdentifier = "addToBag"
        add.addTarget(self, action: #selector(addToBag), for: .touchUpInside)
        content.addArrangedSubview(add)
        feedback.font = .preferredFont(forTextStyle: .subheadline)
        feedback.textColor = StoreStyle.accent
        feedback.numberOfLines = 0
        feedback.accessibilityIdentifier = "bagFeedback"
        feedback.isHidden = true
        content.addArrangedSubview(feedback)
        content.addArrangedSubview(StoreStyle.label(preferences.text("store.notice"), style: .footnote, color: .secondaryLabel))
    }
    @objc private func addToBag() {
        bag.add(product)
        feedback.text = preferences.text("bag.added")
        feedback.isHidden = false
        UIAccessibility.post(notification: .announcement, argument: feedback.text)
    }
}

/// 购物袋按商品汇总数量，滑动移除整项；无结算入口。
final class BagViewController: UITableViewController {
    private let preferences: DemoPreferences
    private let bag: DemoBag
    init(preferences: DemoPreferences, bag: DemoBag) {
        self.preferences = preferences
        self.bag = bag
        super.init(style: .insetGrouped)
    }
    required init?(coder: NSCoder) { nil }
    override func viewDidLoad() {
        super.viewDidLoad()
        title = preferences.text("bag.title")
        navigationItem.largeTitleDisplayMode = .never
        tableView.accessibilityIdentifier = "shoppingBag"
        tableView.rowHeight = UITableView.automaticDimension
        tableView.estimatedRowHeight = 68
    }
    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { bag.products.count }
    override func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? {
        bag.count == 0 ? preferences.text("bag.empty") : String(format: preferences.text("bag.items"), bag.count)
    }
    override func tableView(_ tableView: UITableView, titleForFooterInSection section: Int) -> String? {
        "\(preferences.text("bag.total")) \(DemoProduct.price(bag.totalCents, preferences: preferences))\n\(preferences.text("bag.help"))"
    }
    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let product = bag.products[indexPath.row]
        let cell = UITableViewCell(style: .subtitle, reuseIdentifier: nil)
        cell.textLabel?.text = preferences.text(product.nameKey)
        cell.detailTextLabel?.text = "\(bag.quantities[product.id] ?? 0) × \(DemoProduct.price(product.priceCents, preferences: preferences))"
        cell.imageView?.image = UIImage(systemName: product.symbol)
        cell.imageView?.tintColor = StoreStyle.accent
        cell.accessibilityIdentifier = "bag-\(product.id)"
        cell.selectionStyle = .none
        return cell
    }
    override func tableView(_ tableView: UITableView, trailingSwipeActionsConfigurationForRowAt indexPath: IndexPath) -> UISwipeActionsConfiguration? {
        let product = bag.products[indexPath.row]
        let remove = UIContextualAction(style: .destructive, title: preferences.text("bag.remove")) { [weak self] _, _, completion in
            self?.bag.remove(product)
            self?.tableView.reloadData()
            completion(true)
        }
        return UISwipeActionsConfiguration(actions: [remove])
    }
}
