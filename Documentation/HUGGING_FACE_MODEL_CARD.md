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

The SDK source, tests, training scripts, and demos live on
[GitHub](https://github.com/pmarquees/sf-symbols-classifier).

The quantized `SFS1` model is **2,714,833 bytes**, below the project's 5 MB
weights limit. Both runtimes consume the same weights.

## What is in this repository

The release bundle is stored as a base64-armored tarball:

```text
sf-symbols-classifier-v1.tar.gz.b64
```

Decode and unpack it with Python 3:

```sh
python3 - <<'PY'
from pathlib import Path
import base64

source = Path("sf-symbols-classifier-v1.tar.gz.b64")
target = Path("sf-symbols-classifier-v1.tar.gz")
target.write_bytes(base64.b64decode(b"".join(source.read_bytes().split()), validate=True))
print(target)
PY

tar -xzf sf-symbols-classifier-v1.tar.gz
```

The decoded archive contains:

```text
sf-symbols-classifier.sfs1
runtime/swift/SFSymbolsClassifier.swift
runtime/js/sf-symbols-classifier.mjs
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

Import `runtime/js/sf-symbols-classifier.mjs` as an ES module and load the same
`.sfs1` weights. The runtime is dependency-free and works in modern browsers
and Node.js 18 or newer.

Browsers receive **symbol names**, not Apple glyph artwork. A web product needs
its own appropriately licensed icon renderer if it wants to display visual
icons. Apple platforms can render the returned names using their native system
APIs.

## Evaluation

| Gate | Result |
| --- | ---: |
| Frozen synthetic top-1 accuracy | 0.682516 |
| Frozen synthetic top-5 accuracy | 0.854479 |
| Python to Swift parity | 100 / 100 fixtures |
| Python to JavaScript parity | 100 / 100 fixtures |
| Label count | 9,524 |
| Model weights | 2,714,833 bytes |
| Weights limit | 5,000,000 bytes |

The validation and test prompts were generated deterministically from catalog
metadata. They were not collected from real users, so these scores are a
development benchmark rather than proof of production quality on natural
product copy. Evaluate the model on your own phrases before relying on it.

## Release identity

- Model format: `SFS1`
- Model SHA-256:
  `7be17744d7a795725322b722f9268d2c9152fcf564232406524d2afc713d6ca8`
- Decoded archive SHA-256:
  `c8a536737e45f8518c31dec47acfed1fa117599528e37a64b3302e37e57da1f3`
- Decoded archive size: 2,025,525 bytes
- Training and export compute spend: $0.219416875

## Limitations

- Training prompts are English-oriented and metadata-derived.
- Short or ambiguous phrases can map to several plausible symbols.
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
