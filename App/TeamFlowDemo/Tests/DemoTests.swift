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

    func testPlanUsesSamePriceAndPeriod() {
        let plan = DemoPlan(productID: "fixture.yearly", displayPrice: "$24.99", period: "年")
        XCTAssertEqual(plan.summary, "$24.99 / 年")
        XCTAssertEqual(DemoPlan.monthly.summary, "¥6.00 / 月")
    }

    @MainActor func testNavigationRecordsOneEventAndUsesSelectedPlan() {
        let events = DemoEvents()
        let plan = DemoPlan(productID: "fixture.yearly", displayPrice: "¥60.00", period: "年")
        let controller = DemoViewController(plan: plan, events: events)
        let navigation = UINavigationController(rootViewController: controller)
        controller.loadViewIfNeeded()
        controller.showPlan()
        XCTAssertEqual(events.names, ["demo_plan_open"])
        XCTAssertEqual(navigation.topViewController?.title, plan.summary)
        XCTAssertEqual(navigation.viewControllers.count, 2)
    }

    @MainActor func testControllerReleasesAfterNavigationIsReleased() {
        weak var reference: DemoViewController?
        autoreleasepool {
            let controller = DemoViewController()
            reference = controller
            let navigation = UINavigationController(rootViewController: controller)
            controller.loadViewIfNeeded()
            controller.showPlan()
            _ = navigation.popViewController(animated: false)
        }
        XCTAssertNil(reference)
    }
}
