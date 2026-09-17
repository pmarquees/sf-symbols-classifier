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
    from: "2.0.0"
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
npm install github:pmarquees/sf-symbols-classifier#v2.0.0
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
Evaluation/     Frozen v1 and v2 evaluation reports
Model/          Release manifest and checksums
scripts/        Dataset, training, export, and verification tools
Documentation/  Runtime notes and the Hugging Face model card
```

The model is duplicated inside the Swift and JavaScript packages so both are
independently installable and work offline. Both copies must have this SHA-256:

```text
44506fd4bf15a24af891ab16d6e594c1bb5a824c009c48f922abcbeaa0513b7a
```

Run the release identity check after changing either package:

```sh
python3 scripts/verify_release.py
```

## Demos

Build and open the native macOS demo:

```sh
./script/build_and_run.sh
```

Run the browser demo from the repository root:

```sh
python3 -m http.server 8080
```

Then open <http://localhost:8080/Examples/Web/>.

## Evaluation

The bundled model is v2. v1 figures are shown alongside for comparison.

| Gate | Result |
| --- | ---: |
| Synthetic metadata-derived top-1 | 66.91% (v1: 68.25%) |
| Synthetic metadata-derived top-5 | 85.20% (v1: 85.45%) |
| Natural-phrase regression, family top-1 | 85.0% (v1: 30.0%) |
| Python to Swift parity | 100 / 100 |
| Python to JavaScript parity | 100 / 100 |
| Model size | 2,714,833 bytes |

v2 trades a little synthetic accuracy for a large gain on natural phrasing.
The synthetic split is generated deterministically from catalog metadata and is
byte-identical across both releases, so the small top-1 drop is measured on the
same 38,235 rows. The natural-phrase gate is a frozen 40-row set of
hand-written prompts that is never trained on: v1 ranked the right symbol
family first for 30% of them, v2 for 85%, including the four reported misses
("Flight", "Start of the school year", "Vacation", "Trip to Germany").

Neither split is real user search traffic, so treat both as development
benchmarks rather than proof of product quality. Short, ambiguous prompts and
closely related symbol variants remain difficult.

Full reports live under `Evaluation/`.

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
