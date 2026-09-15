# Native SF Symbol Finder

This macOS SwiftUI demo uses the repository's Swift package directly. It ranks
names with the bundled SFS1 model and renders the results with
`Image(systemName:)` and `NSImage(systemSymbolName:)`, so the previews come
from the copy of SF Symbols installed with macOS.

From the repository root:

```sh
sh scripts/build-macos-demo.sh --verify
```

The script builds the nested SwiftPM package, stages
`dist/SFSymbolFinderDemo.app`, launches it, and verifies the process. The demo
targets macOS 14 or newer. Prompts never leave the Mac.
