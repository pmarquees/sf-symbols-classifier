const MAGIC = "SFS1";

function normalizeText(text) {
  return text
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, " ")
    .trim()
    .replace(/ +/g, " ");
}
function fnv1a(bytes) {
  let value = 0x811c9dc5;
  for (const byte of bytes) {
    value ^= byte;
    value = Math.imul(value, 0x01000193) >>> 0;
  }
  return value >>> 0;
}

function features(text, buckets) {
  const normalized = normalizeText(text);
  const bytes = new TextEncoder().encode(`^${normalized}$`);
  const ids = [];
  for (let width = 2; width <= 5; width += 1) {
    for (let start = 0; start + width <= bytes.length; start += 1) {
      ids.push(fnv1a(bytes.subarray(start, start + width)) % buckets);
    }
  }
  for (const word of normalized.split(" ").filter(Boolean)) {
    ids.push(fnv1a(new TextEncoder().encode(`w:${word}`)) % buckets);
  }
  if (ids.length === 0) ids.push(fnv1a(new Uint8Array([94])) % buckets);
  return ids;
}

export class SFSymbolsClassifier {
  constructor(arrayBuffer) {
    this.buffer = arrayBuffer;
    const view = new DataView(arrayBuffer);
    const magic = String.fromCharCode(...new Uint8Array(arrayBuffer, 0, 4));
    if (magic !== MAGIC) throw new Error(`Invalid model magic: ${magic}`);
    this.version = view.getUint32(4, true);
    if (this.version !== 1) throw new Error(`Unsupported model version: ${this.version}`);
    this.buckets = view.getUint32(8, true);
    this.dimension = view.getUint32(12, true);
    this.labelCount = view.getUint32(16, true);
    this.featureScale = view.getFloat32(20, true);
    this.classScale = view.getFloat32(24, true);
    const labelsBytes = view.getUint32(28, true);
    const featureOffset = 32;
    const featureLength = this.buckets * this.dimension;
    const classOffset = featureOffset + featureLength;
    const classLength = this.labelCount * this.dimension;
    const labelsOffset = classOffset + classLength;
    this.featureWeights = new Int8Array(arrayBuffer, featureOffset, featureLength);
    this.classWeights = new Int8Array(arrayBuffer, classOffset, classLength);
    const decoded = new TextDecoder().decode(new Uint8Array(arrayBuffer, labelsOffset, labelsBytes));
    this.labels = decoded.trimEnd().split("\n");
    if (this.labels.length !== this.labelCount) throw new Error("Label count mismatch");
  }

  predict(text, topK = 5) {
    const query = new Int32Array(this.dimension);
    const ids = features(text, this.buckets);
    for (const id of ids) {
      const offset = id * this.dimension;
      for (let d = 0; d < this.dimension; d += 1) query[d] += this.featureWeights[offset + d];
    }
    const scores = new Array(this.labelCount);
    for (let label = 0; label < this.labelCount; label += 1) {
      let score = 0;
      const offset = label * this.dimension;
      for (let d = 0; d < this.dimension; d += 1) score += query[d] * this.classWeights[offset + d];
      scores[label] = { symbol: this.labels[label], score };
    }
    scores.sort((a, b) => b.score - a.score || a.symbol.localeCompare(b.symbol));
    return scores.slice(0, Math.max(1, topK));
  }
}
