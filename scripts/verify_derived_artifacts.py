#!/usr/bin/env python3
"""Check that derived schema metadata still matches the pinned full OpenAPI file."""
from __future__ import annotations

import hashlib
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]


def main() -> None:
    source = ROOT / "upstream/openapi/openapi.yaml"
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    index = json.loads((ROOT / "schema/INDEX.json").read_text(encoding="utf-8"))
    fragment = json.loads((ROOT / "schema/responses-agentic-openapi-fragment.json").read_text(encoding="utf-8"))
    if index.get("source_sha256") != expected:
        raise SystemExit("schema/INDEX.json is stale")
    if fragment.get("_provenance", {}).get("source_sha256") != expected:
        raise SystemExit("derived OpenAPI fragment is stale")
    if fragment.get("_provenance", {}).get("manual_interpretation") is not False:
        raise SystemExit("derived fragment provenance is invalid")
    print("derived artifacts match pinned OpenAPI hash")


if __name__ == "__main__":
    main()
