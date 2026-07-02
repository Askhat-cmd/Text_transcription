from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PRD_ID = "PRD-047.39"
SCHEMA_VERSION = "prd_047_39_architecture_inventory_v1"

RETIRED_COMPONENTS: tuple[dict[str, Any], ...] = (
    {
        "component_id": "answer_basic",
        "kind": "retired_pipeline",
        "candidate_paths": ["bot_psychologist/bot_agent/answer_basic.py"],
        "grep_patterns": ["answer_basic", "answer_question_basic("],
    },
    {
        "component_id": "answer_sag_aware",
        "kind": "retired_pipeline",
        "candidate_paths": ["bot_psychologist/bot_agent/answer_sag_aware.py"],
        "grep_patterns": ["answer_sag_aware", "answer_question_sag_aware("],
    },
    {
        "component_id": "answer_graph_powered",
        "kind": "retired_pipeline",
        "candidate_paths": ["bot_psychologist/bot_agent/answer_graph_powered.py"],
        "grep_patterns": ["answer_graph_powered", "answer_question_graph_powered("],
    },
    {
        "component_id": "sd_classifier",
        "kind": "retired_sd_module",
        "candidate_paths": ["bot_psychologist/bot_agent/sd_classifier.py"],
        "grep_patterns": ["sd_classifier", "sd_filter=", "_load_sd_prompt", "sd_overlay"],
    },
    {
        "component_id": "user_level_adapter",
        "kind": "retired_level_module",
        "candidate_paths": ["bot_psychologist/bot_agent/user_level_adapter.py"],
        "grep_patterns": ["user_level_adapter", "filter_blocks_by_level"],
    },
    *(
        {
            "component_id": name.removesuffix(".md"),
            "kind": "retired_prompt",
            "candidate_paths": [
                f"bot_psychologist/bot_agent/{name}",
                f"bot_psychologist/bot_agent/legacy/prompts/{name}",
            ],
            "grep_patterns": [name, name.removesuffix(".md")],
        }
        for name in (
            "prompt_sd_green.md",
            "prompt_sd_blue.md",
            "prompt_sd_red.md",
            "prompt_sd_orange.md",
            "prompt_sd_yellow.md",
            "prompt_sd_purple.md",
            "prompt_system_level_beginner.md",
            "prompt_system_level_intermediate.md",
            "prompt_system_level_advanced.md",
        )
    ),
)

BRANCH_CANDIDATES = (
    "bot-psychologist",
    "feature/sd-integration",
    "refactor/simplify-retrieval-pipeline",
)

REFERENCE_DOCS = (
    "docs/PROJECT_STATE.md",
    "docs/PRD_INDEX.md",
    "docs/DECISIONS.md",
    "docs/ROADMAP.md",
)


@dataclass(frozen=True)
class GrepHit:
    path: str
    line: int
    text: str


def _repo_root_from_file() -> Path:
    return Path(__file__).resolve().parents[1]


def _run_git(repo_root: Path, args: list[str], check: bool = False) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo_root,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def _git_lines(repo_root: Path, args: list[str]) -> list[str]:
    result = _run_git(repo_root, args)
    if result.returncode not in (0, 1):
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _git_ls_files(repo_root: Path, pathspec: str) -> list[str]:
    return _git_lines(repo_root, ["ls-files", pathspec])


def _git_grep(repo_root: Path, pattern: str) -> list[GrepHit]:
    result = _run_git(repo_root, ["grep", "-n", "-I", "-F", "--", pattern])
    if result.returncode not in (0, 1):
        return []
    hits: list[GrepHit] = []
    for line in result.stdout.splitlines():
        parts = line.split(":", 2)
        if len(parts) != 3:
            continue
        path, line_no, text = parts
        try:
            number = int(line_no)
        except ValueError:
            number = 0
        hits.append(GrepHit(path=path, line=number, text=text.strip()))
    return hits


def _last_commit_for_path(repo_root: Path, rel_path: str) -> str:
    result = _run_git(repo_root, ["log", "--all", "-1", "--format=%h", "--", rel_path])
    return result.stdout.strip() or "not_found"


