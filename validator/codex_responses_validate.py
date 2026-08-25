#!/usr/bin/env python3
"""
Portable validator for projects that reuse Dosa42/codex-responses-truth-base.

Goals:
- validate the truth-base snapshot itself before trusting derived artifacts;
- validate a consuming project's declared reuse against the truth base;
- fail closed on missing evidence, stale copied artifacts, unknown capabilities,
  legacy endpoint substitutions, invalid JSON, or failed project validation commands;
- emit both human-readable output and an optional machine-readable JSON report.

The validator uses only the Python standard library.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Iterable

SKIP_DIRS = {
    ".git", "node_modules", "dist", "build", ".next", ".vite", ".turbo",
    "coverage", ".venv", "venv", "__pycache__", ".pytest_cache",
}
SOURCE_SUFFIXES = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".json", ".yaml", ".yml",
}
RESPONSE_EVIDENCE = (
    "/v1/responses",
    "api.openai.com/v1/responses",
    ".responses.create(",
    ".responses.stream(",
    "responses.create(",
    "responses.stream(",
    "client.responses",
)
LEGACY_OR_PRIVATE_PATTERNS = {
    "chat_completions": ("/v1/chat/completions", "chat.completions.create(", ".chat.completions."),
    "private_codex_backend": ("chatgpt.com/backend-api/codex", "/backend-api/codex"),
}
REQUIRED_TRUTH_FILES = (
    "SOURCE_OF_TRUTH.md",
    "VERSION_LOCK.json",
    "ai/TRUTH_PRIORITY.json",
    "ai/CAPABILITY_INDEX.json",
    "upstream/provenance/snapshot.json",
    "upstream/openapi/openapi.yaml",
    "schema/INDEX.json",
)


@dataclass
class Finding:
    level: str
    code: str
    message: str
    path: str | None = None


class Validation:
    def __init__(self) -> None:
        self.findings: list[Finding] = []

    def pass_(self, code: str, message: str, path: Path | str | None = None) -> None:
        self.findings.append(Finding("PASS", code, message, str(path) if path else None))

    def warn(self, code: str, message: str, path: Path | str | None = None) -> None:
        self.findings.append(Finding("WARN", code, message, str(path) if path else None))

    def fail(self, code: str, message: str, path: Path | str | None = None) -> None:
        self.findings.append(Finding("FAIL", code, message, str(path) if path else None))

    @property
    def ok(self) -> bool:
        return not any(f.level == "FAIL" for f in self.findings)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def repo_root_from_script() -> Path:
    return Path(__file__).resolve().parents[1]


def iter_project_files(root: Path, extra_suffixes: Iterable[str] = ()) -> Iterable[Path]:
    suffixes = SOURCE_SUFFIXES | {s if s.startswith(".") else f".{s}" for s in extra_suffixes}
    for base, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        base_path = Path(base)
        for name in files:
            p = base_path / name
            if p.suffix.lower() in suffixes:
                yield p


def read_text_safely(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def validate_truth_base(truth_root: Path, out: Validation) -> dict[str, Any]:
    for rel in REQUIRED_TRUTH_FILES:
        p = truth_root / rel
        if p.is_file():
            out.pass_("truth.file.present", f"Required truth file present: {rel}", p)
        else:
            out.fail("truth.file.missing", f"Required truth file missing: {rel}", p)

    snapshot_path = truth_root / "upstream/provenance/snapshot.json"
    if not snapshot_path.is_file():
        return {}

    try:
        snapshot = load_json(snapshot_path)
    except Exception as e:
        out.fail("truth.snapshot.invalid_json", f"Could not parse snapshot.json: {e}", snapshot_path)
        return {}

    files = snapshot.get("files")
    if not isinstance(files, dict) or not files:
        out.fail("truth.snapshot.files_missing", "snapshot.json has no files map.", snapshot_path)
        return snapshot

    for rel, metadata in files.items():
        if not isinstance(metadata, dict):
            out.fail("truth.snapshot.entry_invalid", f"Invalid snapshot metadata for {rel}", snapshot_path)
            continue
        expected = str(metadata.get("sha256") or "").lower()
        p = truth_root / rel
        if not p.is_file():
            out.fail("truth.hash.file_missing", f"Snapshot file is missing: {rel}", p)
            continue
        actual = sha256_file(p)
        if expected and actual == expected:
            out.pass_("truth.hash.match", f"SHA-256 verified: {rel}", p)
        else:
            out.fail(
                "truth.hash.mismatch",
                f"SHA-256 mismatch for {rel}: expected {expected or '<missing>'}, got {actual}",
                p,
            )

    openapi_meta = files.get("upstream/openapi/openapi.yaml", {})
    openapi_sha = str(openapi_meta.get("sha256") or "")
    index_path = truth_root / "schema/INDEX.json"
    if index_path.is_file():
        try:
            index = load_json(index_path)
            source_sha = str(index.get("source_sha256") or "")
            if openapi_sha and source_sha == openapi_sha:
                out.pass_("truth.derived.index_provenance", "schema/INDEX.json matches the current OpenAPI snapshot hash.", index_path)
            else:
                out.fail(
                    "truth.derived.index_stale",
                    f"schema/INDEX.json source hash {source_sha or '<missing>'} does not match OpenAPI {openapi_sha or '<missing>'}.",
                    index_path,
                )
        except Exception as e:
            out.fail("truth.derived.index_invalid", f"Could not parse schema/INDEX.json: {e}", index_path)

    capability_path = truth_root / "ai/CAPABILITY_INDEX.json"
    if capability_path.is_file():
        try:
            capabilities = load_json(capability_path)
            if isinstance(capabilities, dict) and "responses" in capabilities:
                out.pass_("truth.capability_index", f"Capability index loaded with {len(capabilities)} entries.", capability_path)
            else:
                out.fail("truth.capability_index_invalid", "Capability index is missing the 'responses' entry.", capability_path)
        except Exception as e:
            out.fail("truth.capability_index_invalid", f"Could not parse capability index: {e}", capability_path)

    return snapshot


def validate_manifest(
    project_root: Path,
    truth_root: Path,
    manifest_path: Path,
    out: Validation,
) -> dict[str, Any]:
    try:
        manifest = load_json(manifest_path)
    except Exception as e:
        out.fail("project.manifest.invalid", f"Could not parse integration manifest: {e}", manifest_path)
        return {}

    if manifest.get("schema_version") != 1:
        out.fail("project.manifest.version", "schema_version must be exactly 1.", manifest_path)
    else:
        out.pass_("project.manifest.version", "Integration manifest schema_version=1.", manifest_path)

    truth = manifest.get("truth_base", {})
    if not isinstance(truth, dict):
        out.fail("project.manifest.truth_base", "truth_base must be an object.", manifest_path)
        truth = {}

    expected_repo = "Dosa42/codex-responses-truth-base"
    repo_name = str(truth.get("repository") or "")
    if repo_name == expected_repo:
        out.pass_("project.truth.repository", f"Truth-base repository is {expected_repo}.", manifest_path)
    else:
        out.fail("project.truth.repository", f"truth_base.repository must be '{expected_repo}', got '{repo_name}'.", manifest_path)

    snapshot_path = truth_root / "upstream/provenance/snapshot.json"
    current_openapi_sha = ""
    if snapshot_path.is_file():
        try:
            snapshot = load_json(snapshot_path)
            current_openapi_sha = str(
                snapshot.get("files", {})
                .get("upstream/openapi/openapi.yaml", {})
                .get("sha256", "")
            )
        except Exception:
            pass

    pinned_sha = str(truth.get("openapi_sha256") or "")
    if not pinned_sha:
        out.fail("project.truth.openapi_unpinned", "truth_base.openapi_sha256 must pin the OpenAPI truth snapshot.", manifest_path)
    elif pinned_sha != current_openapi_sha:
        out.fail(
            "project.truth.openapi_stale",
            f"Project pins OpenAPI {pinned_sha}, but this truth base is {current_openapi_sha}.",
            manifest_path,
        )
    else:
        out.pass_("project.truth.openapi_pin", "Project OpenAPI pin matches the current truth base.", manifest_path)

    integration = manifest.get("integration", {})
    if not isinstance(integration, dict):
        out.fail("project.manifest.integration", "integration must be an object.", manifest_path)
        integration = {}

    if integration.get("responses_api") is not True:
        out.fail("project.responses.required", "integration.responses_api must be true.", manifest_path)
    else:
        out.pass_("project.responses.declared", "Project declares Responses API integration.", manifest_path)

    capabilities_path = truth_root / "ai/CAPABILITY_INDEX.json"
    known_caps: set[str] = set()
    try:
        caps = load_json(capabilities_path)
        if isinstance(caps, dict):
            known_caps = set(caps.keys())
    except Exception:
        pass

    declared_caps = integration.get("capabilities", [])
    if not isinstance(declared_caps, list):
        out.fail("project.capabilities.type", "integration.capabilities must be an array.", manifest_path)
        declared_caps = []
    for cap in declared_caps:
        if not isinstance(cap, str):
            out.fail("project.capability.invalid", f"Capability name must be a string: {cap!r}", manifest_path)
        elif cap not in known_caps:
            out.fail("project.capability.unknown", f"Unknown capability '{cap}'. It is not in ai/CAPABILITY_INDEX.json.", manifest_path)
        else:
            out.pass_("project.capability.known", f"Declared capability exists in truth base: {cap}", manifest_path)

    artifacts = integration.get("artifacts", [])
    if not isinstance(artifacts, list):
        out.fail("project.artifacts.type", "integration.artifacts must be an array.", manifest_path)
        artifacts = []

    for idx, item in enumerate(artifacts):
        if not isinstance(item, dict):
            out.fail("project.artifact.invalid", f"Artifact entry #{idx} must be an object.", manifest_path)
            continue
        source_rel = str(item.get("source") or "")
        target_rel = str(item.get("target") or "")
        mode = str(item.get("mode") or "copied_exact")
        if not source_rel or not target_rel:
            out.fail("project.artifact.path_missing", f"Artifact entry #{idx} requires source and target.", manifest_path)
            continue
        source = (truth_root / source_rel).resolve()
        target = (project_root / target_rel).resolve()
        try:
            source.relative_to(truth_root.resolve())
            target.relative_to(project_root.resolve())
        except ValueError:
            out.fail("project.artifact.path_escape", f"Artifact entry #{idx} escapes its allowed root.", manifest_path)
            continue
        if not source.is_file():
            out.fail("project.artifact.source_missing", f"Truth-base artifact does not exist: {source_rel}", source)
            continue
        if not target.is_file():
            out.fail("project.artifact.target_missing", f"Project artifact does not exist: {target_rel}", target)
            continue
        if mode == "copied_exact":
            source_sha = sha256_file(source)
            target_sha = sha256_file(target)
            if source_sha == target_sha:
                out.pass_("project.artifact.exact", f"Exact reusable artifact verified: {target_rel}", target)
            else:
                out.fail(
                    "project.artifact.modified",
                    f"{target_rel} differs from truth-base artifact {source_rel}. Declare mode='adapted' only when modification is intentional.",
                    target,
                )
        elif mode == "adapted":
            out.warn(
                "project.artifact.adapted",
                f"Artifact is intentionally adapted and cannot be byte-verified: {target_rel}. Static integration checks still apply.",
                target,
            )
        else:
            out.fail("project.artifact.mode", f"Unsupported artifact mode '{mode}' for {target_rel}.", manifest_path)

    return manifest


def validate_project_sources(project_root: Path, manifest: dict[str, Any], out: Validation) -> None:
    validation_cfg = manifest.get("validation", {})
    if not isinstance(validation_cfg, dict):
        validation_cfg = {}

    extra_suffixes = validation_cfg.get("extra_source_suffixes", [])
    if not isinstance(extra_suffixes, list):
        extra_suffixes = []

    files = list(iter_project_files(project_root, extra_suffixes))
    if not files:
        out.fail("project.sources.none", "No source/configuration files were found to inspect.", project_root)
        return

    responses_hits: list[Path] = []
    legacy_hits: dict[str, list[Path]] = {k: [] for k in LEGACY_OR_PRIVATE_PATTERNS}
    invalid_json: list[Path] = []

    for p in files:
        text = read_text_safely(p)
        low = text.lower()
        if any(pattern.lower() in low for pattern in RESPONSE_EVIDENCE):
            responses_hits.append(p)

        for name, patterns in LEGACY_OR_PRIVATE_PATTERNS.items():
            if any(pattern.lower() in low for pattern in patterns):
                legacy_hits[name].append(p)

        if p.suffix.lower() == ".json":
            try:
                json.loads(text)
            except Exception:
                invalid_json.append(p)

    if responses_hits:
        sample = ", ".join(str(p.relative_to(project_root)) for p in responses_hits[:5])
        out.pass_("project.responses.evidence", f"Found Responses integration evidence in: {sample}", project_root)
    else:
        out.fail(
            "project.responses.no_evidence",
            "No Responses endpoint/SDK usage evidence was found in the inspected project files.",
            project_root,
        )

    allow_chat = bool(validation_cfg.get("allow_chat_completions", False))
    allow_private = bool(validation_cfg.get("allow_private_codex_backend", False))

    if legacy_hits["chat_completions"]:
        paths = ", ".join(str(p.relative_to(project_root)) for p in legacy_hits["chat_completions"][:5])
        if allow_chat:
            out.warn("project.legacy.chat_allowed", f"Chat Completions usage present but explicitly allowed by manifest: {paths}", project_root)
        else:
            out.fail(
                "project.legacy.chat_forbidden",
                f"Chat Completions usage detected where Responses-only reuse is expected: {paths}",
                project_root,
            )

    if legacy_hits["private_codex_backend"]:
        paths = ", ".join(str(p.relative_to(project_root)) for p in legacy_hits["private_codex_backend"][:5])
        if allow_private:
            out.warn("project.private_backend.allowed", f"Private Codex backend usage explicitly allowed by manifest: {paths}", project_root)
        else:
            out.fail(
                "project.private_backend.forbidden",
                f"Private/product Codex backend usage detected; truth base targets official API Platform Responses: {paths}",
                project_root,
            )

    for p in invalid_json:
        out.warn("project.json.nonstandard", f"Non-standard/JSONC file could not be parsed as strict JSON: {p.relative_to(project_root)}", p)


def run_validation_commands(project_root: Path, manifest: dict[str, Any], out: Validation) -> None:
    validation_cfg = manifest.get("validation", {})
    if not isinstance(validation_cfg, dict):
        return
    commands = validation_cfg.get("commands", [])
    if not isinstance(commands, list):
        out.fail("project.commands.type", "validation.commands must be an array.", project_root)
        return

    for idx, command in enumerate(commands):
        if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
            out.fail(
                "project.command.invalid",
                f"validation.commands[{idx}] must be a non-empty argv array of strings, not a shell command string.",
                project_root,
            )
            continue
        try:
            completed = subprocess.run(
                command,
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300,
                shell=False,
            )
        except FileNotFoundError:
            out.fail("project.command.missing_executable", f"Executable not found: {command[0]}", project_root)
            continue
        except subprocess.TimeoutExpired:
            out.fail("project.command.timeout", f"Validation command timed out: {shlex.join(command)}", project_root)
            continue
        except Exception as e:
            out.fail("project.command.error", f"Could not run {shlex.join(command)}: {e}", project_root)
            continue

        if completed.returncode == 0:
            out.pass_("project.command.pass", f"Command passed: {shlex.join(command)}", project_root)
        else:
            detail = (completed.stderr or completed.stdout or "").strip()
            if len(detail) > 1200:
                detail = detail[-1200:]
            out.fail(
                "project.command.fail",
                f"Command failed ({completed.returncode}): {shlex.join(command)}"
                + (f"\n{detail}" if detail else ""),
                project_root,
            )


def print_report(out: Validation) -> None:
    for f in out.findings:
        marker = {"PASS": "[PASS]", "WARN": "[WARN]", "FAIL": "[FAIL]"}[f.level]
        suffix = f" ({f.path})" if f.path else ""
        print(f"{marker} {f.code}: {f.message}{suffix}")
    counts = {level: sum(1 for f in out.findings if f.level == level) for level in ("PASS", "WARN", "FAIL")}
    print(f"\nResult: {'PASS' if out.ok else 'FAIL'} | PASS={counts['PASS']} WARN={counts['WARN']} FAIL={counts['FAIL']}")


def write_json_report(path: Path, out: Validation, truth_root: Path, project_root: Path | None) -> None:
    payload = {
        "validator": "codex-responses-truth-base",
        "ok": out.ok,
        "truth_root": str(truth_root),
        "project_root": str(project_root) if project_root else None,
        "findings": [asdict(f) for f in out.findings],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate the Codex Responses truth base and/or a consuming project against it."
    )
    parser.add_argument(
        "--truth-root",
        type=Path,
        default=repo_root_from_script(),
        help="Path to codex-responses-truth-base. Defaults to the repository containing this validator.",
    )
    parser.add_argument(
        "--project",
        type=Path,
        help="Consuming project to validate. If omitted, only the truth base itself is validated.",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        help="Integration manifest. Defaults to <project>/codex-responses.integration.json.",
    )
    parser.add_argument("--report", type=Path, help="Optional JSON report output path.")
    args = parser.parse_args()

    truth_root = args.truth_root.resolve()
    project_root = args.project.resolve() if args.project else None
    out = Validation()

    validate_truth_base(truth_root, out)

    if project_root is not None:
        if not project_root.is_dir():
            out.fail("project.root.missing", f"Project directory does not exist: {project_root}", project_root)
        else:
            manifest_path = (args.manifest.resolve() if args.manifest else project_root / "codex-responses.integration.json")
            if not manifest_path.is_file():
                out.fail(
                    "project.manifest.missing",
                    "Missing codex-responses.integration.json. Copy validator/integration-manifest.template.json and declare the reuse contract.",
                    manifest_path,
                )
            else:
                manifest = validate_manifest(project_root, truth_root, manifest_path, out)
                if manifest:
                    validate_project_sources(project_root, manifest, out)
                    run_validation_commands(project_root, manifest, out)

    print_report(out)
    if args.report:
        write_json_report(args.report.resolve(), out, truth_root, project_root)
    return 0 if out.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
