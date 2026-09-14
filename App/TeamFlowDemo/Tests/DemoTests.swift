import XCTest
@testable import TeamFlowDemo

final class DemoTests: XCTestCase {
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

    @MainActor func testAppearanceAppliesPersistsAndReturnsToSystem() {
        let suite = "DemoTests." + UUID().uuidString
        let defaults = UserDefaults(suiteName: suite)!
        defer { defaults.removePersistentDomain(forName: suite) }
        let preferences = DemoPreferences(defaults: defaults)
        let window = UIWindow()
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
        weak var language: LanguageViewController?
        weak var about: AboutViewController?
        autoreleasepool {
            let controller = SettingsViewController()
            settings = controller
            let navigation = UINavigationController(rootViewController: controller)
            let picker = LanguageViewController(preferences: .shared)
            language = picker
            navigation.pushViewController(picker, animated: false)
            picker.loadViewIfNeeded()
            let info = AboutViewController(preferences: .shared)
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

    @MainActor func testNavigationRecordsOneEventAndUsesSelectedProduct() {
        let events = DemoEvents()
        let product = DemoProduct.catalog[2]
        let controller = DemoViewController(events: events)
        let navigation = UINavigationController(rootViewController: controller)
        controller.loadViewIfNeeded()
        controller.showProduct(product)
        XCTAssertEqual(events.names, ["demo_product_open"])
        XCTAssertEqual((navigation.topViewController as? ProductViewController)?.product, product)
        XCTAssertEqual(navigation.viewControllers.count, 2)
    }

    @MainActor func testStoreScreensReleaseWithNavigation() {
        weak var reference: DemoViewController?
        weak var detail: ProductViewController?
        weak var cart: BagViewController?
        autoreleasepool {
            let controller = DemoViewController()
            reference = controller
            let navigation = UINavigationController(rootViewController: controller)
            controller.loadViewIfNeeded()
            controller.showProduct(DemoProduct.catalog[0])
            detail = navigation.topViewController as? ProductViewController
            detail?.loadViewIfNeeded()
            let bagPage = BagViewController(preferences: .shared, bag: controller.bag)
            cart = bagPage
            navigation.pushViewController(bagPage, animated: false)
            bagPage.loadViewIfNeeded()
        }
        XCTAssertNil(reference)
        XCTAssertNil(detail)
        XCTAssertNil(cart)
    }
}
