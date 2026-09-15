#!/usr/bin/env python3
"""Quantize the selected checkpoint, evaluate it, and assemble portable runtimes."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from train import batchify, features, load_rows, normalize, prepare


HEADER = struct.Struct("<4sIIIIffI")
MAGIC = b"SFS1"


def quantize(tensor: torch.Tensor) -> tuple[np.ndarray, float]:
    array = tensor.detach().cpu().numpy().astype(np.float32)
    scale = float(np.max(np.abs(array)) / 127.0) if array.size else 1.0
    if scale == 0:
        scale = 1.0
    quantized = np.clip(np.rint(array / scale), -127, 127).astype(np.int8)
    return quantized, scale


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def topk_quantized(text: str, feature_q: np.ndarray, class_q: np.ndarray, labels: list[str], k: int = 5) -> list[dict]:
    ids = features(text, feature_q.shape[0])
    query = feature_q[ids].astype(np.int32).sum(axis=0)
    scores = class_q.astype(np.int32) @ query
    indices = np.argpartition(scores, -k)[-k:]
    indices = indices[np.argsort(-scores[indices], kind="stable")]
    return [{"symbol": labels[int(index)], "score": int(scores[index])} for index in indices]


def lexical_baseline(rows: list[dict], labels: list[str]) -> float:
    names: dict[str, str] = {}
    max_words = 1
    for label in labels:
        key = normalize(label.replace(".", " "))
        names.setdefault(key, label)
        max_words = max(max_words, len(key.split()))
    correct = 0
    for row in rows:
        words = normalize(row["text"]).split()
        matches = []
        for width in range(1, min(max_words, len(words)) + 1):
            for start in range(len(words) - width + 1):
                key = " ".join(words[start : start + width])
                if key in names:
                    matches.append((width, names[key]))
        prediction = max(matches, default=(0, ""), key=lambda item: (item[0], item[1]))[1]
        correct += prediction == row["label"]
    return correct / max(1, len(rows))


@torch.inference_mode()
def evaluate_quantized(rows: list[dict], labels: list[str], buckets: int, feature_q: np.ndarray, class_q: np.ndarray, batch_size: int) -> dict:
    label_to_id = {label: index for index, label in enumerate(labels)}
    examples = prepare(rows, label_to_id, buckets)
    device = torch.device("cuda")
    feature_weight = torch.from_numpy(feature_q.astype(np.float32)).to(device)
    class_weight = torch.from_numpy(class_q.astype(np.float32)).to(device)
    total = Counter()
    correct1 = Counter()
    correct5 = Counter()
    total_loss = 0.0
    for start in range(0, len(examples), batch_size):
        batch_indices = list(range(start, min(start + batch_size, len(examples))))
        ids, offsets, targets = batchify(examples, batch_indices, device)
        query = F.embedding_bag(ids, feature_weight, offsets, mode="mean", include_last_offset=True)
        logits = query @ class_weight.T
        total_loss += F.cross_entropy(logits, targets, reduction="sum").item()
        predictions = logits.topk(5, dim=1).indices
        top1 = (predictions[:, 0] == targets).cpu().tolist()
        top5 = (predictions == targets[:, None]).any(dim=1).cpu().tolist()
        for local_index, example_index in enumerate(batch_indices):
            row = rows[example_index]
            keys = ("overall", f"style:{row['style']}", f"provenance:{row['provenance']}")
            for key in keys:
                total[key] += 1
                correct1[key] += int(top1[local_index])
                correct5[key] += int(top5[local_index])
    return {
        "loss": total_loss / max(1, len(examples)),
        "top1": correct1["overall"] / max(1, total["overall"]),
        "top5": correct5["overall"] / max(1, total["overall"]),
        "by_style": {
            key.removeprefix("style:"): {"count": total[key], "top1": correct1[key] / total[key], "top5": correct5[key] / total[key]}
            for key in sorted(total) if key.startswith("style:")
        },
        "by_provenance": {
            key.removeprefix("provenance:"): {"count": total[key], "top1": correct1[key] / total[key], "top5": correct5[key] / total[key]}
            for key in sorted(total) if key.startswith("provenance:")
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, default=Path("artifacts/model-v1/checkpoint.pt"))
    parser.add_argument("--selection", type=Path, default=Path("artifacts/model-v1/selection.json"))
    parser.add_argument("--data", type=Path, default=Path("artifacts/dataset-v1"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/export-v1"))
    parser.add_argument("--runtime", type=Path, default=Path("runtime"))
    parser.add_argument("--batch-size", type=int, default=512)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    labels = checkpoint["labels"]
    config = checkpoint["config"]
    feature_q, feature_scale = quantize(checkpoint["model_state"]["feature_embedding.weight"])
    class_q, class_scale = quantize(checkpoint["model_state"]["classifier.weight"])
    labels_blob = ("\n".join(labels) + "\n").encode("utf-8")
    model_path = args.out / "sf-symbols-classifier.sfs1"
    with model_path.open("wb") as handle:
        handle.write(HEADER.pack(MAGIC, 1, config["buckets"], config["dim"], len(labels), feature_scale, class_scale, len(labels_blob)))
        handle.write(feature_q.tobytes(order="C"))
        handle.write(class_q.tobytes(order="C"))
        handle.write(labels_blob)

    selection = json.loads(args.selection.read_text())
    winner = next(candidate for candidate in selection["candidates"] if candidate["name"] == selection["winner"])
    test_rows = load_rows(args.data / "test.jsonl")
    quantized = evaluate_quantized(test_rows, labels, config["buckets"], feature_q, class_q, args.batch_size)
    baseline_top1 = lexical_baseline(test_rows, labels)

    curated_texts = [
        "favorite", "delete item", "go back", "hiking trail", "wireless network",
        "take a photo", "dark mode", "share this", "warning", "search",
    ]
    fixture_texts = curated_texts + [row["text"] for row in test_rows[:: max(1, len(test_rows) // 90)][:90]]
    fixtures = [{"text": text, "predictions": topk_quantized(text, feature_q, class_q, labels)} for text in fixture_texts]
    (args.out / "parity-fixtures.json").write_text(json.dumps(fixtures, indent=2, ensure_ascii=False) + "\n")
    shutil.copytree(args.runtime, args.out / "runtime", dirs_exist_ok=True)

    manifest = {
        "schema_version": 1,
        "format": "SFS1",
        "model_file": model_path.name,
        "model_bytes": model_path.stat().st_size,
        "model_sha256": sha256(model_path),
        "weights_limit_bytes": 5_000_000,
        "weights_limit_pass": model_path.stat().st_size < 5_000_000,
        "labels": len(labels),
        "buckets": config["buckets"],
        "dimension": config["dim"],
        "quantization": "symmetric int8 per tensor",
        "selected_by": selection["selection_metric"],
        "selected_candidate": selection["winner"],
        "float_test_top1": winner["test_top1_sealed_until_selection"],
        "float_test_top5": winner["test_top5_sealed_until_selection"],
        "quantized_test": quantized,
        "quantization_top1_delta": quantized["top1"] - winner["test_top1_sealed_until_selection"],
        "lexical_baseline_test_top1": baseline_top1,
        "evaluation_warning": "No real user examples were available; this test is metadata-derived and optimistic.",
    }
    manifest_path = args.out / "export.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "export/model_bytes": manifest["model_bytes"],
        "export/size_gate_pass": int(manifest["weights_limit_pass"]),
        "eval/quantized_top1": quantized["top1"],
        "eval/quantized_top5": quantized["top5"],
        "eval/quantization_top1_delta": manifest["quantization_top1_delta"],
        "eval/lexical_baseline_top1": baseline_top1,
    }, sort_keys=True))
    if not manifest["weights_limit_pass"]:
        raise RuntimeError(f"export exceeds 5 MB: {manifest['model_bytes']} bytes")
    if manifest["quantization_top1_delta"] < -0.01:
        raise RuntimeError(f"quantization loses more than 1 point top-1: {manifest['quantization_top1_delta']:.4f}")


if __name__ == "__main__":
    main()
