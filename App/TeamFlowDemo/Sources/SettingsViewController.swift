import UIKit

/// 设置保持原有导航栈；返回页面时刷新文案，使语言切换立即生效。
final class SettingsViewController: UITableViewController {
    let preferences: DemoPreferences

    init(preferences: DemoPreferences = .shared) {
        self.preferences = preferences
        super.init(style: .insetGrouped)
    }
    required init?(coder: NSCoder) { nil }

    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        title = preferences.text("settings.title")
        navigationItem.backButtonTitle = preferences.text("common.back")
        tableView.reloadData()
    }

    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { 3 }

    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = UITableViewCell(style: .value1, reuseIdentifier: nil)
        cell.accessoryType = .disclosureIndicator
        cell.textLabel?.font = .preferredFont(forTextStyle: .body)
        cell.textLabel?.adjustsFontForContentSizeCategory = true
        cell.detailTextLabel?.adjustsFontForContentSizeCategory = true
        if indexPath.row == 0 {
            cell.textLabel?.text = preferences.text("settings.language")
            cell.detailTextLabel?.text = preferences.text(preferences.language.titleKey)
            cell.imageView?.image = UIImage(systemName: "globe")
            cell.accessibilityIdentifier = "settingsLanguage"
        } else if indexPath.row == 1 {
            cell.textLabel?.text = preferences.text("settings.appearance")
            cell.detailTextLabel?.text = preferences.text(preferences.appearance.titleKey)
            cell.imageView?.image = UIImage(systemName: "moon.circle")
            cell.accessibilityIdentifier = "settingsAppearance"
        } else {
            cell.textLabel?.text = preferences.text("settings.about")
            cell.imageView?.image = UIImage(systemName: "info.circle")
            cell.accessibilityIdentifier = "settingsAbout"
        }
        return cell
    }

    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)
        let destination: UIViewController
        switch indexPath.row {
        case 0: destination = LanguageViewController(preferences: preferences)
        case 1: destination = AppearanceViewController(preferences: preferences)
        default: destination = AboutViewController(preferences: preferences)
        }
        navigationController?.pushViewController(destination, animated: true)
    }
}

/// 语言选择写入独立偏好后刷新当前页面，重启仍保留选择。
final class LanguageViewController: UITableViewController {
    private let preferences: DemoPreferences
    init(preferences: DemoPreferences) {
        self.preferences = preferences
        super.init(style: .insetGrouped)
    }
    required init?(coder: NSCoder) { nil }
    override func viewDidLoad() { super.viewDidLoad(); refresh() }
    private func refresh() {
        title = preferences.text("settings.language")
        // 返回按钮属于前一页面；同步整个栈，避免返回设置后仍显示旧语言。
        navigationController?.viewControllers.forEach {
            $0.navigationItem.backButtonTitle = preferences.text("common.back")
        }
        tableView.reloadData()
    }
    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        DemoPreferences.Language.allCases.count
    }
    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let language = DemoPreferences.Language.allCases[indexPath.row]
        let cell = UITableViewCell(style: .default, reuseIdentifier: nil)
        cell.textLabel?.text = preferences.text(language.titleKey)
        cell.accessoryType = preferences.language == language ? .checkmark : .none
        cell.accessibilityIdentifier = "language-\(language.rawValue)"
        cell.accessibilityTraits = preferences.language == language ? [.button, .selected] : .button
        return cell
    }
    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        preferences.language = DemoPreferences.Language.allCases[indexPath.row]
        TFLog.info("Demo 语言设置已更新")
        refresh()
    }
}

/// 关于页只展示应用自身信息，不引入未经确认的公司或联系方式。
final class AboutViewController: UIViewController {
    private let preferences: DemoPreferences
    init(preferences: DemoPreferences) { self.preferences = preferences; super.init(nibName: nil, bundle: nil) }
    required init?(coder: NSCoder) { nil }
    override func viewDidLoad() {
        super.viewDidLoad()
        title = preferences.text("settings.about")
        view.backgroundColor = .systemGroupedBackground
        let icon = UIImageView(image: UIImage(systemName: "bag.circle.fill"))
        icon.contentMode = .scaleAspectFit
        icon.tintColor = .systemTeal
        let name = UILabel()
        name.text = "TeamFlow Demo"
        name.font = .preferredFont(forTextStyle: .title1)
        name.textAlignment = .center
        let description = UILabel()
        description.text = preferences.text("about.description")
        description.accessibilityIdentifier = "aboutDescription"
        description.font = .preferredFont(forTextStyle: .body)
        description.textColor = .secondaryLabel
        description.textAlignment = .center
        description.numberOfLines = 0
        description.adjustsFontForContentSizeCategory = true
        let version = UILabel()
        let number = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0"
        let build = Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "1"
        version.text = "\(preferences.text("about.version")) \(number) (\(build))"
        version.textAlignment = .center
        version.textColor = .secondaryLabel
        version.font = .preferredFont(forTextStyle: .footnote)
        let stack = UIStackView(arrangedSubviews: [icon, name, description, version])
        stack.axis = .vertical
        stack.spacing = 20
        stack.translatesAutoresizingMaskIntoConstraints = false
        view.addSubview(stack)
        NSLayoutConstraint.activate([
            icon.heightAnchor.constraint(equalToConstant: 88),
            stack.topAnchor.constraint(equalTo: view.safeAreaLayoutGuide.topAnchor, constant: 48),
            stack.leadingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.leadingAnchor, constant: 32),
            stack.trailingAnchor.constraint(equalTo: view.safeAreaLayoutGuide.trailingAnchor, constant: -32)
        ])
    }
}

/// 提供系统、浅色、深色三个互斥选项，避免开关丢失「跟随系统」语义。
final class AppearanceViewController: UITableViewController {
    private let preferences: DemoPreferences
    init(preferences: DemoPreferences) {
        self.preferences = preferences
        super.init(style: .insetGrouped)
    }
    required init?(coder: NSCoder) { nil }
    override func viewDidLoad() {
        super.viewDidLoad()
        title = preferences.text("settings.appearance")
    }
    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        DemoPreferences.Appearance.allCases.count
    }
    override func tableView(_ tableView: UITableView, titleForFooterInSection section: Int) -> String? {
        preferences.text("appearance.help")
    }
    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let appearance = DemoPreferences.Appearance.allCases[indexPath.row]
        let cell = UITableViewCell(style: .default, reuseIdentifier: nil)
        cell.textLabel?.text = preferences.text(appearance.titleKey)
        cell.accessoryType = preferences.appearance == appearance ? .checkmark : .none
        cell.accessibilityIdentifier = "appearance-\(appearance.rawValue)"
        cell.accessibilityTraits = preferences.appearance == appearance ? [.button, .selected] : .button
        return cell
    }
    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        preferences.appearance = DemoPreferences.Appearance.allCases[indexPath.row]
        TFLog.info("Demo 外观设置已更新")
        tableView.reloadData()
    }
}
