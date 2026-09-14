import UIKit

/// 仅用于工作流测试；价格为夹具，不连接 StoreKit、不发起付款。
struct DemoPlan {
    let productID: String
    let displayPrice: String
    let period: String

    var summary: String { "\(displayPrice) / \(period)" }
    static let monthly = DemoPlan(productID: "fixture.monthly", displayPrice: "¥6.00", period: "月")
}

final class DemoEvents {
    private(set) var names: [String] = []
    /// 记录本地演练事件，日志仅包含内部事件名称。
    func record(_ name: String) {
        names.append(name)
        TFLog.debug("Demo 事件：\(name)")
    }
}

final class DemoViewController: UIViewController {
    let events: DemoEvents
    let plan: DemoPlan
    let preferences: DemoPreferences
    private let summaryLabel = UILabel()
    private let planButton = UIButton(type: .system)

    init(plan: DemoPlan = .monthly, events: DemoEvents = DemoEvents(), preferences: DemoPreferences = .shared) {
        self.preferences = preferences
        self.plan = plan
        self.events = events
        super.init(nibName: nil, bundle: nil)
    }

    required init?(coder: NSCoder) { return nil }

    override func viewDidLoad() {
        super.viewDidLoad()
        navigationItem.rightBarButtonItem = UIBarButtonItem(image: UIImage(systemName: "gearshape"), style: .plain, target: self, action: #selector(openSettings))
        navigationItem.rightBarButtonItem?.accessibilityIdentifier = "openSettings"
        view.backgroundColor = .systemBackground
        let label = summaryLabel
        label.text = "测试套餐：\(plan.summary)\n仅用于工作流验证，不提供真实购买。"
        label.numberOfLines = 0
        label.font = .preferredFont(forTextStyle: .body)
        label.adjustsFontForContentSizeCategory = true
        label.accessibilityIdentifier = "planSummary"
        let button = planButton
        button.setTitle("查看套餐", for: .normal)
        button.titleLabel?.font = .preferredFont(forTextStyle: .headline)
        button.titleLabel?.adjustsFontForContentSizeCategory = true
        button.accessibilityIdentifier = "showPlan"
        button.addTarget(self, action: #selector(showPlan), for: .touchUpInside)
        let stack = UIStackView(arrangedSubviews: [label, button])
        stack.axis = .vertical
        stack.spacing = 16
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        NSLayoutConstraint.activate([
            stack.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 24),
            stack.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -24),
            stack.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 24),
            button.heightAnchor.constraint(greaterThanOrEqualToConstant: 44)
        ])
    }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        title = preferences.text("demo.title")
        navigationItem.backButtonTitle = preferences.text("common.back")
        navigationItem.rightBarButtonItem?.accessibilityLabel = preferences.text("settings.title")
        summaryLabel.text = String(format: preferences.text("demo.plan"), plan.summary)
        planButton.setTitle(preferences.text("demo.open"), for: .normal)
    }

    @objc private func openSettings() {
        navigationController?.pushViewController(SettingsViewController(preferences: preferences), animated: true)
    }

    @objc func showPlan() {
        events.record("demo_plan_open")
        let detail = UIViewController()
        detail.title = plan.summary
        detail.view.backgroundColor = .systemBackground
        navigationController?.pushViewController(detail, animated: true)
    }
}
