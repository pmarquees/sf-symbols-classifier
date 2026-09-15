import * as runtime from "../../JavaScript/sf-symbols-classifier.mjs";

const MODEL_URL = new URL("../../JavaScript/model/sf-symbols-classifier.sfs1", import.meta.url);
const TOP_K = 6;

const query = document.querySelector("#query");
const status = document.querySelector("#model-status");
const resultsRegion = document.querySelector(".results");
const resultsTitle = document.querySelector("#results-title");
const primary = document.querySelector("#primary-result");
const primaryName = document.querySelector("#primary-name");
const primaryCopy = document.querySelector("#primary-copy");
const resultList = document.querySelector("#result-list");
const resultTemplate = document.querySelector("#result-template");
const emptyMessage = document.querySelector("#empty-message");
const latency = document.querySelector("#latency");
const inputHint = document.querySelector("#input-hint");
const clearButton = document.querySelector("#clear-button");

let predict = null;
let inputVersion = 0;
let renderedVersion = 0;
let draining = false;
let currentBest = "";

boot().catch(showFatalError);

query.addEventListener("input", () => {
  inputVersion += 1;
  clearButton.hidden = query.value.length === 0;
  inputHint.textContent = query.value.length
    ? `${query.value.length} character${query.value.length === 1 ? "" : "s"} · running locally`
    : "Start typing to run the model";
  drainInputs();
});

clearButton.addEventListener("click", () => {
  query.value = "";
  query.dispatchEvent(new Event("input"));
  query.focus();
});

document.querySelectorAll("[data-example]").forEach((button) => {
  button.addEventListener("click", () => {
    query.value = button.dataset.example;
    query.dispatchEvent(new Event("input"));
    query.focus();
  });
});

primaryCopy.addEventListener("click", () => copyName(currentBest, primaryCopy));

async function boot() {
  const modelBytes = await loadModel(MODEL_URL);
  predict = await createPredictor(runtime, modelBytes);

  status.classList.add("ready");
  status.querySelector("span:last-child").textContent = "Model ready";
  resultsRegion.setAttribute("aria-busy", "false");
  primary.classList.remove("skeleton");
  resultsTitle.textContent = "Ready as you type";
  primaryName.textContent = "Describe an intent above";
  query.disabled = false;

  if (query.value.trim()) {
    inputVersion += 1;
    drainInputs();
  }
}

async function drainInputs() {
  if (!predict || draining) return;
  draining = true;

  while (renderedVersion < inputVersion) {
    const version = inputVersion;
    const text = query.value.trim();

    if (!text) {
      renderEmpty();
      renderedVersion = version;
      continue;
    }

    await new Promise(requestAnimationFrame);
    const started = performance.now();
    const raw = await predict(text, TOP_K);
    const recommendations = normalizeResults(raw).slice(0, TOP_K);
    const elapsed = performance.now() - started;

    if (version === inputVersion) {
      renderResults(text, recommendations, elapsed);
      renderedVersion = version;
    }
  }

  draining = false;
}

async function loadModel(url) {
  setStatus("Loading 2.7 MB weights");
  const response = await fetch(url);
  if (!response.ok) throw new Error(`Could not load the model (${response.status}).`);
  return new Uint8Array(await response.arrayBuffer());
}

async function createPredictor(module, bytes) {
  const buffer = bytes.buffer.slice(bytes.byteOffset, bytes.byteOffset + bytes.byteLength);
  const blobUrl = URL.createObjectURL(new Blob([bytes], { type: "application/octet-stream" }));
  const Type = module.SFSymbolsClassifier ?? module.Classifier ?? module.default;
  const factories = [
    () => module.loadSFS1?.(bytes),
    () => module.loadModel?.(bytes),
    () => Type?.fromBytes?.(bytes),
    () => Type?.fromArrayBuffer?.(buffer),
    () => Type?.load?.(blobUrl),
    () => (typeof Type === "function" ? new Type(bytes) : null),
    () => (typeof Type === "function" ? new Type(buffer) : null)
  ];

  let lastError;
  for (const make of factories) {
    try {
      const classifier = await make();
      if (!classifier) continue;
      const callable = findPredictionMethod(module, classifier);
      if (callable) {
        URL.revokeObjectURL(blobUrl);
        return callable;
      }
    } catch (error) {
      lastError = error;
    }
  }

  URL.revokeObjectURL(blobUrl);
  throw new Error(`The JavaScript runtime API could not be initialized${lastError ? `: ${lastError.message}` : "."}`);
}

