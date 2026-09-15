import UIKit

/// 关于页只展示应用自身信息，不引入未经确认的公司或联系方式。
final class AboutViewController: UIViewController {
    private let viewModel: AboutViewModel
    init(viewModel: AboutViewModel) { self.viewModel = viewModel; super.init(nibName: nil, bundle: nil) }
    required init?(coder: NSCoder) { nil }
    override func viewDidLoad() {
        super.viewDidLoad()
        title = viewModel.text("settings.about")
        view.backgroundColor = .systemGroupedBackground
        let icon = UIImageView(image: UIImage(systemName: "bag.circle.fill"))
        icon.contentMode = .scaleAspectFit
        icon.tintColor = .systemTeal
        let name = UILabel()
        name.text = viewModel.name
        name.font = .preferredFont(forTextStyle: .title1)
        name.textAlignment = .center
        let description = UILabel()
        description.text = viewModel.description
        description.accessibilityIdentifier = "aboutDescription"
        description.font = .preferredFont(forTextStyle: .body)
        description.textColor = .secondaryLabel
        description.textAlignment = .center
        description.numberOfLines = 0
        description.adjustsFontForContentSizeCategory = true
        let version = UILabel()
        version.text = viewModel.versionText
        version.textAlignment = .center
        version.textColor = .secondaryLabel
        version.font = .preferredFont(forTextStyle: .footnote)
        let stack = UIStackView(arrangedSubviews: [icon, name, description, version])
        stack.axis = .vertical
        stack.spacing = 20
        view.addSubview(stack)
        icon.mas_makeConstraints { make in make?.height.equalTo()(88) }
        stack.mas_makeConstraints { make in
            make?.top.equalTo()(view.safeAreaLayoutGuide.masAttribute(.top))?.offset()(48)
            make?.leading.equalTo()(view.safeAreaLayoutGuide.masAttribute(.leading))?.offset()(32)
            make?.trailing.equalTo()(view.safeAreaLayoutGuide.masAttribute(.trailing))?.offset()(-32)
        }
    }
}

