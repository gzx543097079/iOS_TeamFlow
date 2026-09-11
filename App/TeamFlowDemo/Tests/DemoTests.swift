import XCTest
@testable import TeamFlowDemo

final class DemoTests: XCTestCase {
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