function findPredictionMethod(module, classifier) {
  const methodNames = ["predict", "predictTopK", "classify", "rank", "recommend", "search"];

  for (const name of methodNames) {
    if (typeof classifier?.[name] === "function") {
      return async (text, topK) => classifier[name](text, topK);
    }
  }

  for (const name of methodNames) {
    if (typeof module[name] === "function") {
      return async (text, topK) => module[name](classifier, text, topK);
    }
  }

  return typeof classifier === "function" ? classifier : null;
}

function normalizeResults(raw) {
  const value = raw?.predictions ?? raw?.results ?? raw?.recommendations ?? raw?.topK ?? raw;

  if (Array.isArray(value)) {
    return value.map((item, index) => {
      if (typeof item === "string") return { name: item, score: null, rank: index + 1 };
      if (Array.isArray(item)) return { name: String(item[0]), score: finiteNumber(item[1]), rank: index + 1 };
      return {
        name: String(item?.name ?? item?.symbol ?? item?.label ?? item?.id ?? "Unknown symbol"),
        score: finiteNumber(item?.score ?? item?.logit ?? item?.confidence ?? item?.value),
        rank: index + 1
      };
    });
  }

  if (Array.isArray(value?.labels)) {
    return value.labels.map((name, index) => ({ name: String(name), score: finiteNumber(value.scores?.[index]), rank: index + 1 }));
  }

  throw new Error("The classifier returned an unsupported prediction shape.");
}

function finiteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function renderResults(text, recommendations, elapsed) {
  if (!recommendations.length) {
    renderEmpty();
    return;
  }

  const [best, ...more] = recommendations;
  currentBest = best.name;
  primaryName.textContent = best.name;
  primaryCopy.disabled = false;
  resultsTitle.textContent = `Best matches for “${truncate(text, 42)}”`;
  latency.textContent = `${elapsed.toFixed(elapsed < 10 ? 1 : 0)} ms`;
  emptyMessage.hidden = true;
  primary.hidden = false;
  resultList.replaceChildren();

  const widths = relativeWidths(recommendations);
  more.forEach((result, index) => {
    const row = resultTemplate.content.firstElementChild.cloneNode(true);
    row.querySelector(".result-rank").textContent = String(index + 2).padStart(2, "0");
    row.querySelector(".result-name").textContent = result.name;
    row.querySelector(".score-track span").style.setProperty("--score", `${widths[index + 1]}%`);
    const copy = row.querySelector(".row-copy");
    copy.setAttribute("aria-label", `Copy ${result.name}`);
    copy.addEventListener("click", () => copyName(result.name, copy));
    resultList.append(row);
  });
}

function relativeWidths(items) {
  const numeric = items.every((item) => item.score !== null);
  if (!numeric) return items.map((_, index) => Math.max(28, 100 - index * 13));
  const scores = items.map((item) => item.score);
  const low = Math.min(...scores);
  const high = Math.max(...scores);
  const spread = high - low || 1;
  return scores.map((score) => Math.round(28 + ((score - low) / spread) * 72));
}

function renderEmpty() {
  currentBest = "";
  resultsTitle.textContent = "Ready as you type";
  primaryName.textContent = "Describe an intent above";
  primaryCopy.disabled = true;
  primary.hidden = false;
  resultList.replaceChildren();
  latency.textContent = "";
  emptyMessage.hidden = true;
}

async function copyName(name, button) {
  if (!name) return;
  await navigator.clipboard.writeText(name);
  const old = button.textContent;
  button.textContent = "Copied";
  setTimeout(() => { button.textContent = old; }, 900);
}

function setStatus(message) {
  status.querySelector("span:last-child").textContent = message;
}

function showFatalError(error) {
  console.error(error);
  status.classList.add("error");
  setStatus("Model unavailable");
  resultsRegion.setAttribute("aria-busy", "false");
  primary.classList.remove("skeleton");
  primaryName.textContent = "Could not load the classifier";
  resultsTitle.textContent = "Setup needed";
  inputHint.textContent = error.message;
  query.disabled = true;
}

function truncate(text, maxLength) {
  return text.length <= maxLength ? text : `${text.slice(0, maxLength - 1)}…`;
}
