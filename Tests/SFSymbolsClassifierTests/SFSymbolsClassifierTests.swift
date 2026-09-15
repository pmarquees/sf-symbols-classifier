import Foundation
import XCTest
@testable import SFSymbolsClassifier

final class SFSymbolsClassifierTests: XCTestCase {
    func testFrozenParityFixtures() throws {
        let classifier = try SFSymbolsClassifier(
            url: SFSymbolsClassifierResources.bundledModelURL
        )
        let fixtureURL = try XCTUnwrap(
            Bundle.module.url(
                forResource: "parity-fixtures",
                withExtension: "json",
                subdirectory: "Fixtures"
            )
        )
        let fixtures = try JSONDecoder().decode(
            [Fixture].self,
            from: Data(contentsOf: fixtureURL)
        )

        XCTAssertEqual(fixtures.count, 100)

        for fixture in fixtures {
            let expected = fixture.predictions.map(\.symbol)
            let actual = classifier
                .predict(fixture.text, topK: expected.count)
                .map(\.symbol)
            XCTAssertEqual(actual, expected, "Parity mismatch for \(fixture.text)")
        }
    }
}

private struct Fixture: Decodable {
    let text: String
    let predictions: [Prediction]
}

private struct Prediction: Decodable {
    let symbol: String
}
