import UIKit

extension UILayoutGuide {
    /// 保留布局指南为约束对象，同时提供所属视图供 Masonry 寻找公共父视图。
    /// 仅在指南已经归属视图后调用，适用于安全区域和滚动视图的两种指南。
    func masAttribute(_ attribute: NSLayoutConstraint.Attribute) -> MASViewAttribute {
        MASViewAttribute(view: owningView, item: self, layoutAttribute: attribute)
    }
}
