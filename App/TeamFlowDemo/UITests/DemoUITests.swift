import XCTest

final class DemoUITests: XCTestCase {
    func testOpenPlanAndReturn() {
        let app = XCUIApplication()
        app.launch()
        XCTAssertTrue(app.buttons["showPlan"].waitForExistence(timeout: 10))
        XCTAssertTrue(app.staticTexts["planSummary"].label.contains("¥6.00 / 月"))
        XCTAssertEqual(app.tabBars.count, 0)
        app.buttons["showPlan"].tap()
        XCTAssertTrue(app.navigationBars["¥6.00 / 月"].waitForExistence(timeout: 5))
        app.navigationBars.buttons.element(boundBy: 0).tap()
        XCTAssertTrue(app.buttons["showPlan"].waitForExistence(timeout: 5))
    }
}
