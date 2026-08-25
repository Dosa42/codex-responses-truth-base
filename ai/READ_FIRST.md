# AI / Coding Agent — Read This First

This repository is a **truth reference and reuse base**, not an application to complete.

Before answering questions or copying code from this repository:

1. Read `SOURCE_OF_TRUTH.md`.
2. Read `ai/TRUTH_PRIORITY.json`.
3. Locate the capability in `ai/CAPABILITY_INDEX.json`.
4. Inspect the corresponding official source under `upstream/`.
5. Use `schema/` only as a machine-derived navigation aid.
6. Use `artifacts/` only when implementation reuse is requested.
7. If you reuse this repository in another project, create that project's `codex-responses.integration.json` from `validator/integration-manifest.template.json`.
8. **Before claiming the consuming integration is complete or valid, run `validator/codex-responses-validate --project <project>` and require exit code 0.**

## Hard rules

- Do not infer missing API fields.
- Do not convert examples into API requirements.
- Do not treat reusable TypeScript as authoritative schema.
- Do not assume a Codex-runtime feature is a Responses API feature.
- Do not assume a Responses built-in tool is a locally executed custom function.
- Do not silently substitute a model, endpoint, tool type, reasoning effort, beta header, or authentication flow.
- Do not redesign a consuming project merely because this repository contains broader capabilities.
- Do not report a consuming integration as validated when the downstream validator was not run or returned non-zero.
- When upstream sources disagree with a derived file, upstream wins.

If a requested capability cannot be established from the pinned upstream material, report that fact instead of filling the gap.
