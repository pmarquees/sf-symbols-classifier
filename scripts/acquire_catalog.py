#!/usr/bin/env python3
"""Download Apple's SF Symbols DMG and build a provenance-pinned metadata catalog."""

from __future__ import annotations

import argparse
import hashlib
import json
import plistlib
import re
import shutil
import subprocess
import sys
import urllib.request
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


DEFAULT_URL = "https://devimages-cdn.apple.com/design/resources/download/SF-Symbols-27.dmg?2="
PLIST_NAMES = {
    "name_availability.plist",
    "symbol_search.plist",
    "symbol_categories.plist",
    "categories.plist",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        return
    partial = destination.with_suffix(destination.suffix + ".partial")
    request = urllib.request.Request(url, headers={"User-Agent": "sf-symbols-classifier/1"})
    with urllib.request.urlopen(request, timeout=120) as response, partial.open("wb") as output:
        shutil.copyfileobj(response, output)
    partial.replace(destination)


def extract(archive: Path, destination: Path) -> None:
    marker = destination / ".complete-v2"
    if marker.exists():
        return
    if shutil.which("7z") is None:
        raise RuntimeError("7z is required to extract the Apple disk image")
    destination.mkdir(parents=True, exist_ok=True)
    subprocess.run(["7z", "x", "-y", f"-o{destination}", str(archive)], check=True)
    packages = sorted(destination.rglob("*.pkg"))
    if not packages:
        raise RuntimeError("Apple disk image did not contain an installer package")
    package_dir = destination / "package"
    subprocess.run(["7z", "x", "-y", f"-o{package_dir}", str(packages[0])], check=True)
    payloads = sorted(package_dir.rglob("Payload~")) + sorted(package_dir.rglob("Payload"))
    if not payloads:
        raise RuntimeError("Apple installer package did not contain a payload")
    payload_dir = destination / "payload"
    subprocess.run(["7z", "x", "-y", f"-o{payload_dir}", str(payloads[0])], check=True)
    marker.write_text("ok\n", encoding="utf-8")


def load_plist(path: Path) -> Any:
    with path.open("rb") as handle:
        return plistlib.load(handle)


def all_strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, child in value.items():
            if isinstance(key, str):
                yield key
            yield from all_strings(child)
    elif isinstance(value, (list, tuple, set)):
        for child in value:
            yield from all_strings(child)


def locate_metadata(root: Path) -> dict[str, Path]:
    candidates: dict[str, list[Path]] = defaultdict(list)
    for path in root.rglob("*.plist"):
        if path.name in PLIST_NAMES:
            candidates[path.name].append(path)
    selected: dict[str, Path] = {}
    for name, paths in candidates.items():
        # Prefer the SF Symbols app Metadata directory, then the shallowest match.
        paths.sort(key=lambda p: ("/Metadata/" not in str(p), len(p.parts), str(p)))
        selected[name] = paths[0]
    return selected


def symbol_names(availability: Any) -> set[str]:
    if isinstance(availability, dict):
        symbols = availability.get("symbols")
        if isinstance(symbols, dict):
            return {str(name) for name in symbols}
    return set()


def terms_by_symbol(payload: Any, names: set[str]) -> dict[str, set[str]]:
    """Recover either symbol -> terms or term -> symbols plist shapes."""
    result: dict[str, set[str]] = defaultdict(set)

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                key_text = str(key)
                strings = set(all_strings(child))
                if key_text in names:
                    result[key_text].update(text for text in strings if text not in names)
                else:
                    matched = strings & names
                    for name in matched:
                        result[name].add(key_text)
                walk(child)
        elif isinstance(value, (list, tuple)):
            for child in value:
                walk(child)

    walk(payload)
    return result


VARIANT_SUFFIXES = {
    "fill", "circle", "square", "rectangle", "slash", "badge", "rtl", "ltr",
    "portrait", "landscape", "horizontal", "vertical", "left", "right", "up", "down",
    "leading", "trailing", "top", "bottom", "inverse", "dashed", "solid", "half", "full",
}


def family_for(name: str) -> str:
    parts = name.split(".")
    while len(parts) > 1 and parts[-1] in VARIANT_SUFFIXES:
        parts.pop()
    return ".".join(parts)


def clean_terms(values: Iterable[str]) -> list[str]:
    cleaned = set()
    for value in values:
        text = re.sub(r"\s+", " ", value.strip().lower())
        if text and len(text) <= 100 and not re.fullmatch(r"[0-9._-]+", text):
            cleaned.add(text)
    return sorted(cleaned)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_URL)
    parser.add_argument("--out", type=Path, default=Path("artifacts/catalog-v1"))
    args = parser.parse_args()

    raw_dir = args.out / "raw"
    extracted_dir = raw_dir / "extracted"
    dmg = raw_dir / "SF-Symbols-27.dmg"
    download(args.url, dmg)
    extract(dmg, extracted_dir)

    paths = locate_metadata(extracted_dir)
    missing = sorted(PLIST_NAMES - set(paths))
    if "name_availability.plist" in missing:
        inventory = sorted(str(path.relative_to(extracted_dir)) for path in extracted_dir.rglob("*.plist"))
        (args.out / "plist_inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
        raise RuntimeError(f"missing required metadata; found {len(inventory)} plists: {missing}")

    loaded = {name: load_plist(path) for name, path in paths.items()}
    names = symbol_names(loaded["name_availability.plist"])
    if not names:
        raise RuntimeError("name_availability.plist did not contain a non-empty symbols dictionary")

    search = terms_by_symbol(loaded.get("symbol_search.plist", {}), names)
    categories = terms_by_symbol(loaded.get("symbol_categories.plist", {}), names)
    catalog_path = args.out / "catalog.jsonl"
    args.out.mkdir(parents=True, exist_ok=True)
    with catalog_path.open("w", encoding="utf-8") as output:
        for name in sorted(names):
            row = {
                "name": name,
                "family": family_for(name),
                "name_terms": name.replace(".", " ").split(),
                "search_terms": clean_terms(search.get(name, set())),
                "categories": clean_terms(categories.get(name, set())),
            }
            output.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    metadata_files = {
        name: {
            "path": str(path.relative_to(extracted_dir)),
            "sha256": sha256(path),
        }
        for name, path in sorted(paths.items())
    }
    manifest = {
        "schema_version": 1,
        "source_url": args.url,
        "source_sha256": sha256(dmg),
        "source_bytes": dmg.stat().st_size,
        "symbol_count": len(names),
        "catalog_sha256": sha256(catalog_path),
        "metadata_files": metadata_files,
        "missing_optional_metadata": [name for name in missing if name != "name_availability.plist"],
    }
    manifest_path = args.out / "catalog.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"metric": "data/symbol_count", "value": len(names)}))
    print(json.dumps({"metric": "data/catalog_bytes", "value": catalog_path.stat().st_size}))
    print(json.dumps(manifest, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"catalog acquisition failed: {exc}", file=sys.stderr)
        raise
