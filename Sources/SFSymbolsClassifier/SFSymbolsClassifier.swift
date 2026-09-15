import Foundation

public struct SFSymbolPrediction: Equatable {
    public let symbol: String
    public let score: Int64
}
public enum SFSymbolsClassifierError: Error {
    case truncatedModel
    case invalidMagic
    case unsupportedVersion(UInt32)
    case labelCountMismatch
}

public final class SFSymbolsClassifier {
    private let buckets: Int
    private let dimension: Int
    private let labels: [String]
    private let featureWeights: [Int8]
    private let classWeights: [Int8]

    public convenience init(url: URL) throws {
        try self.init(data: Data(contentsOf: url))
    }

    public init(data: Data) throws {
        let bytes = [UInt8](data)
        guard bytes.count >= 32 else { throw SFSymbolsClassifierError.truncatedModel }
        guard String(bytes: bytes[0..<4], encoding: .ascii) == "SFS1" else {
            throw SFSymbolsClassifierError.invalidMagic
        }
        func uint32(_ offset: Int) -> UInt32 {
            UInt32(bytes[offset])
                | (UInt32(bytes[offset + 1]) << 8)
                | (UInt32(bytes[offset + 2]) << 16)
                | (UInt32(bytes[offset + 3]) << 24)
        }
        let version = uint32(4)
        guard version == 1 else { throw SFSymbolsClassifierError.unsupportedVersion(version) }
        buckets = Int(uint32(8))
        dimension = Int(uint32(12))
        let labelCount = Int(uint32(16))
        let labelBytes = Int(uint32(28))
        let featureOffset = 32
        let featureLength = buckets * dimension
        let classOffset = featureOffset + featureLength
        let classLength = labelCount * dimension
        let labelsOffset = classOffset + classLength
        guard labelsOffset + labelBytes <= bytes.count else { throw SFSymbolsClassifierError.truncatedModel }
        featureWeights = bytes[featureOffset..<(featureOffset + featureLength)].map { Int8(bitPattern: $0) }
        classWeights = bytes[classOffset..<(classOffset + classLength)].map { Int8(bitPattern: $0) }
        let labelText = String(decoding: bytes[labelsOffset..<(labelsOffset + labelBytes)], as: UTF8.self)
        labels = labelText.split(separator: "\n").map(String.init)
        guard labels.count == labelCount else { throw SFSymbolsClassifierError.labelCountMismatch }
    }

    public func predict(_ text: String, topK: Int = 5) -> [SFSymbolPrediction] {
        var query = [Int32](repeating: 0, count: dimension)
        for id in Self.features(text, buckets: buckets) {
            let offset = id * dimension
            for d in 0..<dimension {
                query[d] += Int32(featureWeights[offset + d])
            }
        }
        var predictions = [SFSymbolPrediction]()
        predictions.reserveCapacity(labels.count)
        for label in labels.indices {
            let offset = label * dimension
            var score: Int64 = 0
            for d in 0..<dimension {
                score += Int64(query[d]) * Int64(classWeights[offset + d])
            }
            predictions.append(SFSymbolPrediction(symbol: labels[label], score: score))
        }
        predictions.sort { lhs, rhs in
            lhs.score == rhs.score ? lhs.symbol < rhs.symbol : lhs.score > rhs.score
        }
        return Array(predictions.prefix(max(1, topK)))
    }

    private static func normalize(_ text: String) -> [UInt8] {
        let decomposed = text.decomposedStringWithCompatibilityMapping.lowercased()
        var output = [UInt8]()
        var pendingSpace = false
        for scalar in decomposed.unicodeScalars {
            if CharacterSet.nonBaseCharacters.contains(scalar) { continue }
            let value = scalar.value
            let isAlphaNumeric = (48...57).contains(value) || (97...122).contains(value)
            if isAlphaNumeric {
                if pendingSpace && !output.isEmpty { output.append(32) }
                output.append(UInt8(value))
                pendingSpace = false
            } else {
                pendingSpace = true
            }
        }
        return output
    }

    private static func fnv1a<S: Sequence>(_ bytes: S) -> UInt32 where S.Element == UInt8 {
        var value: UInt32 = 2_166_136_261
        for byte in bytes {
            value ^= UInt32(byte)
            value = value &* 16_777_619
        }
        return value
    }

    private static func features(_ text: String, buckets: Int) -> [Int] {
        let normalized = normalize(text)
        let bordered = [UInt8(94)] + normalized + [UInt8(36)]
        var ids = [Int]()
        for width in 2...5 where bordered.count >= width {
            for start in 0...(bordered.count - width) {
                ids.append(Int(fnv1a(bordered[start..<(start + width)]) % UInt32(buckets)))
            }
        }
        for word in String(decoding: normalized, as: UTF8.self).split(separator: " ") {
            let token = Array("w:".utf8) + Array(word.utf8)
            ids.append(Int(fnv1a(token) % UInt32(buckets)))
        }
        if ids.isEmpty { ids.append(Int(fnv1a([UInt8(94)]) % UInt32(buckets))) }
        return ids
    }
}
