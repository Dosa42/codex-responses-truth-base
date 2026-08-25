# Reusable Artifacts

Material here is designed to be copied into consuming projects when useful. It is **not** authoritative API documentation.

Before reusing an artifact, consult `ai/REUSE_MAP.json` and its upstream truth sources.

The TypeScript reference client intentionally has no GUI, Android, Termux, Kali, filesystem, shell-host, or project-framework dependency. OpenAI-hosted tools are passed to Responses as tool definitions; only custom function tools are executed by caller-supplied handlers.
