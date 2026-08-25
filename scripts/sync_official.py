#!/usr/bin/env python3
"""Fetch official OpenAI truth sources without rewriting their contents."""
from __future__ import annotations

import hashlib
import json
import pathlib
import urllib.request
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "VERSION_LOCK.json").read_text(encoding="utf-8"))

SOURCES = {
    "upstream/openapi/openapi.yaml": LOCK["openai_openapi"]["raw_url"],
    "upstream/docs/gpt-5.6-sol.md": "https://developers.openai.com/api/docs/models/gpt-5.6-sol.md",
    "upstream/docs/responses-api.md": "https://developers.openai.com/api/docs/guides/migrate-to-responses.md",
    "upstream/docs/conversation-state.md": "https://developers.openai.com/api/docs/guides/conversation-state.md",
    "upstream/docs/background-mode.md": "https://developers.openai.com/api/docs/guides/background.md",
    "upstream/docs/streaming-responses.md": "https://developers.openai.com/api/docs/guides/streaming-responses.md",
    "upstream/docs/webhooks.md": "https://developers.openai.com/api/docs/guides/webhooks.md",
    "upstream/docs/compaction.md": "https://developers.openai.com/api/docs/guides/compaction.md",
    "upstream/docs/function-calling.md": "https://developers.openai.com/api/docs/guides/function-calling.md",
    "upstream/docs/hosted-shell.md": "https://developers.openai.com/api/docs/guides/tools-shell.md",
    "upstream/docs/code-interpreter.md": "https://developers.openai.com/api/docs/guides/tools-code-interpreter.md",
    "upstream/docs/skills.md": "https://developers.openai.com/api/docs/guides/tools-skills.md",
    "upstream/docs/tool-search.md": "https://developers.openai.com/api/docs/guides/tools-tool-search.md",
    "upstream/docs/programmatic-tool-calling.md": "https://developers.openai.com/api/docs/guides/tools-programmatic-tool-calling.md",
    "upstream/docs/apply-patch.md": "https://developers.openai.com/api/docs/guides/tools-apply-patch.md",
    "upstream/docs/computer-use.md": "https://developers.openai.com/api/docs/guides/tools-computer-use.md",
    "upstream/docs/mcp-connectors.md": "https://developers.openai.com/api/docs/guides/tools-connectors-mcp.md",
    "upstream/docs/multi-agent.md": "https://developers.openai.com/api/docs/guides/responses-multi-agent.md",
    "upstream/docs/codex-hooks.md": "https://developers.openai.com/codex/hooks.md",
    "upstream/docs/plugin-architecture.md": "https://developers.openai.com/plugins/concepts/plugins.md",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "codex-responses-truth-base/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response:
        data = response.read()
        final_url = response.geturl()
    if not data:
        raise RuntimeError(f"Official source returned an empty body: {url}")
    return data, final_url


def main() -> None:
    snapshot = {
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "openapi_commit": LOCK["openai_openapi"]["commit"],
        "files": {},
    }
    hashes: list[str] = []

    for relative, source_url in SOURCES.items():
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        data, final_url = fetch(source_url)
        target.write_bytes(data)
        digest = sha256(data)
        snapshot["files"][relative] = {
            "requested_url": source_url,
            "final_url": final_url,
            "sha256": digest,
            "bytes": len(data),
        }
        hashes.append(f"{digest}  {relative}")
        print(f"synced {relative} ({len(data)} bytes)")

    provenance = ROOT / "upstream/provenance"
    provenance.mkdir(parents=True, exist_ok=True)
    (provenance / "sources.json").write_text(
        json.dumps(SOURCES, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (provenance / "snapshot.json").write_text(
        json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (provenance / "SHA256SUMS").write_text("\n".join(sorted(hashes)) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
