import UIKit

/// 品牌色随系统外观调整，内容颜色仍采用系统语义颜色。
enum StoreStyle {
    static let accent = UIColor { $0.userInterfaceStyle == .dark
        ? UIColor(red: 0.40, green: 0.83, blue: 0.73, alpha: 1)
        : UIColor(red: 0.08, green: 0.36, blue: 0.31, alpha: 1) }
    static let background = UIColor { $0.userInterfaceStyle == .dark
        ? .systemBackground : UIColor(red: 0.97, green: 0.97, blue: 0.95, alpha: 1) }
    static let tile = UIColor { $0.userInterfaceStyle == .dark
        ? .secondarySystemGroupedBackground : UIColor(red: 0.91, green: 0.94, blue: 0.91, alpha: 1) }

    static func label(_ text: String, style: UIFont.TextStyle, color: UIColor = .label) -> UILabel {
        let label = UILabel()
        label.text = text
        label.font = .preferredFont(forTextStyle: style)
        label.adjustsFontForContentSizeCategory = true
        label.numberOfLines = 0
        label.textColor = color
        return label
    }

    /// 把内容装进可滚动的安全区，窄屏与横屏都能访问底部操作。
    static func content(in view: UIView) -> UIStackView {
        let scroll = UIScrollView()
        let stack = UIStackView()
        stack.axis = .vertical
        stack.spacing = 20
        view.addSubview(scroll)
        scroll.addSubview(stack)
        // 内容边界决定滚动高度，框架宽度约束避免横向溢出。
        scroll.mas_makeConstraints { make in
            make?.top.equalTo()(view.safeAreaLayoutGuide.masAttribute(.top))
            make?.leading.equalTo()(view.safeAreaLayoutGuide.masAttribute(.leading))
            make?.trailing.equalTo()(view.safeAreaLayoutGuide.masAttribute(.trailing))
            make?.bottom.equalTo()(view.safeAreaLayoutGuide.masAttribute(.bottom))
        }
        stack.mas_makeConstraints { make in
            make?.top.equalTo()(scroll.contentLayoutGuide.masAttribute(.top))?.offset()(20)
            make?.leading.equalTo()(scroll.contentLayoutGuide.masAttribute(.leading))?.offset()(20)
            make?.trailing.equalTo()(scroll.contentLayoutGuide.masAttribute(.trailing))?.offset()(-20)
            make?.bottom.equalTo()(scroll.contentLayoutGuide.masAttribute(.bottom))?.offset()(-28)
            make?.width.equalTo()(scroll.frameLayoutGuide.masAttribute(.width))?.offset()(-40)
        }
        return stack
    }
}