def _is_active_runtime_ref(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if "/tests/" in normalized or normalized.startswith("TO_DO_LIST/") or normalized.startswith("docs/"):
        return False
    return normalized.startswith("bot_psychologist/bot_agent/") or normalized.startswith("bot_psychologist/api/")


def _is_test_ref(path: str) -> bool:
    return "/tests/" in path.replace("\\", "/")


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    def cell(value: Any) -> str:
        text = str(value)
        text = text.replace("|", "\\|").replace("\n", "<br>")
        return text

    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell(value) for value in row) + " |")
    return "\n".join(lines)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_legacy_dead_code_inventory(repo_root: Path) -> list[dict[str, Any]]:
    inventory: list[dict[str, Any]] = []
    for component in RETIRED_COMPONENTS:
        hit_map: dict[str, GrepHit] = {}
        for pattern in component["grep_patterns"]:
            for hit in _git_grep(repo_root, pattern):
                key = f"{hit.path}:{hit.line}:{hit.text}"
                hit_map[key] = hit

        hits = sorted(hit_map.values(), key=lambda item: (item.path, item.line, item.text))
        active_hits = [hit for hit in hits if _is_active_runtime_ref(hit.path)]
        test_hits = [hit for hit in hits if _is_test_ref(hit.path)]
        doc_hits = [
            hit
            for hit in hits
            if hit.path.startswith("docs/") or hit.path.startswith("TO_DO_LIST/")
        ]

        if active_hits:
            import_graph_status = "referenced_by_active_path"
            proposed_classification = "unclear_needs_trace"
        elif test_hits:
            import_graph_status = "referenced_by_test_only"
            proposed_classification = "dead_confirmed"
        else:
            import_graph_status = "dead_confirmed"
            proposed_classification = "dead_confirmed"

        last_commits = {
            path: _last_commit_for_path(repo_root, path)
            for path in component["candidate_paths"]
        }

        inventory.append(
            {
                "component_id": component["component_id"],
                "kind": component["kind"],
                "candidate_paths": component["candidate_paths"],
                "file_paths_referencing_it": [
                    {
                        "path": hit.path,
                        "line": hit.line,
                        "preview": hit.text[:180],
                    }
                    for hit in hits
                ],
                "reference_counts": {
                    "total": len(hits),
                    "active_runtime": len(active_hits),
                    "test": len(test_hits),
                    "docs_or_logs": len(doc_hits),
                },
                "import_graph_status": import_graph_status,
                "last_commit_touching_it": last_commits,
                "proposed_classification": proposed_classification,
            }
        )
    return inventory


ENV_CALL_RE = re.compile(
    r"os\.(?:getenv|environ\.get)\(\s*['\"](?P<name>[A-Z0-9_]+)['\"]\s*(?:,\s*(?P<default>[^)\n]+))?\)"
)
ENV_INDEX_RE = re.compile(r"os\.environ\[\s*['\"](?P<name>[A-Z0-9_]+)['\"]\s*\]")


def _iter_python_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    ignored_parts = {"__pycache__", ".pytest_cache", ".venv", "node_modules"}
    result: list[Path] = []
    for path in root.rglob("*.py"):
        if any(part in ignored_parts for part in path.parts):
            continue
        result.append(path)
    return sorted(result)


def _extract_env_calls(repo_root: Path, rel_roots: list[str]) -> dict[str, dict[str, Any]]:
    flags: dict[str, dict[str, Any]] = {}
    for rel_root in rel_roots:
        for path in _iter_python_files(repo_root / rel_root):
            rel_path = path.relative_to(repo_root).as_posix()
            text = path.read_text(encoding="utf-8", errors="ignore")
            for line_no, line in enumerate(text.splitlines(), start=1):
                matches = list(ENV_CALL_RE.finditer(line)) + list(ENV_INDEX_RE.finditer(line))
                for match in matches:
                    name = match.group("name")
                    default = match.groupdict().get("default")
                    record = flags.setdefault(
                        name,
                        {
                            "flag_name": name,
                            "default_values": set(),
                            "read_in_files": [],
                            "controls_what": "",
                            "last_prd_that_introduced_it": "unknown",
                            "proposed_status": "active_tunable",
                        },
                    )
                    if default:
                        record["default_values"].add(default.strip())
                    else:
                        record["default_values"].add("<required>")
                    record["read_in_files"].append(
                        {
                            "path": rel_path,
                            "line": line_no,
                            "code": line.strip()[:220],
                        }
                    )
    return flags


