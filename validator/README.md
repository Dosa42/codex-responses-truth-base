# Downstream Codex Responses Validator

This directory contains the **portable executable validator for consuming projects**.

The repository's `scripts/verify_*.py` files verify the truth base itself. This validator does that **and** verifies that a separate project which reused this repository still matches the declared truth/reuse contract.

## Required downstream workflow

After an AI or developer reuses artifacts from this repository:

1. Copy `integration-manifest.template.json` into the consuming project as `codex-responses.integration.json`.
2. Replace the OpenAPI SHA placeholder with the current value from `upstream/provenance/snapshot.json`.
3. Declare only the capabilities actually reused.
4. Declare copied/adapted artifacts and their target paths.
5. Put the consuming project's real build/test/typecheck commands in `validation.commands` as argv arrays.
6. Run the validator **after the project build/change**.

From this truth-base checkout:

```bash
./validator/codex-responses-validate --project /path/to/project
```

Equivalent portable invocation:

```bash
python validator/codex_responses_validate.py --project /path/to/project
```

Machine-readable report:

```bash
python validator/codex_responses_validate.py \
  --project /path/to/project \
  --report /path/to/project/codex-responses.validation.json
```

## What it validates

The validator fails closed when it finds:

- corruption or drift in the pinned official truth snapshot;
- stale derived schema provenance;
- a project pinned to a different OpenAPI snapshot;
- unknown declared capabilities;
- a missing reused artifact;
- a `copied_exact` artifact whose bytes differ from the truth-base artifact;
- no evidence that the consuming project actually uses the Responses API;
- Chat Completions substitution unless explicitly allowed;
- use of the private/product `chatgpt.com/backend-api/codex` endpoint unless explicitly allowed;
- a declared project build/test/typecheck command that fails.

`mode: "adapted"` is allowed for intentionally modified reusable artifacts, but it is reported as a warning because byte identity can no longer prove equivalence.

## Exit status

- `0`: all required validations passed.
- `1`: at least one required validation failed.
- `2`: reserved for invocation/runtime misuse by future validator versions.

The JSON report contains every finding with `PASS`, `WARN`, or `FAIL`, making it suitable for CI and AI/code-agent consumption.

## Important

This validator does **not** invent API requirements. It validates against the pinned truth files and the consuming project's explicit `codex-responses.integration.json` contract.
