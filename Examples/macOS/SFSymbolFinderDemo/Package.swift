// swift-tools-version: 6.0

import PackageDescription

let package = Package(
    name: "SFSymbolFinderDemo",
    platforms: [.macOS(.v14)],
    dependencies: [
        .package(path: "../../.."),
    ],
    targets: [
        .executableTarget(
            name: "SFSymbolFinderDemo",
            dependencies: [
                .product(
                    name: "SFSymbolsClassifier",
                    package: "sf-symbols-classifier"
                ),
            ],
            path: ".",
            exclude: ["README.md"]
        ),
    ]
)
