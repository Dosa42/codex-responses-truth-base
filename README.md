# OpenAI Codex Responses Truth Base

**This repository is a reference and reuse base for OpenAI Codex Responses integrations. It is not an application, UI, or project-specific implementation.**

## Start here

- Need authoritative upstream API truth? → [`upstream/`](upstream/)
- Need machine-readable Responses/tool schemas? → [`schema/`](schema/)
- Need capability explanations and boundaries? → [`reference/`](reference/)
- Need reusable integration artifacts? → [`artifacts/`](artifacts/)
- Need structural examples/fixtures? → [`fixtures/`](fixtures/)
- Are you an AI/code agent? → **[`ai/READ_FIRST.md`](ai/READ_FIRST.md)**

## Truth order

1. Pinned official OpenAI OpenAPI snapshot in `upstream/openapi/openapi.yaml`.
2. Snapshotted official OpenAI documentation in `upstream/docs/`.
3. Machine-derived material in `schema/`.
4. Human/AI orientation material in `reference/`.
5. Reusable implementation artifacts in `artifacts/`.
6. Examples and fixtures in `fixtures/`.

If layers disagree, the higher layer wins. **Examples and reusable code are never evidence of OpenAI API behavior.**

See [`SOURCE_OF_TRUTH.md`](SOURCE_OF_TRUTH.md), [`MANIFEST.json`](MANIFEST.json), and [`ai/TRUTH_PRIORITY.json`](ai/TRUTH_PRIORITY.json) before deriving architecture from this repository.
