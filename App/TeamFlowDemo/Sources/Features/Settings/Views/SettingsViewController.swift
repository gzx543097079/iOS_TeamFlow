import UIKit

/// 设置页面仅渲染行快照，导航目的通过回调交给 Application 组装。
final class SettingsViewController: UITableViewController {
    private let viewModel: SettingsViewModel
    var onSelect: ((SettingsItem.Destination) -> Void)?
    init(viewModel: SettingsViewModel) {
        self.viewModel = viewModel
        super.init(style: .insetGrouped)
    }
    required init?(coder: NSCoder) { nil }
    override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        title = viewModel.text("settings.title")
        navigationItem.backButtonTitle = viewModel.text("common.navigation.backButton")
        tableView.reloadData()
    }
    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { viewModel.items.count }
    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let item = viewModel.items[indexPath.row]
        let cell = UITableViewCell(style: .value1, reuseIdentifier: nil)
        cell.accessoryType = .disclosureIndicator
        cell.textLabel?.font = .preferredFont(forTextStyle: .body)
        cell.textLabel?.adjustsFontForContentSizeCategory = true
        cell.detailTextLabel?.adjustsFontForContentSizeCategory = true
        cell.textLabel?.text = item.title
        cell.detailTextLabel?.text = item.detail
        cell.imageView?.image = UIImage(systemName: item.symbol)
        cell.accessibilityIdentifier = item.identifier
        return cell
    }
    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)
        onSelect?(viewModel.items[indexPath.row].destination)
    }
}
