# Source of Truth

This repository deliberately separates **official upstream truth** from derived references and reusable code.

## Authority order

1. `upstream/openapi/openapi.yaml` — pinned, unmodified official OpenAI OpenAPI snapshot.
2. `upstream/docs/` — snapshotted official OpenAI documentation, stored unmodified as retrieved.
3. `schema/` — machine-derived extractions from the pinned OpenAPI snapshot.
4. `reference/` — orientation material that cites its upstream inputs.
5. `artifacts/` — reusable implementation material; never authoritative about API behavior.
6. `fixtures/` — examples only; never authoritative.

When two layers conflict, the higher-authority layer wins.

## Non-inference rule

Missing API behavior must not be filled in from intuition, examples, older SDK knowledge, project code, or neighboring APIs. Inspect the pinned schema or official docs. If the official sources do not establish a claim, mark it unknown or version-dependent.

## Upstream schema lock

The initial schema snapshot is pinned to official repository `openai/openai-openapi` commit:

`a0a969c1f51254ff5c0393933787c76e2576912a` (2026-08-24)

The sync process records source URLs, retrieval time, SHA-256 hashes, and the pinned revision in `upstream/provenance/`.

## Derived-material rule

Generated schema files must carry provenance in `schema/INDEX.json`. Editing a generated schema by hand invalidates it; regenerate it instead.
