import Foundation

struct SymbolRecommendation: Identifiable, Equatable, Sendable {
    let rank: Int
    let name: String
    let score: Double?

    var id: String { "\(rank)-\(name)" }
}

enum ClassifierState: Equatable {
    case loading(String)
    case ready
    case failed(String)

    var label: String {
        switch self {
        case .loading(let detail): detail
        case .ready: "Model ready"
        case .failed: "Model unavailable"
        }
    }
}
