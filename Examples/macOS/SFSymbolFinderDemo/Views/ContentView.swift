import AppKit
import SwiftUI

struct ContentView: View {
    @ObservedObject var classifier: ClassifierService
    @State private var query = ""
    @State private var symbols: [SymbolRecommendation] = []
    @State private var selection: String?
    @State private var copiedName: String?
    @State private var showsExplainer = false
    @FocusState private var searchFocused: Bool

    private let examples = [
        "Share my location",
        "A rainy evening",
        "Start a video call",
        "Delete this file",
        "Quiet alarm for tomorrow"
    ]

    private let columns = [GridItem(.adaptive(minimum: 104, maximum: 124), spacing: 14, alignment: .top)]

    var body: some View {
        // A plain HStack instead of .inspector: the inspector's split view sized the whole window
        // to the explainer's full scroll height, pushing the UI off-screen.
        HStack(spacing: 0) {
            mainColumn
                .frame(maxWidth: .infinity, maxHeight: .infinity)

            if showsExplainer {
                HowItWorksPanel(isPresented: $showsExplainer)
                    .frame(width: 380)
                    .frame(maxHeight: .infinity)
                    .clipShape(RoundedRectangle(cornerRadius: 28, style: .continuous))
                    .glassSurface(RoundedRectangle(cornerRadius: 28, style: .continuous))
                    .padding([.vertical, .trailing], 12)
                    .transition(.move(edge: .trailing).combined(with: .opacity))
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(backdrop)
        .navigationTitle("Symbol Finder")
        .animation(.smooth(duration: 0.35), value: showsExplainer)
        .onAppear { searchFocused = true }
        .onChange(of: query) { _, value in
            selection = nil
            classifier.predict(value)
        }
        .onChange(of: classifier.recommendations) { _, recommendations in
            // Drop names this macOS can't render, like the SF Symbols app only lists installed symbols.
            symbols = recommendations.filter { NSImage(systemSymbolName: $0.name, accessibilityDescription: nil) != nil }
        }
        .onCopyCommand {
            guard let selection else { return [] }
            return [NSItemProvider(object: selection as NSString)]
        }
        .animation(.smooth(duration: 0.35), value: query.isEmpty)
        .animation(.smooth(duration: 0.25), value: copiedName)
    }

    private var mainColumn: some View {
        // Search sits above the scroll view rather than in its safe-area inset, which drew a divider.
        VStack(spacing: 0) {
            searchPanel

            ScrollView {
                resultsSection
                    .padding(.horizontal, 32)
                    .padding(.top, 8)
                    .padding(.bottom, 32)
                    .frame(maxWidth: 1080)
                    .frame(maxWidth: .infinity)
            }
            .hidingTopScrollEdge()
        }
        .overlay(alignment: .bottom) { copiedToast }
    }

    // MARK: Search panel

    private var searchPanel: some View {
        VStack(alignment: .leading, spacing: 18) {
            headerRow

            if query.isEmpty {
                VStack(alignment: .leading, spacing: 10) {
                    Text("9,524 SYMBOLS · ON DEVICE")
                        .font(.caption2.weight(.bold))
                        .tracking(1.2)
                        .foregroundStyle(.secondary)
                    Text("Describe it. Find the symbol.")
                        .font(.system(size: 46, weight: .bold, design: .rounded))
                        .tracking(-1.8)
                    Text("Type what the icon should communicate. Every keystroke reruns our classifier locally and fills the grid with real SF Symbols.")
                        .font(.title3)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
                .transition(.opacity.combined(with: .move(edge: .top)))
            }

            searchField
            suggestions
        }
        .padding(.horizontal, 32)
        .padding(.top, 14)
        .padding(.bottom, 16)
        .frame(maxWidth: 1080, alignment: .leading)
        .frame(maxWidth: .infinity)
    }

    private var headerRow: some View {
        HStack(spacing: 10) {
            Text("SF")
                .font(.caption2.weight(.bold))
                .foregroundStyle(.primary)
                .frame(width: 30, height: 30)
                .glassSurface(RoundedRectangle(cornerRadius: 9, style: .continuous))

            Text("Symbol Finder")
                .font(.subheadline.weight(.semibold))

            Spacer()

            StatusPill(state: classifier.state)

            Button {
                showsExplainer.toggle()
            } label: {
                Label("How this works?", systemImage: "sparkles")
            }
            .glassButton()
        }
    }

    private var searchField: some View {
        HStack(spacing: 14) {
            Image(systemName: "magnifyingglass")
                .font(.system(size: 20, weight: .semibold))
                .foregroundStyle(searchFocused ? .blue : .secondary)

            TextField("Describe what the symbol should communicate", text: $query)
                .textFieldStyle(.plain)
                .font(.system(size: 22, weight: .medium, design: .rounded))
                .focused($searchFocused)
                .onSubmit {
                    if let best = symbols.first { copy(best.name) }
                }

            if !query.isEmpty {
                if let latency = classifier.latencyMilliseconds {
                    Text(latency < 10 ? String(format: "%.1f ms", latency) : String(format: "%.0f ms", latency))
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                }
                Button {
                    query = ""
                    searchFocused = true
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 18))
                }
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
                .keyboardShortcut(.cancelAction)
                .accessibilityLabel("Clear search")
            }
        }
        .padding(.horizontal, 22)
        .frame(height: 62)
        .glassSurface(Capsule(), interactive: true)
    }

    private var suggestions: some View {
        FlowLayout(spacing: 8) {
            Text("Try")
                .font(.callout)
                .foregroundStyle(.secondary)
            ForEach(examples, id: \.self) { example in
                Button(example) {
                    query = example
                    searchFocused = true
                }
                .buttonStyle(PromptChipStyle())
            }
        }
    }

    // MARK: Results

    @ViewBuilder
    private var resultsSection: some View {
        switch classifier.state {
        case .failed(let message):
            ContentUnavailableView("Model unavailable", systemImage: "exclamationmark.triangle", description: Text(message))
                .frame(maxWidth: .infinity, minHeight: 260)
        case .loading where symbols.isEmpty:
            ContentUnavailableView("Loading classifier", systemImage: "arrow.triangle.2.circlepath", description: Text("The 2.7 MB model is loading locally."))
                .frame(maxWidth: .infinity, minHeight: 260)
        default:
            if query.isEmpty {
                ContentUnavailableView("Ready when you are", systemImage: "text.cursor", description: Text("Start typing, or pick one of the prompts above."))
                    .frame(maxWidth: .infinity, minHeight: 220)
            } else if symbols.isEmpty {
                ContentUnavailableView.search(text: query)
                    .frame(maxWidth: .infinity, minHeight: 260)
            } else {
                matches
            }
        }
    }

    private var matches: some View {
        VStack(alignment: .leading, spacing: 22) {
            if let best = symbols.first {
                BestMatchCard(name: best.name, copied: copiedName == best.name) { copy(best.name) }
            }

            if symbols.count > 1 {
                HStack(alignment: .firstTextBaseline) {
                    Text("More matches")
                        .font(.headline)
                    Text("\(symbols.count - 1)")
                        .font(.subheadline.monospacedDigit())
                        .foregroundStyle(.secondary)
                    Spacer()
                    Text("Double-click to copy")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }

                LazyVGrid(columns: columns, spacing: 18) {
                    ForEach(symbols.dropFirst()) { recommendation in
                        SymbolTile(name: recommendation.name, isSelected: selection == recommendation.name)
                            .onTapGesture(count: 2) { copy(recommendation.name) }
                            .onTapGesture { selection = recommendation.name }
                            .contextMenu {
                                Button("Copy Name") { copy(recommendation.name) }
                            }
                    }
                }
            }
        }
    }

    // MARK: Chrome

    private var backdrop: some View {
        Color(nsColor: .windowBackgroundColor)
            .ignoresSafeArea()
    }

    @ViewBuilder
    private var copiedToast: some View {
        if let copiedName {
            Label {
                Text("Copied ") + Text(copiedName).font(.body.monospaced())
            } icon: {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(.blue)
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 11)
            .glassSurface(Capsule())
            .padding(.bottom, 24)
            .transition(.move(edge: .bottom).combined(with: .opacity))
        }
    }

    private func copy(_ name: String) {
        selection = name
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(name, forType: .string)
        copiedName = name
        Task {
            try? await Task.sleep(for: .seconds(1.6))
            if copiedName == name { copiedName = nil }
        }
    }
}

private struct BestMatchCard: View {
    let name: String
    let copied: Bool
    let onCopy: () -> Void

