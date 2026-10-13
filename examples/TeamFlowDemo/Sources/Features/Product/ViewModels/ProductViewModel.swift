import Foundation

/// 详情处理加入购物袋意图，并输出可直接渲染的反馈状态。
final class ProductViewModel: DemoViewModel {
    let product: DemoProduct
    private let bag: DemoBag
    private(set) var feedback: String?
    init(product: DemoProduct, preferences: PreferencesStore, bag: DemoBag) {
        self.product = product
        self.bag = bag
        super.init(preferences: preferences)
    }
    var item: ProductItem { ProductItem(product: product, preferences: preferences) }
    func addToBag() {
        bag.add(product)
        feedback = text("store.productDetail.addedMessage")
    }
}
