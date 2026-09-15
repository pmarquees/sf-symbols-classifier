#!/usr/bin/env python3
"""Train a compact hashed byte-ngram SF Symbols classifier."""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import time
import unicodedata
from collections import defaultdict
from pathlib import Path

import torch
import torch.nn.functional as F
from torch import nn


SEED = 270091


def normalize(text: str) -> str:
    result = []
    for char in unicodedata.normalize("NFKD", text).lower():
        if unicodedata.combining(char):
            continue
        result.append(char if char.isascii() and char.isalnum() else " ")
    return re.sub(r" +", " ", "".join(result)).strip()


def fnv1a(data: bytes) -> int:
    value = 2166136261
    for byte in data:
        value ^= byte
        value = (value * 16777619) & 0xFFFFFFFF
    return value


def features(text: str, buckets: int, min_n: int = 2, max_n: int = 5) -> list[int]:
    normalized = normalize(text)
    bordered = ("^" + normalized + "$").encode("ascii")
    result: list[int] = []
    for width in range(min_n, max_n + 1):
        for start in range(max(0, len(bordered) - width + 1)):
            result.append(fnv1a(bordered[start : start + width]) % buckets)
    for word in normalized.split():
        result.append(fnv1a(("w:" + word).encode("ascii")) % buckets)
    return result or [fnv1a(b"^") % buckets]


def load_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def prepare(rows: list[dict], label_to_id: dict[str, int], buckets: int) -> list[tuple[list[int], int]]:
    return [(features(row["text"], buckets), label_to_id[row["label"]]) for row in rows if row["label"] in label_to_id]


class CompactClassifier(nn.Module):
    def __init__(self, buckets: int, labels: int, dim: int) -> None:
        super().__init__()
        self.feature_embedding = nn.EmbeddingBag(buckets, dim, mode="mean", include_last_offset=True)
        self.classifier = nn.Linear(dim, labels, bias=False)
        nn.init.normal_(self.feature_embedding.weight, std=0.04)
        nn.init.normal_(self.classifier.weight, std=0.04)

    def forward(self, indices: torch.Tensor, offsets: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.feature_embedding(indices, offsets))


def batchify(examples: list[tuple[list[int], int]], indices: list[int], device: torch.device):
    flat: list[int] = []
    offsets = [0]
    labels: list[int] = []
    for index in indices:
        feats, label = examples[index]
        flat.extend(feats)
        offsets.append(len(flat))
        labels.append(label)
    return (
        torch.tensor(flat, dtype=torch.long, device=device),
        torch.tensor(offsets, dtype=torch.long, device=device),
        torch.tensor(labels, dtype=torch.long, device=device),
    )


@torch.inference_mode()
def evaluate(model: nn.Module, examples: list[tuple[list[int], int]], batch_size: int, device: torch.device) -> dict[str, float]:
    if not examples:
        return {"loss": float("nan"), "top1": float("nan"), "top5": float("nan")}
    model.eval()
    total_loss = 0.0
    top1 = 0
    top5 = 0
    count = 0
    for start in range(0, len(examples), batch_size):
        batch_indices = list(range(start, min(start + batch_size, len(examples))))
        ids, offsets, labels = batchify(examples, batch_indices, device)
        logits = model(ids, offsets)
        total_loss += F.cross_entropy(logits, labels, reduction="sum").item()
        predictions = logits.topk(min(5, logits.shape[1]), dim=1).indices
        top1 += (predictions[:, 0] == labels).sum().item()
        top5 += (predictions == labels[:, None]).any(dim=1).sum().item()
        count += len(batch_indices)
    return {"loss": total_loss / count, "top1": top1 / count, "top5": top5 / count}


