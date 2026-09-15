import Foundation

/// Access to the immutable SFS1 weights bundled by Swift Package Manager.
public enum SFSymbolsClassifierResources {
    public static var bundledModelURL: URL {
        guard let url = Bundle.module.url(
            forResource: "sf-symbols-classifier",
            withExtension: "sfs1",
            subdirectory: "Resources"
        ) else {
            preconditionFailure("Bundled sf-symbols-classifier.sfs1 is missing")
        }
        return url
    }
}
