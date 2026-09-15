import XCTest
@testable import TeamFlowDemo

/// 用内存替身验证展示逻辑，不启动页面、不读取用户真实偏好。
final class ViewModelTests: XCTestCase {
    func testStoreFilterPreservesSelectionAndRejectsInvalidIndex() {
        let preferences = MemoryPreferences()
        let events = RecordingEvents()
        let model = StoreViewModel(preferences: preferences, events: events)
        model.selectCategory(at: 1)
        XCTAssertEqual(model.items.map(\.id), ["headphones", "speaker"])
        model.selectCategory(at: -1)
        model.selectCategory(at: 99)
        XCTAssertEqual(model.selectedCategoryIndex, 1)
        model.selectProduct(model.items[0].product)
        XCTAssertEqual(events.names, ["demo_product_open"])
        preferences.language = .chinese
        XCTAssertTrue(model.items[0].name.hasPrefix("zh-Hans:"))
        XCTAssertEqual(model.selectedCategoryIndex, 1)
    }

    func testDetailAndBagShareStateAndRemoveByStableID() {
        let preferences = MemoryPreferences()
        let bag = DemoBag()
        let store = StoreViewModel(preferences: preferences, bag: bag, events: RecordingEvents())
        let detail = ProductViewModel(product: DemoProduct.catalog[0], preferences: preferences, bag: bag)
        let list = BagViewModel(preferences: preferences, bag: bag)
        XCTAssertNil(detail.feedback)
        detail.addToBag()
        detail.addToBag()
        XCTAssertNotNil(detail.feedback)
        XCTAssertTrue(store.bagTitle.hasSuffix("· 2"))
        XCTAssertEqual(list.items.map(\.id), ["headphones"])
        XCTAssertTrue(list.items[0].detail.hasPrefix("2 ×"))
        XCTAssertTrue(list.footer.contains("598"))
        list.remove(id: "missing")
        XCTAssertEqual(list.items.count, 1)
        list.remove(id: "headphones")
        XCTAssertTrue(list.items.isEmpty)
        XCTAssertTrue(store.bagTitle.hasSuffix("· 0"))
    }

    func testLanguageAndAppearanceRefreshSharedSettings() {
        let preferences = MemoryPreferences()
        let settings = SettingsViewModel(preferences: preferences)
        let language = LanguageViewModel(preferences: preferences)
        let appearance = AppearanceViewModel(preferences: preferences)
        language.select(at: 2)
        XCTAssertEqual(preferences.language, .chinese)
        XCTAssertEqual(language.items.filter(\.isSelected).count, 1)
        XCTAssertTrue(settings.items[0].detail?.contains("zh-Hans") == true)
        appearance.select(at: 2)
        XCTAssertEqual(preferences.appearance, .dark)
        XCTAssertTrue(settings.items[1].detail?.contains("dark") == true)
        appearance.select(at: 0)
        XCTAssertEqual(preferences.appearance, .system)
        language.select(at: 100)
        appearance.select(at: -1)
        XCTAssertEqual(preferences.language, .chinese)
        XCTAssertEqual(preferences.appearance, .system)
    }

    func testAboutUsesInjectedVersion() {
        let model = AboutViewModel(preferences: MemoryPreferences(), version: "8.7", build: "42")
        XCTAssertTrue(model.versionText.hasSuffix("8.7 (42)"))
        XCTAssertEqual(model.name, "TeamFlow Demo")
    }

    @MainActor func testCoordinatorAndPageCallbacksReleaseTogether() {
        weak var coordinator: DemoCoordinator?
        weak var store: DemoViewController?
        autoreleasepool {
            let owner = DemoCoordinator(preferences: MemoryPreferences(), events: RecordingEvents())
            coordinator = owner
            owner.start()
            store = owner.navigationController.viewControllers.first as? DemoViewController
            store?.onOpenSettings?()
            let settings = owner.navigationController.topViewController as? SettingsViewController
            settings?.onSelect?(.language)
            XCTAssertTrue(owner.navigationController.topViewController is ChoiceViewController)
        }
        XCTAssertNil(coordinator)
        XCTAssertNil(store)
    }
}

private final class MemoryPreferences: PreferencesStore {
    var language: DemoLanguage = .english
    var appearance: DemoAppearance = .system
    var locale: Locale { Locale(identifier: language == .chinese ? "zh-Hans" : "en") }
    func text(_ key: String) -> String {
        if key == "store.count" || key == "bag.items" { return "%d" }
        return "\(language.rawValue):\(key)"
    }
}

private final class RecordingEvents: DemoEventRecording {
    var names: [String] = []
    func record(_ name: String) { names.append(name) }
}
