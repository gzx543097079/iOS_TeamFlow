import XCTest

final class DemoUITests: XCTestCase {
    func testShopBrowseAddAndRemove() {
        let app = XCUIApplication()
        app.launchArguments = ["-demo-ui-testing", "-reset-demo-preferences", "-AppleLanguages", "(en)"]
        app.launch()
        XCTAssertTrue(app.buttons["product-headphones"].waitForExistence(timeout: 10))
        XCTAssertEqual(app.tabBars.count, 0)
        capture("shop-light", app: app)
        XCUIDevice.shared.orientation = .landscapeLeft
        let rotated = expectation(for: NSPredicate { _, _ in app.frame.width > app.frame.height }, evaluatedWith: app)
        wait(for: [rotated], timeout: 5)
        capture("shop-landscape", app: app)
        XCUIDevice.shared.orientation = .portrait
        app.segmentedControls["storeCategories"].buttons["Audio"].tap()
        XCTAssertFalse(app.buttons["product-bag"].exists)
        app.buttons["product-headphones"].tap()
        XCTAssertTrue(app.staticTexts["productPrice"].label.contains("299"))
        app.buttons["addToBag"].tap()
        XCTAssertTrue(app.staticTexts["bagFeedback"].exists)
        capture("product-detail", app: app)
        app.navigationBars.buttons.element(boundBy: 0).tap()
        app.buttons["openBag"].tap()
        XCTAssertTrue(app.cells["bag-headphones"].exists)
        app.cells["bag-headphones"].swipeLeft()
        app.buttons["Remove"].tap()
        XCTAssertFalse(app.cells["bag-headphones"].exists)
        XCTAssertTrue(app.staticTexts["Your bag is empty"].exists)
    }

    private func capture(_ name: String, app: XCUIApplication) {
        // 旋转后使用整屏截图，避免应用裁剪区域仍使用旋转前的坐标。
        let attachment = XCTAttachment(screenshot: XCUIScreen.main.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }

    func testLanguageSwitchAboutAndPersistence() {
        let app = XCUIApplication()
        app.launchArguments = ["-demo-ui-testing", "-reset-demo-preferences"]
        app.launch()
        app.buttons["openSettings"].tap()
        app.cells["settingsLanguage"].tap()
        app.cells["language-en"].tap()
        XCTAssertTrue(app.navigationBars["Language"].exists)
        app.navigationBars.buttons.element(boundBy: 0).tap()
        XCTAssertTrue(app.navigationBars["Settings"].exists)
        app.cells["settingsAbout"].tap()
        XCTAssertTrue(app.navigationBars["About Us"].exists)
        XCTAssertTrue(app.staticTexts["aboutDescription"].label.contains("no real purchases"))
        app.terminate()
        app.launchArguments = ["-demo-ui-testing"]
        app.launch()
        app.buttons["openSettings"].tap()
        XCTAssertTrue(app.navigationBars["Settings"].exists)
        app.cells["settingsLanguage"].tap()
        XCTAssertTrue(app.cells["language-en"].isSelected)
        app.cells["language-zh-Hans"].tap()
        XCTAssertTrue(app.navigationBars["语言"].exists)
        app.navigationBars.buttons.element(boundBy: 0).tap()
        XCTAssertTrue(app.navigationBars["设置"].exists)
        XCTAssertEqual(app.navigationBars.buttons.element(boundBy: 0).label, "返回")
        capture("settings-chinese", app: app)
        app.cells["settingsAbout"].tap()
        XCTAssertTrue(app.staticTexts["aboutDescription"].label.contains("不提供真实购买"))
        capture("about-chinese", app: app)
        app.navigationBars.buttons.element(boundBy: 0).tap()
        app.navigationBars.buttons.element(boundBy: 0).tap()
        XCTAssertTrue(app.navigationBars["商城"].exists)
        capture("shop-chinese", app: app)
    }
    func testAppearanceSelectionPersistsAndCanFollowSystem() {
        let app = XCUIApplication()
        app.launchArguments = ["-demo-ui-testing", "-reset-demo-preferences"]
        app.launch()
        app.buttons["openSettings"].tap()
        app.cells["settingsAppearance"].tap()
        XCTAssertTrue(app.cells["appearance-system"].isSelected)
        app.cells["appearance-dark"].tap()
        XCTAssertTrue(app.cells["appearance-dark"].isSelected)
        XCUIDevice.shared.press(.home)
        app.activate()
        XCTAssertTrue(app.cells["appearance-dark"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.cells["appearance-dark"].isSelected)
        capture("appearance-dark", app: app)
        app.navigationBars.buttons.element(boundBy: 0).tap()
        app.navigationBars.buttons.element(boundBy: 0).tap()
        capture("shop-dark", app: app)
        app.terminate()
        app.launchArguments = ["-demo-ui-testing"]
        app.launch()
        app.buttons["openSettings"].tap()
        app.cells["settingsAppearance"].tap()
        XCTAssertTrue(app.cells["appearance-dark"].isSelected)
        app.cells["appearance-light"].tap()
        XCTAssertTrue(app.cells["appearance-light"].isSelected)
        app.cells["appearance-system"].tap()
        XCTAssertTrue(app.cells["appearance-system"].isSelected)
    }
}
