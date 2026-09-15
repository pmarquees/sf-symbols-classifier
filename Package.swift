// swift-tools-version: 5.9

import PackageDescription

let package = Package(
    name: "SFSymbolsClassifier",
    platforms: [
        .macOS(.v13),
        .iOS(.v16),
    ],
    products: [
        .library(
            name: "SFSymbolsClassifier",
            targets: ["SFSymbolsClassifier"]
        ),
    ],
    targets: [
        .target(
            name: "SFSymbolsClassifier",
            resources: [.copy("Resources")]
        ),
        .testTarget(
            name: "SFSymbolsClassifierTests",
            dependencies: ["SFSymbolsClassifier"],
            resources: [.copy("Fixtures")]
        ),
    ]
)