def _infer_controls(flag_name: str, read_entries: list[dict[str, Any]]) -> str:
    names = " ".join(entry["path"] for entry in read_entries).lower()
    flag_lower = flag_name.lower()
    if "openai" in flag_lower or "voyage" in flag_lower or "api_key" in flag_lower:
        return "provider credentials / model provider integration"
    if "trace" in flag_lower or "debug" in flag_lower:
        return "debug and trace visibility"
    if "writer" in flag_lower or "kb_payload" in flag_lower:
        return "Writer context / knowledge payload behavior"
    if "retrieval" in flag_lower or "rag" in flag_lower or "chroma" in flag_lower:
        return "retrieval or vector-store behavior"
    if "semantic" in flag_lower or "card" in flag_lower:
        return "semantic-card pilot behavior"
    if "admin" in names:
        return "admin API/runtime surface"
    if "api" in names:
        return "API service runtime"
    return "runtime configuration"


def _propose_flag_status(flag_name: str, read_entries: list[dict[str, Any]]) -> str:
    name = flag_name.upper()
    joined = " ".join(entry["path"] for entry in read_entries)
    if any(token in name for token in ("LEGACY", "SD_", "USER_LEVEL")):
        return "retirement_candidate"
    if any(token in name for token in ("APP_ENV", "OPENAI", "VOYAGE", "BOT_DATA_BASE", "DEBUG_TRACE")):
        return "active_tunable"
    if any(token in name for token in ("PILOT", "EXPERIMENT", "SHADOW", "FEATURE")):
        return "active_tunable"
    if "runtime_config.py" in joined:
        return "active_tunable"
    return "frozen_default_only"


def _build_prd_index_lookup(repo_root: Path) -> str:
    path = repo_root / "docs" / "PRD_INDEX.md"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def build_env_flag_inventory(repo_root: Path) -> list[dict[str, Any]]:
    flags = _extract_env_calls(
        repo_root,
        ["bot_psychologist/bot_agent", "bot_psychologist/api"],
    )
    prd_index = _build_prd_index_lookup(repo_root)
    inventory: list[dict[str, Any]] = []
    for name, record in sorted(flags.items()):
        read_entries = sorted(record["read_in_files"], key=lambda item: (item["path"], item["line"]))
        prd_match = "unknown"
        if name in prd_index:
            for line in prd_index.splitlines():
                if name in line:
                    match = re.search(r"PRD-\d+(?:\.\d+)?(?:-[A-Z0-9]+)?", line)
                    if match:
                        prd_match = match.group(0)
                        break
        inventory.append(
            {
                "flag_name": name,
                "default_value": ", ".join(sorted(record["default_values"])),
                "read_in_files": read_entries,
                "controls_what": _infer_controls(name, read_entries),
                "last_prd_that_introduced_it": prd_match,
                "proposed_status": _propose_flag_status(name, read_entries),
            }
        )
    return inventory


RESPONSIBILITY_MARKERS = {
    "parsing": ("parse", "extract", "normalize", "regex"),
    "validation": ("validate", "validator", "acceptance", "gate", "check"),
    "prompt_assembly": ("prompt", "directive", "contract"),
    "trace_debug": ("trace", "debug", "evidence"),
    "legacy_compat": ("legacy", "compat", "fallback"),
    "retrieval": ("retrieval", "rag", "chroma", "knowledge"),
    "routing": ("route", "router", "endpoint"),
    "streaming": ("stream", "sse", "event"),
    "persistence": ("session", "memory", "store", "history"),
    "admin_runtime": ("admin", "runtime_config", "control"),
    "writer": ("writer", "answer", "llm"),
}


def _detect_responsibilities(text: str, rel_path: str) -> list[str]:
    haystack = f"{rel_path}\n{text}".lower()
    found = [
        name
        for name, markers in RESPONSIBILITY_MARKERS.items()
        if any(marker in haystack for marker in markers)
    ]
    return found or ["general_runtime"]


