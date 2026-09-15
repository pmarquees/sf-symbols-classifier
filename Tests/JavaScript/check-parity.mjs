import fs from "node:fs";
import { fileURLToPath } from "node:url";
import { SFSymbolsClassifier } from "../../JavaScript/sf-symbols-classifier.mjs";

const [modelArgument, fixtureArgument] = process.argv.slice(2);
const modelPath = modelArgument ?? fileURLToPath(
  new URL("../../JavaScript/model/sf-symbols-classifier.sfs1", import.meta.url)
);
const fixturePath = fixtureArgument ?? fileURLToPath(
  new URL("../SFSymbolsClassifierTests/Fixtures/parity-fixtures.json", import.meta.url)
);
const bytes = fs.readFileSync(modelPath);
const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
const classifier = new SFSymbolsClassifier(buffer);
const fixtures = JSON.parse(fs.readFileSync(fixturePath, "utf8"));
let checked = 0;
for (const fixture of fixtures) {
  const actual = classifier.predict(fixture.text, fixture.predictions.length);
  const expected = fixture.predictions.map((item) => item.symbol);
  const received = actual.map((item) => item.symbol);
  if (JSON.stringify(expected) !== JSON.stringify(received)) {
    throw new Error(`parity mismatch for ${JSON.stringify(fixture.text)}: ${received} != ${expected}`);
  }
  checked += 1;
}
console.log(JSON.stringify({ "parity/js_fixtures": checked, "parity/js_pass": 1 }));
