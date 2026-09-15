#!/usr/bin/env python3
"""Select the best size-compliant candidate using validation top-1 only."""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("artifacts/candidates-v1"))
    parser.add_argument("--out", type=Path, default=Path("artifacts/model-v1"))
    args = parser.parse_args()
    candidates = []
    for metrics_path in sorted(args.root.glob("*/metrics.json")):
        metrics = json.loads(metrics_path.read_text())
        candidates.append({"name": metrics_path.parent.name, "path": metrics_path.parent, "metrics": metrics})
    eligible = [candidate for candidate in candidates if candidate["metrics"]["size_gate_pass"]]
    if not eligible:
        raise RuntimeError("no candidate passed the 5 MB projected export gate")
    # The test split is never used for selection.
    winner = max(eligible, key=lambda candidate: (candidate["metrics"]["val"]["top1"], -candidate["metrics"]["projected_full_int8_bytes"]))
    args.out.mkdir(parents=True, exist_ok=True)
    shutil.copy2(winner["path"] / "checkpoint.pt", args.out / "checkpoint.pt")
    report = {
        "selection_metric": "val/top1",
        "size_gate_bytes": 5_000_000,
        "winner": winner["name"],
        "candidates": [
            {
                "name": candidate["name"],
                "val_top1": candidate["metrics"]["val"]["top1"],
                "val_top5": candidate["metrics"]["val"]["top5"],
                "test_top1_sealed_until_selection": candidate["metrics"]["test"]["top1"],
                "test_top5_sealed_until_selection": candidate["metrics"]["test"]["top5"],
                "projected_int8_bytes": candidate["metrics"]["projected_full_int8_bytes"],
                "size_gate_pass": candidate["metrics"]["size_gate_pass"],
                "train_sec": candidate["metrics"]["train_sec"],
            }
            for candidate in candidates
        ],
    }
    (args.out / "selection.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps({
        "selection/winner_index": [candidate["name"] for candidate in candidates].index(winner["name"]),
        "selection/val_top1": winner["metrics"]["val"]["top1"],
        "selection/test_top1": winner["metrics"]["test"]["top1"],
        "selection/projected_int8_bytes": winner["metrics"]["projected_full_int8_bytes"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