def build_god_file_inventory(repo_root: Path) -> list[dict[str, Any]]:
    targets = [
        repo_root / "bot_psychologist" / "bot_agent" / "multiagent",
        repo_root / "bot_psychologist" / "api",
    ]
    inventory: list[dict[str, Any]] = []
    for root in targets:
        for path in _iter_python_files(root):
            rel_path = path.relative_to(repo_root).as_posix()
            text = path.read_text(encoding="utf-8", errors="ignore")
            line_count = len(text.splitlines())
            if line_count <= 500:
                continue
            responsibilities = _detect_responsibilities(text, rel_path)
            legacy_marker_count = len(re.findall(r"legacy", text, flags=re.IGNORECASE))
            split_candidate = "yes" if line_count >= 800 or len(responsibilities) >= 4 else "no"
            if "writer_agent.py" in rel_path:
                boundary = "extract prompt/context shaping, final answer validation, and trace packing into dedicated modules"
            elif "admin_routes.py" in rel_path:
                boundary = "split admin runtime/config/read-only debug endpoints into separate routers"
            elif "writer_contract.py" in rel_path:
                boundary = "split schema definitions from prompt serialization and trace helpers"
            elif "memory_retrieval.py" in rel_path:
                boundary = "split retrieval query planning, raw-hit normalization, and source-proof trace"
            elif "runtime_config.py" in rel_path:
                boundary = "split env parsing from effective runtime registry"
            else:
                boundary = "split by dominant responsibility groups listed in inventory"
            inventory.append(
                {
                    "file_path": rel_path,
                    "line_count": line_count,
                    "number_of_distinct_responsibilities": len(responsibilities),
                    "responsibilities": responsibilities,
                    "legacy_marker_count": legacy_marker_count,
                    "split_candidate": split_candidate,
                    "proposed_split_boundary": boundary,
                }
            )
    return sorted(inventory, key=lambda item: (-item["line_count"], item["file_path"]))


def _read_reference_docs(repo_root: Path) -> str:
    chunks: list[str] = []
    for rel in REFERENCE_DOCS:
        path = repo_root / rel
        if path.exists():
            chunks.append(path.read_text(encoding="utf-8", errors="ignore"))
    return "\n".join(chunks)


def _is_referenced_by_name(rel_path: str, reference_text: str) -> bool:
    return rel_path in reference_text or rel_path.replace("/", "\\") in reference_text


def classify_log_file(rel_path: str, size_bytes: int, referenced_by_name: bool = False) -> str:
    normalized = rel_path.replace("\\", "/")
    name = Path(normalized).name.lower()
    suffix = Path(normalized).suffix.lower()
    if referenced_by_name:
        return "evidence_of_record"
    if suffix == ".md":
        return "evidence_of_record"
    if "/live_turn_exports/" in normalized or "/prompt_canvases/" in normalized or "/raw/" in normalized:
        return "raw_artifact"
    if "/screenshots/" in normalized or suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return "raw_artifact"
    if suffix in {".log", ".jsonl", ".ndjson"}:
        return "raw_artifact"
    if suffix == ".json" and (
        size_bytes > 100_000
        or any(token in name for token in ("raw", "live_quality", "trace_dump", "prompt_canvas"))
    ):
        return "raw_artifact"
    if suffix in {".json", ".txt"} and size_bytes <= 100_000:
        return "light_evidence_keep"
    return "review_needed"


def build_logs_tracking_manifest(repo_root: Path) -> dict[str, Any]:
    reference_text = _read_reference_docs(repo_root)
    files = _git_ls_files(repo_root, "TO_DO_LIST/logs")
    entries: list[dict[str, Any]] = []
    summary: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "bytes": 0})
    for rel_path in files:
        path = repo_root / rel_path
        size = path.stat().st_size if path.exists() else 0
        referenced = _is_referenced_by_name(rel_path, reference_text)
        tier = classify_log_file(rel_path, size, referenced)
        entries.append(
            {
                "path": rel_path,
                "size_bytes": size,
                "tier": tier,
                "referenced_by_name": referenced,
            }
        )
        summary[tier]["count"] += 1
        summary[tier]["bytes"] += size
    return {
        "summary": dict(sorted(summary.items())),
        "entries": sorted(entries, key=lambda item: (item["tier"], item["path"])),
    }


