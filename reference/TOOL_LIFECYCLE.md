# Tool Lifecycle — Boundary Reference

There are materially different tool classes. Do not flatten them:

- **OpenAI built-in/hosted tools**: described by official Responses tool schemas and executed by OpenAI infrastructure where documented.
- **Custom function tools**: the model emits a function call; the consuming application executes it and returns a matching function-call output.
- **MCP/connectors**: governed by the MCP/connectors schemas and authentication/approval semantics documented upstream.
- **Codex Hooks**: Codex runtime lifecycle callbacks, not automatically a Responses tool type.

Exact names, beta requirements and parameter schemas must be read from `upstream/`.
