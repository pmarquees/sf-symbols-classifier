import SwiftUI

extension View {
    /// Liquid Glass on macOS 26+, falling back to a material surface on earlier systems.
    @ViewBuilder
    func glassSurface<S: Shape>(_ shape: S, tint: Color? = nil, interactive: Bool = false) -> some View {
        if #available(macOS 26.0, *) {
            let glass = Glass.regular.tint(tint)
            self.glassEffect(interactive ? glass.interactive() : glass, in: shape)
        } else {
            self
                .background(.regularMaterial, in: shape)
                .background(tint ?? .clear, in: shape)
                .overlay { shape.stroke(.separator) }
        }
    }

    /// Hides the macOS 26 scroll edge effect, whose hard style draws a divider under pinned content.
    @ViewBuilder
    func hidingTopScrollEdge() -> some View {
        if #available(macOS 26.0, *) {
            self.scrollEdgeEffectHidden(true, for: .top)
        } else {
            self
        }
    }

    @ViewBuilder
    func glassButton(prominent: Bool = false) -> some View {
        if #available(macOS 26.0, *) {
            if prominent {
                self.buttonStyle(.glassProminent)
            } else {
                self.buttonStyle(.glass)
            }
        } else if prominent {
            self.buttonStyle(.borderedProminent)
        } else {
            self.buttonStyle(.bordered)
        }
    }
}
