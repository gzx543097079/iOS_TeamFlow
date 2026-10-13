import UIKit

/// 场景内唯一组装点：共享购物袋与偏好，协调功能间导航，不承载页面业务规则。
final class DemoCoordinator {
    let navigationController = UINavigationController()
    private let preferences: PreferencesStore
    private let bag: DemoBag
    private let events: DemoEventRecording
    init(preferences: PreferencesStore, bag: DemoBag = DemoBag(), events: DemoEventRecording = DemoEvents()) {
        self.preferences = preferences
        self.bag = bag
        self.events = events
    }
    func start() {
        let page = DemoViewController(viewModel: StoreViewModel(preferences: preferences, bag: bag, events: events))
        page.onOpenProduct = { [weak self] product in
            guard let self = self else { return }
            self.navigationController.pushViewController(ProductViewController(viewModel: ProductViewModel(product: product, preferences: self.preferences, bag: self.bag)), animated: true)
        }
        page.onOpenBag = { [weak self] in
            guard let self = self else { return }
            self.navigationController.pushViewController(BagViewController(viewModel: BagViewModel(preferences: self.preferences, bag: self.bag)), animated: true)
        }
        page.onOpenSettings = { [weak self] in self?.showSettings() }
        navigationController.setViewControllers([page], animated: false)
    }
    private func showSettings() {
        let page = SettingsViewController(viewModel: SettingsViewModel(preferences: preferences))
        page.navigationItem.largeTitleDisplayMode = .never
        page.onSelect = { [weak self] destination in
            guard let self = self else { return }
            let child: UIViewController
            switch destination {
            case .language: child = ChoiceViewController(viewModel: LanguageViewModel(preferences: self.preferences))
            case .appearance: child = ChoiceViewController(viewModel: AppearanceViewModel(preferences: self.preferences))
            case .about: child = AboutViewController(viewModel: AboutViewModel(preferences: self.preferences, version: Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "1.0", build: Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String ?? "1"))
            }
            self.navigationController.pushViewController(child, animated: true)
        }
        navigationController.pushViewController(page, animated: true)
    }
}
