#!/usr/bin/env python3
"""Verify every official upstream snapshot against SHA256SUMS."""
from __future__ import annotations

import hashlib
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SUMS = ROOT / "upstream/provenance/SHA256SUMS"


def main() -> None:
    failures: list[str] = []
    for line in SUMS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(None, 1)
        relative = relative.strip()
        actual = hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()
        if actual != expected:
            failures.append(f"{relative}: expected {expected}, got {actual}")
    if failures:
        raise SystemExit("\n".join(failures))
    print("all upstream SHA-256 hashes verified")


if __name__ == "__main__":
    main()
