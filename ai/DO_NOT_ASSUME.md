# Do Not Assume

The following are common invalid shortcuts when using this repository:

- A field seen in a sample exists in every API version.
- A model alias is identical to a pinned model snapshot forever.
- A built-in OpenAI tool needs a local executor.
- A custom function tool is executed by OpenAI.
- Codex Hooks are a generic Responses `tool` type.
- Plugin packaging is identical to MCP or Skills.
- A beta feature may be used without its documented beta requirements.
- A browser, Android, Termux, shell, GUI, server, database, or framework exists unless the consuming project explicitly establishes it.
- A reusable artifact is more current than the pinned upstream source.

When uncertain, inspect `upstream/` and state the unresolved fact.
