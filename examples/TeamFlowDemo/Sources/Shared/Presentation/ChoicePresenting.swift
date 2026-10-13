import Foundation

protocol ChoicePresenting: AnyObject {
    var title: String { get }
    var backTitle: String { get }
    var footer: String? { get }
    var items: [ChoiceItem] { get }
    func select(at index: Int)
}

struct ChoiceItem {
    let title: String
    let identifier: String
    let isSelected: Bool
}
