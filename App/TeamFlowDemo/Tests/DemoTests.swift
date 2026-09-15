import XCTest
@testable import TeamFlowDemo

final class DemoTests: XCTestCase {
    @MainActor func testScrollableContentFitsResizedViewport() throws {
        // 验证滚动指南桥接后的真实尺寸，覆盖窄屏、横屏和 iPad 宽度。
        for size in [CGSize(width: 320, height: 568), CGSize(width: 844, height: 390), CGSize(width: 768, height: 1024)] {
            let host = UIView(frame: CGRect(origin: .zero, size: size))
            let content = StoreStyle.content(in: host)
            let label = UILabel()
            label.numberOfLines = 0
            label.text = String(repeating: "商品说明 Product description ", count: 300)
            content.addArrangedSubview(label)
            host.layoutIfNeeded()
            let scroll = try XCTUnwrap(content.superview as? UIScrollView)
            XCTAssertEqual(scroll.frame.width, size.width, accuracy: 0.5)
            XCTAssertEqual(content.frame.width, scroll.bounds.width - 40, accuracy: 0.5)
            XCTAssertEqual(scroll.contentSize.width, scroll.bounds.width, accuracy: 0.5)
            XCTAssertGreaterThan(scroll.contentSize.height, scroll.bounds.height)
            XCTAssertFalse(content.hasAmbiguousLayout)
        }
    }

    func testLogMessageEvaluationMatchesBuildConfiguration() {
        var count = 0
        func message() -> String { count += 1; return "本地测试消息" }
        TFLog.debug(message())
        TFLog.info(message())
        TFLog.warning(message())
        TFLog.error(message())
        TFLog.fault(message())
        #if DEBUG
        XCTAssertEqual(count, 5)
        #else
        XCTAssertEqual(count, 0)
        #endif
    }

    @MainActor func testSceneOwnsLiveWindowAndRootNavigation() throws {
        let scene = try XCTUnwrap(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first)
        let delegate = try XCTUnwrap(scene.delegate as? SceneDelegate)
        let window = try XCTUnwrap(delegate.window)
        XCTAssertTrue(window.windowScene === scene)
        let navigation = try XCTUnwrap(window.rootViewController as? UINavigationController)
        XCTAssertTrue(navigation.viewControllers.first is DemoViewController)
        XCTAssertFalse(window.isHidden)
    }

