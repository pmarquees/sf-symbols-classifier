import SwiftUI

@main
@MainActor
struct SFSymbolFinderDemoApp: App {
    @StateObject private var classifier = ClassifierService()

    var body: some Scene {
        WindowGroup {
            ContentView(classifier: classifier)
                .frame(minWidth: 640, minHeight: 560)
        }
        .defaultSize(width: 1100, height: 800)
        .windowResizability(.contentMinSize)
    }
}
