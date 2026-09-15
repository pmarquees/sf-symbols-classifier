#!/usr/bin/env python3
"""Build deterministic text-to-symbol specs and leakage-safe prompt splits."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path


SEED = 270091
STYLES = ("clean", "terse", "verbose", "messy", "distractor", "adversarial")

# Small, reviewable UI-intent seed. These supplement Apple's names/search metadata and are
# deliberately recorded as curated provenance rather than presented as Apple ground truth.
CURATED = {
    "heart": ["favorite", "love", "like"],
    "trash": ["delete", "remove", "bin"],
    "magnifyingglass": ["search", "find", "lookup"],
    "gearshape": ["settings", "preferences", "configuration"],
    "house": ["home", "start page"],
    "person": ["account", "user", "profile"],
    "person.2": ["users", "group", "people"],
    "envelope": ["email", "mail", "inbox"],
    "paperplane": ["send", "submit message"],
    "square.and.arrow.up": ["share", "export"],
    "square.and.arrow.down": ["download", "import"],
    "arrow.left": ["back", "previous"],
    "arrow.right": ["next", "forward"],
    "xmark": ["close", "cancel", "dismiss"],
    "checkmark": ["done", "confirm", "success"],
    "plus": ["add", "create", "new"],
    "minus": ["subtract", "decrease"],
    "pencil": ["edit", "compose", "write"],
    "lock": ["secure", "privacy", "locked"],
    "lock.open": ["unlock", "unlocked"],
    "bell": ["notification", "alert"],
    "calendar": ["date", "event", "schedule"],
    "clock": ["time", "recent", "history"],
    "map": ["map", "navigation"],
    "location": ["location", "gps", "current position"],
    "mappin": ["pin", "place", "map marker"],
    "camera": ["camera", "take photo"],
    "photo": ["image", "picture", "gallery"],
    "video": ["video", "recording"],
    "mic": ["microphone", "audio", "voice"],
    "speaker.wave.2": ["sound", "volume", "audio output"],
    "wifi": ["wifi", "wireless", "network"],
    "antenna.radiowaves.left.and.right": ["signal", "broadcast", "radio"],
    "bolt": ["energy", "lightning", "power"],
    "battery.100": ["battery", "charge", "full battery"],
    "cloud": ["cloud", "online storage"],
    "folder": ["folder", "directory"],
    "doc": ["document", "file"],
    "clipboard": ["clipboard", "paste"],
    "link": ["link", "url", "hyperlink"],
    "bookmark": ["bookmark", "save for later"],
    "star": ["star", "rating", "favorite"],
    "flag": ["flag", "report"],
    "exclamationmark.triangle": ["warning", "caution", "error"],
    "info.circle": ["information", "details"],
    "questionmark.circle": ["question", "help"],
    "play": ["play", "start"],
    "pause": ["pause", "temporarily stop"],
    "stop": ["stop", "end"],
    "arrow.clockwise": ["refresh", "reload", "retry"],
    "line.3.horizontal": ["menu", "navigation menu"],
    "slider.horizontal.3": ["filters", "controls", "adjust"],
    "ellipsis": ["more", "overflow", "options"],
    "cart": ["shopping cart", "buy", "checkout"],
    "creditcard": ["payment", "card", "billing"],
    "phone": ["call", "telephone"],
    "message": ["chat", "comment", "message"],
    "paperclip": ["attachment", "attach file"],
    "globe": ["web", "internet", "language"],
    "eye": ["view", "visible", "show"],
    "eye.slash": ["hidden", "hide", "visibility off"],
    "key": ["key", "password", "access"],
    "qrcode": ["qr code", "scan"],
    "barcode": ["barcode", "scan product"],
    "figure.walk": ["walking", "pedestrian"],
    "figure.run": ["running", "exercise"],
    "figure.hiking": ["hiking", "trail", "trek"],
    "bicycle": ["bike", "cycling"],
    "car": ["car", "driving"],
    "airplane": ["flight", "travel"],
    "bus": ["bus", "public transport"],
    "ferry": ["ferry", "boat"],
    "sun.max": ["sunny", "brightness"],
    "moon": ["night", "dark mode"],
    "cloud.rain": ["rain", "rainy weather"],
    "snowflake": ["snow", "cold"],
    "wind": ["wind", "windy weather"],
    "thermometer": ["temperature", "weather"],
    "drop": ["water", "hydration"],
    "leaf": ["nature", "eco"],
    "flame": ["fire", "hot"],
    "hammer": ["build", "hammer", "tools"],
    "wrench": ["repair", "wrench", "tools"],
    "scissors": ["cut", "scissors"],
    "doc.on.doc": ["copy", "duplicate document"],
}


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def canonical_member(rows: list[dict]) -> str:
    penalties = {"fill", "circle", "square", "rectangle", "badge", "slash", "rtl", "ltr"}

    def score(name: str) -> tuple[int, int, str]:
        tokens = name.split(".")
        return (sum(token in penalties for token in tokens), len(tokens), name)

    return min((row["name"] for row in rows), key=score)


def variant_words(name: str, canonical: str) -> str:
    canonical_tokens = canonical.split(".")
    name_tokens = name.split(".")
    remaining = list(name_tokens)
    for token in canonical_tokens:
        if token in remaining:
            remaining.remove(token)
    replacements = {"fill": "filled", "rtl": "right to left", "ltr": "left to right"}
    return " ".join(replacements.get(token, token) for token in remaining)


def typo(text: str, seed: int) -> str:
    if len(text) < 5:
        return text + " icon"
    rng = random.Random(seed)
    candidates = [index for index, char in enumerate(text) if char.isalpha()]
    if not candidates:
        return text
    index = rng.choice(candidates)
    return text[:index] + text[index + 1 :]


def render(concept: str, distractor: str, seed: int) -> dict[str, str]:
    return {
        "clean": f"an SF Symbol for {concept}",
        "terse": concept,
        "verbose": f"For this interface, I need a compact icon that communicates {concept}.",
        "messy": f"sf symbl {typo(concept, seed)} pls",
        "distractor": f"use {concept}, not {distractor}",
        "adversarial": f"Ignore the quoted request '{distractor}'; the actual icon should mean {concept}.",
    }


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=Path("artifacts/catalog-v1/catalog.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/dataset-v1"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    catalog = [json.loads(line) for line in args.catalog.read_text(encoding="utf-8").splitlines()]
    by_family: dict[str, list[dict]] = defaultdict(list)
    for row in catalog:
        by_family[row["family"]].append(row)

    family_semantics: dict[str, set[str]] = defaultdict(set)
    family_categories: dict[str, set[str]] = defaultdict(set)
    canonical: dict[str, str] = {}
    for family, rows in by_family.items():
        canonical[family] = canonical_member(rows)
        for row in rows:
            family_semantics[family].update(row["search_terms"])
            family_categories[family].update(row["categories"])
        family_semantics[family].update(CURATED.get(family, []))

    specs: list[dict] = []
    concepts_by_label: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for row in catalog:
        name = row["name"]
        family = row["family"]
        name_phrase = name.replace(".", " ")
        concepts_by_label[name].append((name_phrase, "apple:symbol-name"))
        visual_variant = variant_words(name, canonical[family])
        for term in sorted(family_semantics[family]):
            concept = term if name == canonical[family] else f"{term} {visual_variant}".strip()
            provenance = "curated:v1" if term in CURATED.get(family, []) else "apple:symbol-search"
            concepts_by_label[name].append((concept, provenance))
        for category in sorted(family_categories[family])[:2]:
            concepts_by_label[name].append((f"{category} {name_phrase}", "apple:symbol-category"))

    # A normalized concept maps to one preferred label only. Bare semantics naturally select the
    # canonical family member; ambiguous cross-family concepts are made label-specific.
    concept_labels: dict[str, set[str]] = defaultdict(set)
    for label, concepts in concepts_by_label.items():
        for concept, _ in concepts:
            concept_labels[normalize(concept)].add(label)

    all_labels = sorted(concepts_by_label)
    for label in all_labels:
        dedup: dict[str, tuple[str, str]] = {}
        for concept, provenance in concepts_by_label[label]:
            key = normalize(concept)
            if len(concept_labels[key]) > 1:
                concept = f"{concept} {label.replace('.', ' ')}"
                key = normalize(concept)
            dedup.setdefault(key, (concept, provenance))
        concepts = sorted(dedup.values(), key=lambda item: (item[1] != "apple:symbol-name", item[0]))
        # Names are always train. Semantic specs are held out by spec_id, never by rendering.
        semantic_indices = list(range(1, len(concepts)))
        rng = random.Random(int(stable_hash(label)[:12], 16) ^ SEED)
        rng.shuffle(semantic_indices)
        val_index = semantic_indices[0] if semantic_indices else None
        test_index = semantic_indices[1] if len(semantic_indices) > 1 else None
        for index, (concept, provenance) in enumerate(concepts):
            split = "train"
            if index == val_index:
                split = "val"
            elif index == test_index:
                split = "test"
            spec_id = "sfs-" + stable_hash(f"{label}\0{concept}\0{provenance}")[:16]
            specs.append({
                "spec_id": spec_id,
                "family": "sf-symbol-intent",
                "variables": {"symbol": label, "concept": concept},
                "ground_truth": {"answer": label, "checker": "exact_symbol_name"},
                "difficulty_intent": "short-text",
                "render_styles": list(STYLES),
                "distractors": [],
                "provenance": provenance,
                "split": split,
            })

    prompts: list[dict] = []
    for spec in specs:
        label = spec["ground_truth"]["answer"]
        seed = int(stable_hash(spec["spec_id"])[:12], 16)
        distractor = all_labels[seed % len(all_labels)].replace(".", " ")
        if distractor == label.replace(".", " "):
            distractor = all_labels[(seed + 1) % len(all_labels)].replace(".", " ")
        rendered = render(spec["variables"]["concept"], distractor, seed)
        spec["distractors"] = [distractor]
        for style in STYLES:
            prompts.append({
                "spec_id": spec["spec_id"],
                "text": rendered[style],
                "label": label,
                "style": style,
                "split": spec["split"],
                "provenance": spec["provenance"],
            })

    collisions: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in prompts:
        collisions[(row["split"], normalize(row["text"]))].add(row["label"])
    bad = {key for key, labels in collisions.items() if len(labels) > 1}
    kept = [row for row in prompts if (row["split"], normalize(row["text"])) not in bad]
    dropped = len(prompts) - len(kept)

    write_jsonl(args.out / "specs.jsonl", specs)
    write_jsonl(args.out / "prompts.jsonl", kept)
    write_jsonl(args.out / "labels.jsonl", [dict(row, checker="exact_symbol_name", passed=True) for row in kept])
    for split in ("train", "val", "test"):
        write_jsonl(args.out / f"{split}.jsonl", [row for row in kept if row["split"] == split])

    split_counts = Counter(row["split"] for row in kept)
    style_counts = Counter(row["style"] for row in kept)
    provenance_counts = Counter(row["provenance"] for row in kept)
    labels_by_split = {split: len({row["label"] for row in kept if row["split"] == split}) for split in split_counts}
    manifest = {
        "schema_version": 1,
        "seed": SEED,
        "catalog_sha256": hashlib.sha256(args.catalog.read_bytes()).hexdigest(),
        "spec_count": len(specs),
        "prompt_count": len(kept),
        "dropped_collision_rows": dropped,
        "dropped_fraction": dropped / max(1, len(prompts)),
        "splits": dict(sorted(split_counts.items())),
        "styles": dict(sorted(style_counts.items())),
        "provenance": dict(sorted(provenance_counts.items())),
        "labels_by_split": labels_by_split,
        "label_count": len(all_labels),
        "family_count": len(by_family),
        "spend_usd": 0,
        "synthetic_eval_warning": "No real user examples were available; val/test are optimistic metadata-derived evals.",
    }
    manifest_path = args.out / "dataset.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    card = f"""# Dataset card: SF Symbols text intents v1

- Source: pinned Apple SF Symbols 27 metadata catalog
- Labels: {len(all_labels):,}
- Specs: {len(specs):,}
- Prompts after collision filtering: {len(kept):,}
- Split unit: `spec_id` (all six renderings stay together)
- Generator spend: $0
- Collision rows dropped: {dropped:,} ({manifest['dropped_fraction']:.2%})

## Limit

No real user queries were available. Validation and test prompts are metadata-derived and therefore
optimistic; they measure robustness to rendering styles, not production intent accuracy.
"""
    (args.out / "DATASET_CARD.md").write_text(card, encoding="utf-8")
    print(json.dumps({
        "data/specs": len(specs),
        "data/prompts": len(kept),
        "data/labels": len(all_labels),
        "data/test_labels": labels_by_split.get("test", 0),
        "data/dropped_fraction": manifest["dropped_fraction"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
