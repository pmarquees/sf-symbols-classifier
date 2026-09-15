import SwiftUI

/// Explains the bundled SFS1 model. Figures come from the v1 export manifest and sealed eval report.
struct HowItWorksPanel: View {
    @Binding var isPresented: Bool

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 28) {
                intro
                stats
                pipeline
                training
                accuracy
                runtime
            }
            .padding(22)
        }
    }

    private var intro: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("HOW THIS WORKS")
                    .font(.caption2.weight(.bold))
                    .tracking(1.2)
                    .foregroundStyle(.secondary)
                Spacer()
                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 11, weight: .bold))
                        .frame(width: 22, height: 22)
                }
                .glassButton()
                .buttonBorderShape(.circle)
                .help("Hide explanation")
                .accessibilityLabel("Close explanation")
            }
            Text("Our own model, running on your Mac")
                .font(.system(.title2, design: .rounded).weight(.bold))
                .fixedSize(horizontal: false, vertical: true)
            Text("Symbol Finder doesn’t call a server or a general-purpose AI. It uses SFS1, a tiny classifier trained for one job: turning a plain-language description into SF Symbol names.")
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }

    private var stats: some View {
        HStack(spacing: 10) {
            StatTile(value: "2.7 MB", caption: "of weights")
            StatTile(value: "9,524", caption: "symbols")
            StatTile(value: "0", caption: "network calls")
        }
    }

    private var pipeline: some View {
        PanelSection(title: "What happens when you type") {
            Step(number: 1, symbol: "textformat", title: "Clean up the text",
                 detail: "Lowercase it, strip accents, and turn punctuation into spaces, so “Café Wi-Fi!” becomes “cafe wi fi”.")
            Step(number: 2, symbol: "scissors", title: "Break it into pieces",
                 detail: "Split it into overlapping 2- to 5-letter fragments plus whole words. Fragments make it forgiving of typos and half-typed words.")
            Step(number: 3, symbol: "number", title: "Hash each piece",
                 detail: "Each fragment is hashed with FNV-1a into one of 16,384 buckets, so there’s no vocabulary list to ship.")
            Step(number: 4, symbol: "plus.forwardslash.minus", title: "Build a meaning vector",
                 detail: "Every bucket holds 96 learned numbers. Adding up the buckets for your fragments gives one vector that captures what you described.")
            Step(number: 5, symbol: "square.grid.3x3", title: "Score every symbol",
                 detail: "That vector is compared with a learned vector for each of the 9,524 symbols. The highest scores fill the grid, best first.")
        }
    }

    private var training: some View {
        PanelSection(title: "How it was trained") {
            Bullet("Examples come from Apple’s SF Symbols 27 catalog, including symbol names, search keywords, and categories, plus a small hand-curated set of UI intents such as “delete” → trash.")
            Bullet("Each example is rewritten in six styles: clean, terse, verbose, messy, with distractors, and adversarial, so the model copes with how people really type.")
            Bullet("Several candidates were trained in PyTorch. The winner had the best validation accuracy while staying under a 5 MB limit.")
            Bullet("Its weights were then squeezed into 8-bit integers, costing just 0.05 points of accuracy.")
        }
    }

    private var accuracy: some View {
        PanelSection(title: "How good is it?") {
            VStack(spacing: 12) {
                AccuracyBar(label: "Right answer is #1", value: 0.683, emphasized: true)
                AccuracyBar(label: "Right answer in top 5", value: 0.854, emphasized: true)
            }

            Text("By prompt style (top 1)")
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)
                .padding(.top, 4)

            VStack(spacing: 8) {
                AccuracyBar(label: "Terse", value: 0.894)
                AccuracyBar(label: "Clean", value: 0.862)
                AccuracyBar(label: "Verbose", value: 0.839)
                AccuracyBar(label: "Messy", value: 0.776)
                AccuracyBar(label: "Adversarial", value: 0.375)
                AccuracyBar(label: "Distractor", value: 0.350)
            }

            Label {
                Text("Measured on held-out prompts generated from Apple’s metadata, not real searches, so treat these numbers as optimistic. Scores rank symbols; they aren’t confidence percentages.")
                    .fixedSize(horizontal: false, vertical: true)
            } icon: {
                Image(systemName: "info.circle")
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
    }

    private var runtime: some View {
        PanelSection(title: "Where it runs") {
            Bullet("The 2.7 MB model ships as a Swift package resource and loads directly into the native runtime.")
            Bullet("SwiftUI draws each result with Apple’s own Image(systemName:), so every preview is the real installed symbol.")
            Bullet("The JavaScript package uses the same model and produces identical rankings across 100 reference prompts.")
        }
    }
}

private struct PanelSection<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(title)
                .font(.headline)
            content
        }
    }
}

private struct StatTile: View {
    let value: String
    let caption: String

    var body: some View {
        VStack(spacing: 3) {
            Text(value)
                .font(.system(.title3, design: .rounded).weight(.bold))
                .monospacedDigit()
            Text(caption)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 12)
        .glassSurface(RoundedRectangle(cornerRadius: 16, style: .continuous))
    }
}

private struct Step: View {
    let number: Int
    let symbol: String
    let title: String
    let detail: String

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: symbol)
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(.primary)
                .frame(width: 34, height: 34)
                .glassSurface(Circle())

            VStack(alignment: .leading, spacing: 3) {
                Text("\(number). \(title)")
                    .font(.subheadline.weight(.semibold))
                Text(detail)
                    .font(.callout)
                    .foregroundStyle(.secondary)
                    .fixedSize(horizontal: false, vertical: true)
            }
        }
    }
}

private struct Bullet: View {
    let text: String

    init(_ text: String) {
        self.text = text
    }

    var body: some View {
        HStack(alignment: .firstTextBaseline, spacing: 8) {
            Circle()
                .fill(.secondary)
                .frame(width: 5, height: 5)
                .alignmentGuide(.firstTextBaseline) { $0[VerticalAlignment.center] + 4 }
            Text(text)
                .font(.callout)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}

private struct AccuracyBar: View {
    let label: String
    let value: Double
    var emphasized = false

    var body: some View {
        VStack(alignment: .leading, spacing: 5) {
            HStack {
                Text(label)
                Spacer()
                Text(value, format: .percent.precision(.fractionLength(0)))
                    .monospacedDigit()
                    .foregroundStyle(emphasized ? .primary : .secondary)
            }
            .font(emphasized ? .subheadline.weight(.medium) : .caption)

            GeometryReader { proxy in
                ZStack(alignment: .leading) {
                    Capsule().fill(.quaternary)
                    Capsule()
                        .fill(emphasized ? AnyShapeStyle(Color.blue) : AnyShapeStyle(Color.secondary))
                        .frame(width: proxy.size.width * value)
                }
            }
            .frame(height: emphasized ? 8 : 5)
        }
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(label))
        .accessibilityValue(Text(value, format: .percent.precision(.fractionLength(0))))
    }
}
