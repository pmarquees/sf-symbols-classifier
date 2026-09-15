# Live browser demo

The demo runs the exported SFS1 classifier locally after every `input` event. It has no package or network dependencies.

Serve the repository root so the demo can fetch the model bundle and JavaScript module:

```sh
python3 -m http.server 8080
```

Open <http://localhost:8080/Examples/Web/>.

The browser loads `JavaScript/model/sf-symbols-classifier.sfs1` and initializes
`JavaScript/sf-symbols-classifier.mjs`. Text stays in the browser.

The web demo intentionally displays canonical SF Symbol names rather than drawing lookalike icons. A native Swift host can render the returned name with `Image(systemName:)`.
