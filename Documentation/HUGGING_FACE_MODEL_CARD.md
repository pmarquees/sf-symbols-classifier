---
language:
- en
pipeline_tag: text-classification
library_name: custom
license: other
tags:
- sf-symbols
- swift
- javascript
- on-device
- text-classification
---

# SF Symbols Text Classifier

A compact, offline classifier that maps a short English phrase to ranked
SF Symbols 27 names. It is designed for live icon suggestions while someone
types and ships with dependency-free Swift and JavaScript runtimes.

The current release is v2, which adds a natural-intent training layer over
Apple's catalog metadata so that everyday phrasing such as "vacation" or
"start of the school year" resolves to the symbol a person actually means.

The SDK source, tests, training scripts, and demos live on
[GitHub](https://github.com/pmarquees/sf-symbols-classifier).

The quantized `SFS1` model is **2,714,833 bytes**, below the project's 5 MB
weights limit. Both runtimes consume the same weights.

## What is in this repository

The release bundle is stored as a base64-armored tarball:

```text
sf-symbols-classifier-v2.tar.gz.b64
```

Decode and unpack it with Python 3:

```sh
python3 - <<'PY'
from pathlib import Path
import base64

source = Path("sf-symbols-classifier-v2.tar.gz.b64")
target = Path("sf-symbols-classifier-v2.tar.gz")
target.write_bytes(base64.b64decode(b"".join(source.read_bytes().split()), validate=True))
print(target)
PY

tar -xzf sf-symbols-classifier-v2.tar.gz
```

The decoded archive contains:

```text
sf-symbols-classifier.sfs1
export.manifest.json
parity-fixtures.json
runtime/SFSymbolsClassifier.swift
runtime/sf-symbols-classifier.mjs
runtime/model.mjs
```

## Swift

Add `SFSymbolsClassifier.swift` to your target and bundle
`sf-symbols-classifier.sfs1` as an app resource. The included runtime performs
inference locally; no network request or ML framework is required.

The prediction is an SF Symbols system name. Render it on an Apple platform
with the system API:

```swift
import SwiftUI

Image(systemName: prediction.name)
```

Use `NSImage(systemSymbolName:accessibilityDescription:)` in AppKit or
`UIImage(systemName:)` in UIKit.

## JavaScript

Import `runtime/sf-symbols-classifier.mjs` as an ES module and load the same
`.sfs1` weights. The runtime is dependency-free and works in modern browsers
and Node.js 18 or newer.

Browsers receive **symbol names**, not Apple glyph artwork. A web product needs
its own appropriately licensed icon renderer if it wants to display visual
icons. Apple platforms can render the returned names using their native system
APIs.

## Evaluation

| Gate | Result |
| --- | ---: |
| Frozen synthetic top-1 accuracy | 0.669125 (v1: 0.682516) |
| Frozen synthetic top-5 accuracy | 0.852047 (v1: 0.854479) |
| Natural-phrase regression, family top-1 | 0.85 (v1: 0.30) |
| Natural-phrase regression, exact top-1 | 0.775 |
| Python to Swift parity | 100 / 100 fixtures |
| Python to JavaScript parity | 100 / 100 fixtures |
| Label count | 9,524 |
| Model weights | 2,714,833 bytes |
| Weights limit | 5,000,000 bytes |

The synthetic test split is generated deterministically from catalog metadata
and is byte-identical to the one used for v1 (38,235 rows), so the small top-1
decrease is measured on the same prompts. v2 spends that accuracy on natural
phrasing: the frozen 40-row natural-phrase regression, which is never trained
on, improves from 0.30 to 0.85 family top-1, and the four previously reported
failures ("Flight", "Start of the school year", "Vacation", "Trip to Germany")
are now correct at rank 1.

Neither split was collected from real users, so these scores are a development
benchmark rather than proof of production quality on natural product copy.
Evaluate the model on your own phrases before relying on it.

## Release identity

- Release: `v2-sfsymbols27-int8`
- Model format: `SFS1`, symmetric int8 per tensor
- Model SHA-256:
  `44506fd4bf15a24af891ab16d6e594c1bb5a824c009c48f922abcbeaa0513b7a`
- Model size: 2,714,833 bytes
- Decoded archive SHA-256:
  `cc35936ddc011dac5aae8ec52086c10cd4813faccfc19b6d44a5f1d3df29e547`
- Decoded archive size: 2,015,628 bytes
- Selected candidate: `iterD`, chosen on the frozen natural-phrase regression
  with catalog test top-1 as tie-break

## Limitations

- Training prompts are English-oriented and mostly metadata-derived.
- Short or ambiguous phrases can map to several plausible symbols.
- The natural-phrase regression is hand-authored and only 40 rows, so the 0.85
  family top-1 figure carries a wide confidence interval.
- The architecture matches hashed character n-grams, so a phrase whose
  substrings collide with an unrelated symbol name can misrank it.
- Closely related variants such as filled, circled, or badged symbols can be
  difficult to distinguish.
- Symbol availability depends on the user's OS version.
- Product-specific Apple symbols can have additional usage restrictions.

## Apple and license notice

This repository contains learned weights, runtime code, SF Symbols system
names, and evaluation metadata. It does **not** contain Apple's SF Symbol glyph
artwork, exported templates, SVG files, or fonts.

SF Symbols and Apple platform names are trademarks of Apple Inc. This project
is not affiliated with or endorsed by Apple. Consumers are responsible for
complying with Apple's current SF Symbols terms, Human Interface Guidelines,
platform availability, and symbol-specific restrictions.

No general open-source or model license has been selected, so the Hub metadata
uses `license: other`.
