import XCTest

final class DemoUITests: XCTestCase {
    func testOpenPlanAndReturn() {
        let app = XCUIApplication()
        app.launchArguments = ["-demo-ui-testing", "-reset-demo-preferences"]
        app.launch()
        XCTAssertTrue(app.buttons["showPlan"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["planSummary"].label.contains("¥6.00 / 月"))
        XCTAssertEqual(app.tabBars.count, 0)
        app.buttons["showPlan"].tap()
        XCTAssertTrue(app.navigationBars["¥6.00 / 月"].waitForExistence(timeout: 5))
        app.navigationBars.buttons.element(boundBy: 0).tap()
        XCTAssertTrue(app.buttons["showPlan"].waitForExistence(timeout: 5))
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
        app.cells["settingsAbout"].tap()
        XCTAssertTrue(app.staticTexts["aboutDescription"].label.contains("不提供真实购买"))
    }
}
