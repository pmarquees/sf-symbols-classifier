#!/usr/bin/env python3
"""Verify that both SDKs contain the immutable v1 model release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path


MODEL_SHA256 = "7be17744d7a795725322b722f9268d2c9152fcf564232406524d2afc713d6ca8"
MODEL_BYTES = 2_714_833
WEIGHTS_LIMIT_BYTES = 5_000_000


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    relative_paths = [
        Path("Sources/SFSymbolsClassifier/Resources/sf-symbols-classifier.sfs1"),
        Path("JavaScript/model/sf-symbols-classifier.sfs1"),
    ]

    for relative_path in relative_paths:
        model = root / relative_path
        if not model.is_file():
            raise RuntimeError(f"missing model: {relative_path}")
        if model.stat().st_size != MODEL_BYTES:
            raise RuntimeError(
                f"model size mismatch for {relative_path}: "
                f"expected {MODEL_BYTES}, got {model.stat().st_size}"
            )
        digest = sha256(model)
        if digest != MODEL_SHA256:
            raise RuntimeError(
                f"model checksum mismatch for {relative_path}: "
                f"expected {MODEL_SHA256}, got {digest}"
            )

    manifest_path = root / "Model/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("model_sha256") != MODEL_SHA256:
        raise RuntimeError("manifest model_sha256 does not match the v1 release")
    if manifest.get("model_bytes") != MODEL_BYTES:
        raise RuntimeError("manifest model_bytes does not match the v1 release")
    if manifest.get("model_paths") != [str(path) for path in relative_paths]:
        raise RuntimeError("manifest model_paths do not match the SDK layout")
    if MODEL_BYTES >= WEIGHTS_LIMIT_BYTES:
        raise RuntimeError("model exceeds the 5 MB weights gate")

    print(
        json.dumps(
            {
                "release/model_copies": len(relative_paths),
                "release/model_bytes": MODEL_BYTES,
                "release/model_sha256": MODEL_SHA256,
                "release/weights_limit_pass": 1,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
