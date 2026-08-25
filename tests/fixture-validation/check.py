#!/usr/bin/env python3
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
for path in (ROOT / "fixtures").glob("*.json"):
    data = json.loads(path.read_text(encoding="utf-8"))
    if "_fixture_notice" not in data:
        raise SystemExit(f"{path} is missing _fixture_notice")
print("fixture notices verified")