    var body: some View {
        HStack(spacing: 18) {
            Image(systemName: name)
                .font(.system(size: 38, weight: .medium))
                .symbolRenderingMode(.hierarchical)
                .foregroundStyle(.primary)
                .frame(width: 78, height: 78)
                .background(.primary.opacity(0.06), in: RoundedRectangle(cornerRadius: 20, style: .continuous))

            VStack(alignment: .leading, spacing: 6) {
                Text("BEST MATCH")
                    .font(.caption2.weight(.bold))
                    .tracking(1)
                    .foregroundStyle(.secondary)
                Text(name)
                    .font(.title2.monospaced().weight(.semibold))
                    .lineLimit(1)
                    .truncationMode(.middle)
                    .textSelection(.enabled)
                Text("Press Return to copy")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Spacer(minLength: 12)

            Button(action: onCopy) {
                Label(copied ? "Copied" : "Copy Name", systemImage: copied ? "checkmark" : "doc.on.doc")
            }
            .glassButton(prominent: true)
            .tint(.blue)
            .controlSize(.large)
        }
        .padding(18)
        .glassSurface(RoundedRectangle(cornerRadius: 26, style: .continuous))
    }
}

private struct SymbolTile: View {
    let name: String
    let isSelected: Bool

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: name)
                .font(.system(size: 30, weight: .regular))
                .foregroundStyle(isSelected ? Color.white : Color.primary)
                .frame(maxWidth: .infinity)
                .frame(height: 76)
                .background(
                    isSelected ? AnyShapeStyle(Color.blue) : AnyShapeStyle(Color(nsColor: .controlBackgroundColor)),
                    in: RoundedRectangle(cornerRadius: 16, style: .continuous)
                )
                .overlay {
                    RoundedRectangle(cornerRadius: 16, style: .continuous)
                        .strokeBorder(.separator.opacity(isSelected ? 0 : 0.6))
                }

