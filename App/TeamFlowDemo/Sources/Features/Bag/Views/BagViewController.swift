import UIKit

/// 购物袋按商品汇总数量，左滑每次减少一件；无结算入口。
final class BagViewController: UITableViewController {
    private let viewModel: BagViewModel
    init(viewModel: BagViewModel) {
        self.viewModel = viewModel
        super.init(style: .insetGrouped)
    }
    required init?(coder: NSCoder) { nil }
    override func viewDidLoad() {
        super.viewDidLoad()
        title = viewModel.text("bag.title")
        navigationItem.largeTitleDisplayMode = .never
        tableView.accessibilityIdentifier = "shoppingBag"
        tableView.rowHeight = UITableView.automaticDimension
        tableView.estimatedRowHeight = 68
    }
    override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int { viewModel.items.count }
    override func tableView(_ tableView: UITableView, titleForHeaderInSection section: Int) -> String? {
        viewModel.header
    }
    override func tableView(_ tableView: UITableView, titleForFooterInSection section: Int) -> String? {
        viewModel.footer
    }
    override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let product = viewModel.items[indexPath.row]
        let cell = UITableViewCell(style: .subtitle, reuseIdentifier: nil)
        cell.textLabel?.text = product.name
        cell.detailTextLabel?.text = product.detail
        cell.imageView?.image = UIImage(systemName: product.symbol)
        cell.imageView?.tintColor = StoreStyle.accent
        cell.accessibilityIdentifier = "bag-\(product.id)"
        cell.selectionStyle = .none
        return cell
    }
    override func tableView(_ tableView: UITableView, trailingSwipeActionsConfigurationForRowAt indexPath: IndexPath) -> UISwipeActionsConfiguration? {
        let product = viewModel.items[indexPath.row]
        let remove = UIContextualAction(style: .destructive, title: viewModel.text("bag.swipeAction.removeOne")) { [weak self] _, _, completion in
            self?.viewModel.removeOne(id: product.id)
            self?.tableView.reloadData()
            completion(true)
        }
        return UISwipeActionsConfiguration(actions: [remove])
    }
}