    @MainActor func testAppearanceAppliesPersistsAndReturnsToSystem() throws {
        let suite = "DemoTests." + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let preferences = DemoPreferences(defaults: defaults)
        let scene = try XCTUnwrap(UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }.first)
        let window = UIWindow(windowScene: scene)
        var binding: DemoAppearanceBinding? = DemoAppearanceBinding(window: window, preferences: preferences)
        XCTAssertEqual(window.overrideUserInterfaceStyle, .unspecified)
        preferences.appearance = .dark
        XCTAssertEqual(window.overrideUserInterfaceStyle, .dark)
        XCTAssertEqual(DemoPreferences(defaults: defaults).appearance, .dark)
        preferences.appearance = .light
        XCTAssertEqual(window.overrideUserInterfaceStyle, .light)
        preferences.appearance = .system
        XCTAssertEqual(window.overrideUserInterfaceStyle, .unspecified)
        weak var released = binding
        binding = nil
        XCTAssertNil(released)
        preferences.appearance = .dark
        XCTAssertEqual(window.overrideUserInterfaceStyle, .unspecified, "释放绑定后不再响应通知")
    }

    func testLanguagePersistsAndResolvesBothTranslations() {
        let suite = "DemoTests." + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let preferences = DemoPreferences(defaults: defaults)
        XCTAssertEqual(preferences.language, .system)
        preferences.language = .chinese
        XCTAssertEqual(preferences.text("settings.title"), "设置")
        let reopened = DemoPreferences(defaults: defaults)
        XCTAssertEqual(reopened.language, .chinese)
        reopened.language = .english
        XCTAssertEqual(reopened.text("settings.title"), "Settings")
        XCTAssertEqual(reopened.text("settings.about"), "About Us")
    }

    @MainActor func testSettingsScreensReleaseWithNavigation() {
        weak var settings: SettingsViewController?
        weak var language: ChoiceViewController?
        weak var about: AboutViewController?
        autoreleasepool {
            let controller = SettingsViewController(viewModel: SettingsViewModel(preferences: DemoPreferences.shared))
            settings = controller
            let navigation = UINavigationController(rootViewController: controller)
            let picker = ChoiceViewController(viewModel: LanguageViewModel(preferences: DemoPreferences.shared))
            language = picker
            navigation.pushViewController(picker, animated: false)
            picker.loadViewIfNeeded()
            let info = AboutViewController(viewModel: AboutViewModel(preferences: DemoPreferences.shared, version: "1.0", build: "1"))
            about = info
            navigation.pushViewController(info, animated: false)
            info.loadViewIfNeeded()
        }
        XCTAssertNil(settings)
        XCTAssertNil(language)
        XCTAssertNil(about)
    }

    func testCatalogFiltersAndBagTotalsUseActualProducts() {
        let audio = DemoProduct.filtered(by: .audio)
        XCTAssertEqual(audio.map(\.id), ["headphones", "speaker"])
        XCTAssertEqual(DemoProduct.filtered(by: .all).count, 4)
        let bag = DemoBag()
        XCTAssertEqual(bag.count, 0)
        bag.add(audio[0])
        bag.add(audio[0])
        bag.add(audio[1])
        XCTAssertEqual(bag.count, 3)
        XCTAssertEqual(bag.totalCents, 79700)
        bag.remove(audio[0])
        XCTAssertEqual(bag.count, 1)
        XCTAssertEqual(bag.totalCents, 19900)
        bag.remove(audio[1])
        XCTAssertTrue(bag.products.isEmpty)
        XCTAssertEqual(bag.totalCents, 0)
    }

    @MainActor func testNavigationRecordsOneEventAndUsesSelectedProduct() throws {
        let events = DemoEvents()
        let product = DemoProduct.catalog[2]
        let coordinator = DemoCoordinator(preferences: DemoPreferences.shared, events: events)
        coordinator.start()
        let navigation = coordinator.navigationController
        let controller = try XCTUnwrap(navigation.viewControllers.first as? DemoViewController)
        controller.loadViewIfNeeded()
        controller.showProduct(product)
        XCTAssertEqual(events.names, ["demo_product_open"])
        XCTAssertEqual((navigation.topViewController as? ProductViewController)?.viewModel.product, product)
        XCTAssertEqual(navigation.viewControllers.count, 2)
    }

    @MainActor func testStoreScreensReleaseWithNavigation() {
        weak var reference: DemoViewController?
        weak var detail: ProductViewController?
        weak var cart: BagViewController?
        autoreleasepool {
            let controller = DemoViewController(viewModel: StoreViewModel(preferences: DemoPreferences.shared, events: DemoEvents()))
            reference = controller
            let navigation = UINavigationController(rootViewController: controller)
            controller.loadViewIfNeeded()
            let detailPage = ProductViewController(viewModel: ProductViewModel(product: DemoProduct.catalog[0], preferences: DemoPreferences.shared, bag: DemoBag()))
            navigation.pushViewController(detailPage, animated: false)
            detail = detailPage
            detail?.loadViewIfNeeded()
            let bagPage = BagViewController(viewModel: BagViewModel(preferences: DemoPreferences.shared, bag: DemoBag()))
            cart = bagPage
            navigation.pushViewController(bagPage, animated: false)
            bagPage.loadViewIfNeeded()
        }
        XCTAssertNil(reference)
        XCTAssertNil(detail)
        XCTAssertNil(cart)
    }
}
