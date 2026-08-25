# Error Reference

Error object shapes, HTTP responses, incomplete states, stream failure events and tool-specific failure objects must be taken from the pinned OpenAPI schema.

Use `schema/INDEX.json` to locate error-related component names, then inspect the original component in `upstream/openapi/openapi.yaml`. Do not normalize different error types into a made-up universal structure unless a consuming project explicitly chooses to do so.