def build_git_hygiene_manifest(repo_root: Path, logs_manifest: dict[str, Any]) -> dict[str, Any]:
    branches: list[dict[str, Any]] = []
    for branch in BRANCH_CANDIDATES:
        remote_ref = f"origin/{branch}"
        rev_parse = _run_git(repo_root, ["rev-parse", "--verify", remote_ref])
        exists = rev_parse.returncode == 0
        last_commit = rev_parse.stdout.strip()[:12] if exists else "missing"
        ahead = _git_lines(repo_root, ["log", f"main..{remote_ref}", "--oneline"]) if exists else []
        branches.append(
            {
                "branch": branch,
                "remote_ref": remote_ref,
                "exists": exists,
                "last_commit": last_commit,
                "unique_commits_ahead_of_main": len(ahead),
                "safe_to_delete": bool(exists and not ahead),
                "ahead_preview": ahead[:20],
            }
        )

    backups = _git_ls_files(repo_root, "TO_DO_LIST/backups")
    raw_entries = [entry for entry in logs_manifest["entries"] if entry["tier"] == "raw_artifact"]
    return {
        "branches": branches,
        "tracked_backups": {
            "count": len(backups),
            "paths": backups,
        },
        "raw_log_untrack_candidates": {
            "count": len(raw_entries),
            "size_bytes": sum(entry["size_bytes"] for entry in raw_entries),
            "paths": [entry["path"] for entry in raw_entries],
        },
        "allowed_actions": [
            "delete safe fully merged remote branches",
            "git rm -r --cached TO_DO_LIST/backups",
            "add TO_DO_LIST/backups/ and TO_DO_LIST/logs/*/raw/ ignore rules",
            "quarantine one dead regression test",
            "raw log untrack only from manifest and only when explicitly approved",
        ],
    }


def _format_bytes(value: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.1f} {unit}" if unit != "B" else f"{int(amount)} B"
        amount /= 1024
    return f"{value} B"


def write_legacy_reports(out_dir: Path, inventory: list[dict[str, Any]]) -> None:
    _write_json(
        out_dir / "legacy_dead_code_inventory.json",
        {"schema_version": SCHEMA_VERSION, "items": inventory},
    )
    rows = []
    for item in inventory:
        rows.append(
            [
                item["component_id"],
                item["kind"],
                item["import_graph_status"],
                item["reference_counts"]["active_runtime"],
                item["reference_counts"]["test"],
                item["reference_counts"]["docs_or_logs"],
                item["proposed_classification"],
            ]
        )
    body = [
        f"# {PRD_ID} Legacy Dead-Code Inventory",
        "",
        _markdown_table(
            [
                "Component",
                "Kind",
                "Import graph status",
                "Active refs",
                "Test refs",
                "Docs/log refs",
                "Classification",
            ],
            rows,
        ),
        "",
        "## Evidence Notes",
        "- `dead_confirmed` here means no active runtime-path reference was found by git-grep.",
        "- This PRD does not delete any active runtime modules; removal candidates move to PRD-047.40.",
    ]
    _write_text(out_dir / "legacy_dead_code_inventory.md", "\n".join(body))


def write_env_report(out_dir: Path, inventory: list[dict[str, Any]]) -> None:
    rows = []
    for item in inventory:
        files = ", ".join(
            f"{entry['path']}:{entry['line']}" for entry in item["read_in_files"][:4]
        )
        if len(item["read_in_files"]) > 4:
            files += f" (+{len(item['read_in_files']) - 4})"
        rows.append(
            [
                item["flag_name"],
                item["default_value"],
                files,
                item["controls_what"],
                item["last_prd_that_introduced_it"],
                item["proposed_status"],
            ]
        )
    body = [
        f"# {PRD_ID} Env / Flag Inventory",
        "",
        f"- flag_count: `{len(inventory)}`",
        "",
        _markdown_table(
            ["Flag", "Default", "Read in files", "Controls", "PRD hint", "Proposed status"],
            rows,
        ),
        "",
        "## Classification Policy",
        "- `active_tunable`: still a real operational/configuration surface.",
        "- `frozen_default_only`: candidate for PRD-047.41 effective-config consolidation.",
        "- `retirement_candidate`: legacy/SD/user-level naming that needs separate proof before removal.",
    ]
    _write_text(out_dir / "env_flag_inventory.md", "\n".join(body))


