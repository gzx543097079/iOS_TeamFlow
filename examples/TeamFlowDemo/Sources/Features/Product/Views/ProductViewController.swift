import UIKit

/// 详情展示本地商品，添加操作只更新内存购物袋，不创建真实订单。
final class ProductViewController: UIViewController {
    let viewModel: ProductViewModel
    private let feedback = UILabel()
    init(viewModel: ProductViewModel) {
        self.viewModel = viewModel
        super.init(nibName: nil, bundle: nil)
    }
    required init?(coder: NSCoder) { nil }
    override func viewDidLoad() {
        super.viewDidLoad()
        title = viewModel.item.name
        navigationItem.largeTitleDisplayMode = .never
        view.backgroundColor = StoreStyle.background
        let content = StoreStyle.content(in: view)
        let image = UIImageView(image: UIImage(systemName: viewModel.item.symbol))
        image.contentMode = .center
        image.preferredSymbolConfiguration = UIImage.SymbolConfiguration(pointSize: 112, weight: .light)
        image.tintColor = StoreStyle.accent
        image.backgroundColor = StoreStyle.tile
        image.layer.cornerRadius = 24
        content.addArrangedSubview(image)
        image.mas_makeConstraints { make in make?.height.equalTo()(240) }
        content.addArrangedSubview(StoreStyle.label(viewModel.item.name, style: .title1))
        let price = StoreStyle.label(viewModel.item.price, style: .title2, color: StoreStyle.accent)
        price.accessibilityIdentifier = "productPrice"
        content.addArrangedSubview(price)
        content.addArrangedSubview(StoreStyle.label(viewModel.item.description, style: .body, color: .secondaryLabel))
        let add = UIButton(type: .system)
        add.setTitle(viewModel.text("store.productDetail.addToBagButton"), for: .normal)
        add.backgroundColor = StoreStyle.accent
        add.setTitleColor(StoreStyle.background, for: .normal)
        add.titleLabel?.font = .preferredFont(forTextStyle: .headline)
        add.layer.cornerRadius = 16
        add.accessibilityIdentifier = "addToBag"
        add.addTarget(self, action: #selector(addToBag), for: .touchUpInside)
        content.addArrangedSubview(add)
        add.mas_makeConstraints { make in make?.height.greaterThanOrEqualTo()(54) }
        feedback.font = .preferredFont(forTextStyle: .subheadline)
        feedback.textColor = StoreStyle.accent
        feedback.numberOfLines = 0
        feedback.accessibilityIdentifier = "bagFeedback"
        feedback.isHidden = true
        content.addArrangedSubview(feedback)
        content.addArrangedSubview(StoreStyle.label(viewModel.text("store.demoNotice"), style: .footnote, color: .secondaryLabel))
    }
    @objc private func addToBag() {
        viewModel.addToBag()
        feedback.text = viewModel.feedback
        feedback.isHidden = viewModel.feedback == nil
        UIAccessibility.post(notification: .announcement, argument: feedback.text)
    }
}
