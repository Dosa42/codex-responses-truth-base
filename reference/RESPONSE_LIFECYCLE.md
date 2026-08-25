# Responses Lifecycle — Navigation Reference

This file is orientation only. Exact fields and events come from `upstream/openapi/openapi.yaml` and the snapshotted Responses/streaming docs.

Typical flow:

1. Create a response with model, input, optional instructions/tools and explicit options.
2. Receive a completed response or stream events.
3. Built-in hosted tools are handled by the OpenAI Responses runtime according to their schemas.
4. Custom function calls require the caller to execute the named function and return `function_call_output` with the matching call ID.
5. Continue until no caller-executed function calls remain and a terminal response is produced.

Do not infer required fields from this orientation file.