def write_god_file_report(out_dir: Path, inventory: list[dict[str, Any]]) -> None:
    rows = [
        [
            item["file_path"],
            item["line_count"],
            item["number_of_distinct_responsibilities"],
            ", ".join(item["responsibilities"]),
            item["legacy_marker_count"],
            item["split_candidate"],
            item["proposed_split_boundary"],
        ]
        for item in inventory
    ]
    body = [
        f"# {PRD_ID} God-File Inventory",
        "",
        f"- files_over_500_lines: `{len(inventory)}`",
        "",
        _markdown_table(
            [
                "File",
                "Lines",
                "Responsibilities",
                "Responsibility labels",
                "legacy count",
                "Split candidate",
                "Proposed boundary",
            ],
            rows,
        ),
        "",
        "No file is split in PRD-047.39. Candidates are roadmap inputs for PRD-047.42.",
    ]
    _write_text(out_dir / "god_file_inventory.md", "\n".join(body))


def write_logs_manifest_report(out_dir: Path, manifest: dict[str, Any]) -> None:
    summary_rows = [
        [tier, data["count"], _format_bytes(data["bytes"])]
        for tier, data in sorted(manifest["summary"].items())
    ]
    raw_paths = [entry["path"] for entry in manifest["entries"] if entry["tier"] == "raw_artifact"]
    body = [
        f"# {PRD_ID} Logs Tracking Manifest",
        "",
        _markdown_table(["Tier", "Count", "Size"], summary_rows),
        "",
        "## Policy",
        "- `*.md` and files referenced by name in state/index/decisions/roadmap stay tracked.",
        "- Raw artifact candidates are listed for manifest-first untracking only; markdown evidence is excluded.",
        "- Forward-looking policy: from PRD-047.40 onward, raw artifacts should go under `TO_DO_LIST/logs/PRD-XXX/raw/`.",
        "",
        "## Raw Artifact Candidate Paths",
        "```text",
        *raw_paths,
        "```",
    ]
    _write_text(out_dir / "logs_tracking_manifest.md", "\n".join(body))


def write_git_hygiene_report(out_dir: Path, manifest: dict[str, Any]) -> None:
    branch_rows = [
        [
            item["branch"],
            item["exists"],
            item["last_commit"],
            item["unique_commits_ahead_of_main"],
            item["safe_to_delete"],
        ]
        for item in manifest["branches"]
    ]
    body = [
        f"# {PRD_ID} Git Hygiene Actions Manifest",
        "",
        "## Remote Branch Proof",
        _markdown_table(
            ["Branch", "Exists", "Last commit", "Ahead of main", "Safe to delete"],
            branch_rows,
        ),
        "",
        "## Backups",
        f"- tracked_paths_count: `{manifest['tracked_backups']['count']}`",
        "- action: `git rm -r --cached TO_DO_LIST/backups` and keep files locally ignored.",
        "",
        "## Raw Logs",
        f"- raw_artifact_candidate_count: `{manifest['raw_log_untrack_candidates']['count']}`",
        f"- raw_artifact_candidate_size: `{_format_bytes(manifest['raw_log_untrack_candidates']['size_bytes'])}`",
        "- action in this PRD: manifest produced; untrack only if explicitly approved and still auditable.",
        "",
        "## Exact Backups Paths",
        "```text",
        *manifest["tracked_backups"]["paths"],
        "```",
        "",
        "## Exact Raw Log Candidate Paths",
        "```text",
        *manifest["raw_log_untrack_candidates"]["paths"],
        "```",
    ]
    _write_text(out_dir / "git_hygiene_actions_manifest.md", "\n".join(body))


