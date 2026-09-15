import UIKit

/// 多个设置功能共用单选列表；组件只消费展示协议，不认识偏好存储实现。
final class ChoiceViewController: UITableViewController {
    private let viewModel: ChoicePresenting
    init(viewModel: ChoicePresenting) {
        self.viewModel = viewModel
        super.init(style: .insetGrouped)
    }
    required init?(coder: NSCoder) { nil }
    override func viewDidLoad() { super.viewDidLoad(); render() }
    private func render() {
        title = viewModel.title
        navigationController?.viewControllers.forEach { $0.navigationItem.backButtonTitle = viewModel.backTitle }
        tableView.reloadData()
    }
    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { viewModel.items.count }
    override func tableView(_ tableView: UITableView, titleForFooterInSection section: Int) -> String? { viewModel.footer }
    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let item = viewModel.items[indexPath.row]
        let cell = UITableViewCell(style: .default, reuseIdentifier: nil)
        cell.textLabel?.text = item.title
        cell.accessoryType = item.isSelected ? .checkmark : .none
        cell.accessibilityIdentifier = item.identifier
        cell.accessibilityTraits = item.isSelected ? [.button, .selected] : .button
        return cell
    }
    override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        viewModel.select(at: indexPath.row)
        render()
    }
}
