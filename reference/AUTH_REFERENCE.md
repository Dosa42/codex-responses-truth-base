# Authentication Reference

For public OpenAI API requests, authentication and security schemes are defined by the pinned full OpenAPI document under `upstream/openapi/openapi.yaml`.

This repository does **not** infer ChatGPT product OAuth, Codex product-backend authentication, browser login flows, or local credential storage from the public API schema. A consuming project must choose its authentication architecture explicitly and verify it against the relevant official source.