def stratified_cap(rows: list[dict], labels: list[str], per_label: int, seed: int) -> list[dict]:
    allowed = set(labels)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        if row["label"] in allowed:
            grouped[row["label"]].append(row)
    rng = random.Random(seed)
    result = []
    for label in labels:
        candidates = grouped[label]
        rng.shuffle(candidates)
        result.extend(candidates[:per_label])
    rng.shuffle(result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path("artifacts/dataset-v1"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/model-v1"))
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--smoke-labels", type=int, default=128)
    parser.add_argument("--steps", type=int, default=120)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=256)
    parser.add_argument("--buckets", type=int, default=8192)
    parser.add_argument("--dim", type=int, default=64)
    parser.add_argument("--learning-rate", type=float, default=0.01)
    args = parser.parse_args()

    random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    device = torch.device("cuda")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA is required by this Project's execution contract")

    train_rows = load_rows(args.data / "train.jsonl")
    val_rows = load_rows(args.data / "val.jsonl")
    test_rows = load_rows(args.data / "test.jsonl")
    all_labels = sorted({row["label"] for row in train_rows})
    if args.smoke:
        eligible = sorted({row["label"] for row in val_rows} & set(all_labels))
        labels = eligible[: args.smoke_labels]
        train_rows = stratified_cap(train_rows, labels, per_label=12, seed=SEED)
        val_rows = stratified_cap(val_rows, labels, per_label=4, seed=SEED + 1)
        test_rows = []
    else:
        labels = all_labels
    label_to_id = {label: index for index, label in enumerate(labels)}

    started_preprocessing = time.perf_counter()
    train_examples = prepare(train_rows, label_to_id, args.buckets)
    val_examples = prepare(val_rows, label_to_id, args.buckets)
    test_examples = prepare(test_rows, label_to_id, args.buckets)
    preprocessing_sec = time.perf_counter() - started_preprocessing
    if not train_examples:
        raise RuntimeError("no training examples after label filtering")

    model = CompactClassifier(args.buckets, len(labels), args.dim).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    rng = random.Random(SEED)
    order = list(range(len(train_examples)))
    max_steps = args.steps if args.smoke else math.ceil(len(order) / args.batch_size) * args.epochs
    train_started = time.perf_counter()
    examples_seen = 0
    running_loss = 0.0
    running_correct = 0
    running_count = 0
    step = 0
    epoch = 0
    while step < max_steps:
        epoch += 1
        rng.shuffle(order)
        model.train()
        for start in range(0, len(order), args.batch_size):
            if step >= max_steps:
                break
            batch_indices = order[start : start + args.batch_size]
            ids, offsets, targets = batchify(train_examples, batch_indices, device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(ids, offsets)
            loss = F.cross_entropy(logits, targets)
            loss.backward()
            optimizer.step()
            with torch.no_grad():
                running_loss += loss.item() * len(batch_indices)
                running_correct += (logits.argmax(dim=1) == targets).sum().item()
                running_count += len(batch_indices)
                examples_seen += len(batch_indices)
            step += 1
            if step == 1 or step % 20 == 0 or step == max_steps:
                elapsed = time.perf_counter() - train_started
                print(json.dumps({
                    "step": step,
                    "train/loss": running_loss / max(1, running_count),
                    "train/top1": running_correct / max(1, running_count),
                    "train/examples_per_sec": examples_seen / max(elapsed, 1e-9),
                }, sort_keys=True), flush=True)
                running_loss = 0.0
                running_correct = 0
                running_count = 0

    torch.cuda.synchronize()
    train_sec = time.perf_counter() - train_started
    train_metrics = evaluate(model, train_examples, args.batch_size, device)
    val_metrics = evaluate(model, val_examples, args.batch_size, device)
    test_metrics = evaluate(model, test_examples, args.batch_size, device)
    label_bytes = sum(len(label.encode("utf-8")) + 1 for label in labels)
    projected_int8_bytes = (args.buckets + len(labels)) * args.dim + label_bytes + 64
    projected_full_bytes = (args.buckets + len(all_labels)) * args.dim + sum(len(x.encode("utf-8")) + 1 for x in all_labels) + 64

    args.out.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "schema_version": 1,
        "model_state": {key: value.detach().cpu() for key, value in model.state_dict().items()},
        "labels": labels,
        "config": {"buckets": args.buckets, "dim": args.dim, "seed": SEED},
    }
    checkpoint_path = args.out / "checkpoint.pt"
    torch.save(checkpoint, checkpoint_path)
    metrics = {
        "smoke": args.smoke,
        "labels": len(labels),
        "train_examples": len(train_examples),
        "val_examples": len(val_examples),
        "test_examples": len(test_examples),
        "steps": step,
        "epochs_completed": epoch,
        "preprocessing_sec": preprocessing_sec,
        "train_sec": train_sec,
        "examples_per_sec": examples_seen / max(train_sec, 1e-9),
        "train": train_metrics,
        "val": val_metrics,
        "test": test_metrics,
        "checkpoint_bytes": checkpoint_path.stat().st_size,
        "projected_int8_bytes": projected_int8_bytes,
        "projected_full_int8_bytes": projected_full_bytes,
        "size_gate_bytes": 5_000_000,
        "size_gate_pass": projected_full_bytes < 5_000_000,
        "cuda_device": torch.cuda.get_device_name(0),
    }
    (args.out / "metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "train/final_top1": train_metrics["top1"],
        "val/final_top1": val_metrics["top1"],
        "val/final_top5": val_metrics["top5"],
        "test/final_top1": test_metrics["top1"],
        "test/final_top5": test_metrics["top5"],
        "train/examples_per_sec": metrics["examples_per_sec"],
        "model/projected_full_int8_bytes": projected_full_bytes,
        "model/size_gate_pass": int(metrics["size_gate_pass"]),
    }, sort_keys=True), flush=True)
    if args.smoke and (train_metrics["top1"] < 0.90 or not metrics["size_gate_pass"]):
        raise RuntimeError(f"smoke gate failed: train_top1={train_metrics['top1']:.4f}, size={projected_full_bytes}")


if __name__ == "__main__":
    main()
