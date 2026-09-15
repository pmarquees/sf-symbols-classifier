# SF Symbols Classifier

A 2.7 MB text classifier that turns a short English phrase into ranked SF
Symbols names. It runs fully offline and includes dependency-free Swift and
JavaScript runtimes.

[View the model on Hugging Face](https://huggingface.co/pmarquees/sf-symbols-classifier)

```text
"a rainy evening"       -> cloud.rain
"share my location"     -> location
"quiet alarm tomorrow"  -> alarm
```

The model covers 9,524 names from the SF Symbols 27 catalog. It returns symbol
names, not glyph artwork. Apple platforms can render the result with
`Image(systemName:)`, `UIImage(systemName:)`, or
`NSImage(systemSymbolName:accessibilityDescription:)`.

## Swift

Add the repository as a Swift Package dependency:

```swift
.package(
    url: "https://github.com/pmarquees/sf-symbols-classifier.git",
    from: "1.0.0"
)
```

Load the bundled model and ask for the best matches:

```swift
import SFSymbolsClassifier

let classifier = try SFSymbolsClassifier(
    url: SFSymbolsClassifierResources.bundledModelURL
)

let matches = classifier.predict("a place to go hiking", topK: 5)
print(matches.map(\.symbol))
```

The package supports macOS 13 and iOS 16 or newer.

## JavaScript

Until the package is published to npm, install it directly from GitHub:

```sh
npm install github:pmarquees/sf-symbols-classifier#v1.0.0
```

Load the bundled model in Node.js:

```js
import { readFile } from "node:fs/promises";
import { SFSymbolsClassifier } from "sf-symbols-text-classifier";
import { modelURL } from "sf-symbols-text-classifier/model";

const bytes = await readFile(modelURL);
const buffer = bytes.buffer.slice(
  bytes.byteOffset,
  bytes.byteOffset + bytes.byteLength
);

const classifier = new SFSymbolsClassifier(buffer);
console.log(classifier.predict("start a video call", 5));
```

The JavaScript package is ESM-only and supports Node.js 18 or newer. The same
runtime also works in modern browsers.

## Repository layout

```text
Sources/        Swift library and bundled model
JavaScript/     JavaScript runtime and bundled model
Examples/       Native macOS and browser demos
Tests/          Swift and JavaScript parity checks
Evaluation/     Frozen v1 evaluation report
Model/          Release manifest and checksums
scripts/        Dataset, training, export, and verification tools
Documentation/  Runtime notes and the Hugging Face model card
```

The model is duplicated inside the Swift and JavaScript packages so both are
independently installable and work offline. Both copies must have this SHA-256:

```text
7be17744d7a795725322b722f9268d2c9152fcf564232406524d2afc713d6ca8
```

Run the release identity check after changing either package:

```sh
python3 scripts/verify_release.py
```

## Demos

Build and open the native macOS demo:

```sh
sh scripts/build-macos-demo.sh
```

Run the browser demo from the repository root:

```sh
python3 -m http.server 8080
```

Then open <http://localhost:8080/Examples/Web/>.

## Evaluation

| Gate | Result |
| --- | ---: |
| Synthetic metadata-derived top-1 | 68.25% |
| Synthetic metadata-derived top-5 | 85.45% |
| Python to Swift parity | 100 / 100 |
| Python to JavaScript parity | 100 / 100 |
| Model size | 2,714,833 bytes |

These prompts were generated deterministically from catalog metadata. They are
not real user searches, so the scores are a development benchmark, not proof
of product quality. Short, ambiguous prompts and closely related symbol
variants remain difficult.

Run the shipped parity checks with:

```sh
swift test
npm test
```

## Training and export

The scripts used to acquire metadata, build the dataset, train candidates,
select the winner, and export SFS1 live under `scripts/`. Generated datasets,
checkpoints, and export artifacts stay under the ignored `artifacts/` folder.

The exported format stores int8 feature weights, int8 class weights, and the
symbol names in one file. Both runtimes use identical normalization, FNV-1a
hashed byte n-grams, and integer ranking.

## Model release

The canonical model release and its public history live on
[Hugging Face](https://huggingface.co/pmarquees/sf-symbols-classifier). This
GitHub repository is the canonical home for the SDK source, tests, demos, and
training code.

## Apple and licensing notice

This repository does not contain Apple glyph artwork, exported SF Symbols
templates, SVGs, or fonts. SF Symbols and Apple platform names are trademarks
of Apple Inc. This project is not affiliated with or endorsed by Apple.

No general open-source or model license has been selected yet. See
[NOTICE.md](NOTICE.md) before redistributing the code, learned weights, or
catalog-derived material.
