#!/usr/bin/env python3
"""Derive a navigable Responses/agentic OpenAPI fragment from the full pinned schema."""
from __future__ import annotations

import hashlib
import json
import pathlib
import re

import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "upstream/openapi/openapi.yaml"
OUT = ROOT / "schema"

PATH_PREFIXES = (
    "/responses",
    "/containers",
    "/skills",
    "/vector_stores",
)
NAME_PATTERN = re.compile(
    r"response|tool|function|shell|container|skill|mcp|connector|computer|file.?search|web.?search|apply.?patch|code.?interpreter|reasoning|conversation",
    re.IGNORECASE,
)


def main() -> None:
    raw = SOURCE.read_bytes()
    document = yaml.safe_load(raw)
    paths = document.get("paths", {})
    components = document.get("components", {})
    schemas = components.get("schemas", {})

    selected_paths = {
        path: value for path, value in paths.items() if path.startswith(PATH_PREFIXES)
    }
    selected_schemas = {
        name: value for name, value in schemas.items() if NAME_PATTERN.search(name)
    }

    OUT.mkdir(parents=True, exist_ok=True)
    fragment = {
        "_provenance": {
            "authority": "derived",
            "derived_from": "upstream/openapi/openapi.yaml",
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "manual_interpretation": False,
        },
        "openapi": document.get("openapi"),
        "info": document.get("info"),
        "paths": selected_paths,
        "components": {"schemas": selected_schemas},
    }
    (OUT / "responses-agentic-openapi-fragment.json").write_text(
        json.dumps(fragment, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    index = {
        "authority": "derived",
        "source": "upstream/openapi/openapi.yaml",
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "path_count": len(selected_paths),
        "schema_count": len(selected_schemas),
        "paths": sorted(selected_paths),
        "schemas": sorted(selected_schemas),
        "artifact": "schema/responses-agentic-openapi-fragment.json",
    }
    (OUT / "INDEX.json").write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    print(f"derived {len(selected_paths)} paths and {len(selected_schemas)} schemas")


if __name__ == "__main__":
    main()