            // Zero-width spaces after dots let names wrap at segment boundaries, as in SF Symbols.
            Text(name.replacingOccurrences(of: ".", with: ".\u{200B}"))
                .font(.system(size: 11))
                .multilineTextAlignment(.center)
                .lineLimit(2)
                .foregroundStyle(isSelected ? Color.blue : Color.primary)
                .frame(maxWidth: .infinity, alignment: .top)
        }
        .contentShape(Rectangle())
        .help(name)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(Text(name))
        .accessibilityAddTraits(isSelected ? [.isButton, .isSelected] : .isButton)
    }
}

/// Flat, shadowless capsule for example prompts.
private struct PromptChipStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.callout)
            .foregroundStyle(.primary)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(.primary.opacity(configuration.isPressed ? 0.14 : 0.07), in: Capsule())
            .contentShape(Capsule())
    }
}

/// Lays children out left to right, wrapping onto new rows when the width runs out.
private struct FlowLayout: Layout {
    var spacing: CGFloat = 8

    func sizeThatFits(proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) -> CGSize {
        let rows = arrange(subviews: subviews, width: proposal.width ?? .infinity)
        let width = rows.map(\.width).max() ?? 0
        let height = rows.reduce(0) { $0 + $1.height } + spacing * CGFloat(max(rows.count - 1, 0))
        return CGSize(width: width, height: height)
    }

    func placeSubviews(in bounds: CGRect, proposal: ProposedViewSize, subviews: Subviews, cache: inout ()) {
        var y = bounds.minY
        for row in arrange(subviews: subviews, width: bounds.width) {
            var x = bounds.minX
            for index in row.indices {
                let size = subviews[index].sizeThatFits(.unspecified)
                subviews[index].place(at: CGPoint(x: x, y: y + (row.height - size.height) / 2), proposal: .unspecified)
                x += size.width + spacing
            }
            y += row.height + spacing
        }
    }

    private func arrange(subviews: Subviews, width: CGFloat) -> [(indices: [Int], width: CGFloat, height: CGFloat)] {
        var rows: [(indices: [Int], width: CGFloat, height: CGFloat)] = []
        var current: (indices: [Int], width: CGFloat, height: CGFloat) = ([], 0, 0)
        for index in subviews.indices {
            let size = subviews[index].sizeThatFits(.unspecified)
            let proposedWidth = current.indices.isEmpty ? size.width : current.width + spacing + size.width
            if proposedWidth > width, !current.indices.isEmpty {
                rows.append(current)
                current = ([index], size.width, size.height)
            } else {
                current = (current.indices + [index], proposedWidth, max(current.height, size.height))
            }
        }
        if !current.indices.isEmpty { rows.append(current) }
        return rows
    }
}

private struct StatusPill: View {
    let state: ClassifierState

    var body: some View {
        HStack(spacing: 7) {
            Circle()
                .fill(color)
                .frame(width: 7, height: 7)
            Text(state.label)
        }
        .font(.caption)
        .foregroundStyle(.secondary)
        .padding(.horizontal, 12)
        .padding(.vertical, 7)
        .glassSurface(Capsule())
    }

    private var color: Color {
        switch state {
        case .ready: .blue
        case .loading: .gray
        case .failed: .red
        }
    }
}