def write_static_reports(out_dir: Path) -> None:
    _write_text(
        out_dir / "source_gate.md",
        "\n".join(
            [
                f"# {PRD_ID} Source Gate",
                "",
                "- Read PRD-047.39.",
                "- Read PRD-047.38 project state.",
                "- Read current startup protocol.",
                "- Scope confirmed: inventory and non-runtime git hygiene only.",
                "- S7 panic warning is backlog only and is not repaired in this PRD.",
            ]
        ),
    )
    _write_text(
        out_dir / "no_mutation_proof.md",
        "\n".join(
            [
                f"# {PRD_ID} No-Mutation Proof",
                "",
                "- Active runtime code under `bot_agent/`, `api/`, and `web_ui/src/` is not changed by inventory generation.",
                "- Writer prompt, retrieval ranking, safety logic, DB/Chroma/registry/processed blocks/source documents are not changed.",
                "- Git hygiene is limited to branch cleanup, cached backup removal, ignore rules, and dead-test quarantine.",
                "- `TO_DO_LIST/logs/*.md` evidence reports remain tracked.",
                "- No git history rewrite, no reindex, no provider payload, no raw private chat log commit.",
            ]
        ),
    )
    _write_text(
        out_dir / "consolidation_roadmap_047_40_plus.md",
        "\n".join(
            [
                f"# {PRD_ID} Consolidation Roadmap PRD-047.40+",
                "",
                "## PRD-047.40 - Dead Pipeline Removal",
                "- Remove only inventory-proven `dead_confirmed` retired pipelines/prompts.",
                "- Gate: full regression plus live smoke; no behavior drift.",
                "",
                "## PRD-047.41 - Flag Consolidation",
                "- Move env sprawl into one effective-config registry.",
                "- Gate: admin runtime effective values before/after match.",
                "",
                "## PRD-047.42 - God-File Decomposition",
                "- Split writer/admin/contract/retrieval/config god-files by responsibility.",
                "- Gate: contract tests and behavior diff proof.",
                "",
                "## PRD-047.43 - Admin UI Dedup",
                "- Remove compatibility-only duplicate admin controls.",
                "- Gate: browser proof that remaining UI covers real use cases.",
                "",
                "## Safety Polish Backlog",
                "- S7 `panic_medical_escalation_boundary_soft` from PRD-047.38 stays backlog.",
                "- Do not repair it inside architecture consolidation inventory.",
            ]
        ),
    )
    _write_text(
        out_dir / "next_recommendation.md",
        "\n".join(
            [
                "# Architect Decision Recommendation",
                "",
                "Status: ACCEPTED_WITH_WARNINGS candidate until hygiene/test results are recorded",
                "",
                "Why:",
                "- PRD-047.39 is an inventory-first consolidation entry.",
                "- Runtime behavior is intentionally untouched.",
                "",
                "Recommended next PRD:",
                "- PRD-047.40 Dead Pipeline Removal, only for `dead_confirmed` candidates.",
            ]
        ),
    )


def write_all_reports(repo_root: Path) -> dict[str, Any]:
    out_dir = repo_root / "TO_DO_LIST" / "logs" / PRD_ID
    legacy = build_legacy_dead_code_inventory(repo_root)
    env_flags = build_env_flag_inventory(repo_root)
    god_files = build_god_file_inventory(repo_root)
    logs_manifest = build_logs_tracking_manifest(repo_root)
    git_hygiene = build_git_hygiene_manifest(repo_root, logs_manifest)

    write_legacy_reports(out_dir, legacy)
    write_env_report(out_dir, env_flags)
    write_god_file_report(out_dir, god_files)
    write_logs_manifest_report(out_dir, logs_manifest)
    write_git_hygiene_report(out_dir, git_hygiene)
    write_static_reports(out_dir)

    summary = {
        "schema_version": SCHEMA_VERSION,
        "legacy_items": len(legacy),
        "env_flags": len(env_flags),
        "god_files": len(god_files),
        "logs_summary": logs_manifest["summary"],
        "safe_branch_delete_candidates": [
            item["branch"] for item in git_hygiene["branches"] if item["safe_to_delete"]
        ],
        "tracked_backups_count": git_hygiene["tracked_backups"]["count"],
        "raw_log_candidate_count": git_hygiene["raw_log_untrack_candidates"]["count"],
    }
    _write_json(out_dir / "architecture_inventory_summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PRD-047.39 architecture inventory reports.")
    parser.add_argument("--repo-root", type=Path, default=_repo_root_from_file())
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    summary = write_all_reports(repo_root)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
