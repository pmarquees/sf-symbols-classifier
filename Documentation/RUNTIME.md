# Portable runtime

`sf-symbols-classifier.sfs1` contains the int8 feature table, int8 class table, and all SF Symbol
names. Both runtimes implement the same ASCII-folding, FNV-1a hashed byte n-grams, and exact integer
ranking.

JavaScript: construct `SFSymbolsClassifier` with an `ArrayBuffer`, then call `predict(text, topK)`.

Swift: construct `SFSymbolsClassifier(data:)` or `SFSymbolsClassifier(url:)`, then call
`predict(_:topK:)`.

The returned score is an integer ranking score, not a calibrated probability.
