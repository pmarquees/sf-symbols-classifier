import Combine
import Foundation
import SFSymbolsClassifier

@MainActor
final class ClassifierService: ObservableObject {
    @Published private(set) var state: ClassifierState = .loading("Loading model")
    @Published private(set) var recommendations: [SymbolRecommendation] = []
    @Published private(set) var latencyMilliseconds: Double?

    private var classifier: SFSymbolsClassifier?
    private var generation = 0

    init() {
        do {
            classifier = try SFSymbolsClassifier(
                url: SFSymbolsClassifierResources.bundledModelURL
            )
            state = .ready
        } catch {
            state = .failed(error.localizedDescription)
        }
    }

    func predict(_ text: String) {
        generation += 1
        let requestGeneration = generation
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmed.isEmpty else {
            recommendations = []
            latencyMilliseconds = nil
            return
        }

        guard state == .ready, let classifier else { return }

        let started = ProcessInfo.processInfo.systemUptime
        let predictions = classifier.predict(trimmed, topK: 120)
        let elapsed = ProcessInfo.processInfo.systemUptime - started

        guard requestGeneration == generation else { return }
        recommendations = predictions.enumerated().map { index, prediction in
            SymbolRecommendation(
                rank: index + 1,
                name: prediction.symbol,
                score: Double(prediction.score)
            )
        }
        latencyMilliseconds = elapsed * 1_000
    }
}
