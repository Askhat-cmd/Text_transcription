from __future__ import annotations

import argparse
import difflib
import json
import os
import subprocess
import urllib.request
from pathlib import Path
from typing import Any


PRD_ID = "PRD-047.41"
REPO_ROOT = Path(__file__).resolve().parents[2]
BOT_ROOT = REPO_ROOT / "bot_psychologist"
if str(BOT_ROOT) not in os.sys.path:
    os.sys.path.insert(0, str(BOT_ROOT))

from bot_agent.effective_config_registry import (  # noqa: E402
    FLAG_REGISTRY,
    FROZEN_CONSTANT_FLAGS,
    RECLASSIFIED_ACTIVE_FLAGS,
    SECRET_FLAGS,
    build_effective_config_payload,
    get_admin_hot_editable_env_flags,
)


OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
ADMIN_EFFECTIVE_URL = "http://127.0.0.1:8001/api/admin/runtime/effective"
ADMIN_HEADERS = {"X-API-Key": "dev-key-001"}
KNOWN_BUCKET_A_PATHS = {
    "AUTHOR_BLEND_MODE": ["bot_psychologist/bot_agent/config.py"],
    "BOT_DB_PATH": ["bot_psychologist/bot_agent/config.py"],
    "DATA_ROOT": ["bot_psychologist/bot_agent/config.py"],
    "DEBUG": ["bot_psychologist/bot_agent/config.py"],
    "DIAGNOSTIC_CENTER_CREATOR_USER_ID": [
        "bot_psychologist/bot_agent/diagnostic_center_control.py",
        "bot_psychologist/bot_agent/multiagent/diagnostic_center_creator_live_activation.py",
    ],
    "DIAGNOSTIC_CENTER_DEVELOPER_USER_IDS": ["bot_psychologist/bot_agent/diagnostic_center_control.py"],
    "EMBEDDING_DEVICE": ["bot_psychologist/bot_agent/config.py"],
    "EMBEDDING_MODEL": ["bot_psychologist/bot_agent/config.py"],
    "MULTIAGENT_ENABLED": ["bot_psychologist/api/admin_routes.py"],
    "NEO_MINDBOT_ENABLED": ["bot_psychologist/api/admin_routes.py"],
    "PRIMARY_MODEL": ["bot_psychologist/bot_agent/config.py"],
    "PROMPT_MODE_OVERRIDES_SD": ["bot_psychologist/bot_agent/config.py"],
    "RECENT_WINDOW": ["bot_psychologist/bot_agent/config.py"],
    "RERANKER_BLOCK_THRESHOLD": ["bot_psychologist/bot_agent/config.py"],
    "RERANKER_CONFIDENCE_THRESHOLD": ["bot_psychologist/bot_agent/config.py"],
    "RERANKER_ENABLED": ["bot_psychologist/bot_agent/config.py"],
    "RERANKER_MODE_WHITELIST": ["bot_psychologist/bot_agent/config.py"],
    "SUMMARIZER_FALLBACK_ON_EMPTY": ["bot_psychologist/bot_agent/config.py"],
    "SUMMARIZER_FALLBACK_RETRIES": ["bot_psychologist/bot_agent/config.py"],
    "SUMMARIZER_MIN_TURNS": ["bot_psychologist/bot_agent/config.py"],
    "SUMMARIZER_MODEL": ["bot_psychologist/bot_agent/config.py"],
    "SUMMARIZER_REASONING_EFFORT": ["bot_psychologist/bot_agent/config.py"],
    "SUMMARY_WINDOW_SIZE": ["bot_psychologist/bot_agent/config.py"],
    "TELEGRAM_ALLOWED_UPDATES": ["bot_psychologist/api/telegram_adapter/config.py"],
    "TELEGRAM_ENABLED": ["bot_psychologist/api/telegram_adapter/config.py"],
    "TELEGRAM_MODE": ["bot_psychologist/api/telegram_adapter/config.py"],
    "TELEGRAM_POLLING_MAX_RETRY_DELAY": ["bot_psychologist/api/telegram_adapter/config.py"],
    "TELEGRAM_POLLING_RETRY_DELAY": ["bot_psychologist/api/telegram_adapter/config.py"],
    "TELEGRAM_POLLING_TIMEOUT": ["bot_psychologist/api/telegram_adapter/config.py"],
    "TELEGRAM_WEBHOOK_URL": ["bot_psychologist/api/telegram_adapter/config.py"],
    "THREAD_STORAGE_DIR": ["bot_psychologist/api/admin_routes.py"],
    "TURN_LLM_SUMMARY_DEBUG_PREVIEW_CHARS": ["bot_psychologist/bot_agent/config.py"],
    "TURN_LLM_SUMMARY_ENABLED": ["bot_psychologist/bot_agent/config.py"],
    "TURN_LLM_SUMMARY_MAX_INPUT_CHARS": ["bot_psychologist/bot_agent/config.py"],
    "TURN_LLM_SUMMARY_MAX_PENDING_PER_RUN": ["bot_psychologist/bot_agent/config.py"],
    "TURN_LLM_SUMMARY_MAX_RETRIES": ["bot_psychologist/bot_agent/config.py"],
    "TURN_LLM_SUMMARY_MAX_SUMMARY_CHARS": ["bot_psychologist/bot_agent/config.py"],
    "TURN_LLM_SUMMARY_MODEL": ["bot_psychologist/bot_agent/config.py"],
    "TURN_LLM_SUMMARY_PROVIDER": ["bot_psychologist/bot_agent/config.py"],
    "TURN_LLM_SUMMARY_TIMEOUT_SECONDS": ["bot_psychologist/bot_agent/config.py"],
    "TURN_LLM_SUMMARY_USE_IN_CONTEXT": ["bot_psychologist/bot_agent/config.py"],
}


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _run_git_grep(pattern: str) -> list[str]:
    result = subprocess.run(
        ["git", "grep", "-n", "-I", "-F", "--", pattern],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode not in (0, 1):
        return []
    return [line for line in result.stdout.splitlines() if line.strip()]


def _markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        cells = [str(value).replace("|", "\\|").replace("\n", "<br>") for value in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _fetch_live_effective_payload() -> dict[str, Any]:
    request = urllib.request.Request(ADMIN_EFFECTIVE_URL, headers=ADMIN_HEADERS)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _registry_snapshot_report() -> None:
    payload = build_effective_config_payload()
    rows: list[list[Any]] = []
    for name, entry in payload["entries"].items():
        current_value = entry["current_value"]
        if isinstance(current_value, dict):
            current_value_text = json.dumps(current_value, ensure_ascii=False)
        else:
            current_value_text = str(current_value)
        rows.append(
            [
                name,
                entry["status"],
                entry["source"],
                entry["admin_hot_editable"],
                current_value_text[:120],
                entry["notes"],
            ]
        )
    body = [
        f"# {PRD_ID} Effective Config Registry Snapshot",
        "",
        f"- flag_count: `{payload['flag_count']}`",
        f"- admin_hot_editable_count: `{payload['admin_hot_editable_count']}`",
        f"- editable_env_intersection_count: `{payload['editable_config_env_intersection_count']}`",
        f"- editable_non_env_keys: `{payload['editable_config_non_env_keys']}`",
        "",
        "## Status Counts",
        _markdown_table(
            ["Status", "Count"],
            [[status, count] for status, count in payload["status_counts"].items()],
        ),
        "",
        "## Registry Entries",
        _markdown_table(
            ["Flag", "Status", "Source", "Admin hot-editable", "Current value", "Notes"],
            rows,
        ),
    ]
    _write_text(OUT_DIR / "effective_config_registry_snapshot.md", "\n".join(body))


def _bucket_a_report() -> None:
    rows: list[list[Any]] = []
    for name in FROZEN_CONSTANT_FLAGS:
        getattr_hits = _run_git_grep(f'getattr(config, "{name}"') + _run_git_grep(
            f"getattr(config, '{name}'"
        )
        env_read_hits = _run_git_grep(f'os.getenv("{name}"') + _run_git_grep(
            f"os.getenv('{name}'"
        )
        known_paths = set(KNOWN_BUCKET_A_PATHS.get(name, []))
        remaining_env_reads = [
            hit
            for hit in env_read_hits
            if hit.split(":", 1)[0].replace("\\", "/") not in known_paths
        ]
        rows.append(
            [
                name,
                ", ".join(KNOWN_BUCKET_A_PATHS.get(name, [])),
                len(getattr_hits),
                "<br>".join(getattr_hits[:4]) or "none",
                len(remaining_env_reads),
                "<br>".join(remaining_env_reads[:4]) or "none",
            ]
        )
    body = [
        f"# {PRD_ID} Bucket A Constant Conversion Report",
        "",
        f"- converted_flags: `{len(FROZEN_CONSTANT_FLAGS)}`",
        "- audit_rule: git-grep only for `getattr(config, FLAG)` and residual `os.getenv(FLAG)`.",
        "- interpretation: `Remaining env reads` must stay zero outside declared conversion sites.",
        "",
        _markdown_table(
            [
                "Flag",
                "Known conversion paths",
                "getattr(config, FLAG) hits",
                "getattr preview",
                "Remaining env reads",
                "env read preview",
            ],
            rows,
        ),
    ]
    _write_text(OUT_DIR / "bucket_a_constant_conversion_report.md", "\n".join(body))


def _secret_proof_report(live_payload: dict[str, Any]) -> None:
    entries = live_payload.get("effective_config", {}).get("entries", {})
    rows: list[list[Any]] = []
    for name in SECRET_FLAGS:
        entry = entries.get(name, {})
        rows.append(
            [
                name,
                entry.get("status"),
                json.dumps(entry.get("current_value"), ensure_ascii=False),
                entry.get("source"),
            ]
        )
    body = [
        f"# {PRD_ID} Secret Flag Exposure Proof",
        "",
        "- covered payloads: `/api/admin/runtime/effective` live payload plus contract tests",
        "- contract tests: `tests/contract/test_effective_config_registry_v1041.py`",
        "- requirement: secret entries expose only `{\"is_set\": bool}` as `current_value`.",
        "",
        _markdown_table(
            ["Flag", "Status", "current_value", "Source"],
            rows,
        ),
    ]
    _write_text(OUT_DIR / "secret_flag_exposure_proof.md", "\n".join(body))


def _normalize_payload_for_diff(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = json.loads(json.dumps(payload))
    normalized.pop("effective_config", None)
    trace = normalized.get("trace", {})
    runtime_trace = trace.get("runtime_config_trace", {}) if isinstance(trace, dict) else {}
    if isinstance(runtime_trace, dict):
        runtime_trace.pop("backend_pid", None)
        runtime_trace.pop("backend_start_time", None)
    planner_guard = normalized.get("planner_drift_guard", {})
    if isinstance(planner_guard, dict):
        planner_guard.pop("last_summary", None)
        planner_guard.pop("last_replay_status", None)
    return normalized


def _admin_runtime_diff_report(before_path: Path, after_path: Path) -> None:
    before_payload = _load_json(before_path)
    after_payload = _load_json(after_path)
    before_without_registry = _normalize_payload_for_diff(before_payload)
    after_without_registry = _normalize_payload_for_diff(after_payload)
    stable_equal = before_without_registry == after_without_registry

    before_text = json.dumps(before_without_registry, ensure_ascii=False, indent=2, sort_keys=True)
    after_text = json.dumps(after_without_registry, ensure_ascii=False, indent=2, sort_keys=True)
    diff_lines = list(
        difflib.unified_diff(
            before_text.splitlines(),
            after_text.splitlines(),
            fromfile="before_without_effective_config",
            tofile="after_without_effective_config",
            lineterm="",
        )
    )
    effective_config = after_payload.get("effective_config", {})
    constant_rows = []
    for name in FROZEN_CONSTANT_FLAGS:
        entry = effective_config.get("entries", {}).get(name, {})
        constant_rows.append([name, entry.get("source"), entry.get("status")])

    body = [
        f"# {PRD_ID} Admin Runtime Diff Before / After",
        "",
        f"- stable_payload_without_effective_config_equal: `{stable_equal}`",
        f"- new_registry_schema_version: `{effective_config.get('schema_version')}`",
        f"- reclassified_active_count: `{len(RECLASSIFIED_ACTIVE_FLAGS)}`",
        f"- env_hot_editable_count: `{len(get_admin_hot_editable_env_flags())}`",
        "",
        "## Bucket A Source Labels",
        _markdown_table(["Flag", "Source after", "Status after"], constant_rows),
        "",
        "## Diff Without effective_config",
        "```diff",
        *(diff_lines[:400] or ["<no diff>"]),
        "```",
    ]
    _write_text(OUT_DIR / "admin_runtime_diff_before_after.md", "\n".join(body))


def _owner_pending_report() -> None:
    body = [
        f"# {PRD_ID} Owner Decision Pending",
        "",
        "- bucket B: resolved by owner decision (a) on 2026-07-09 and fully applied.",
        "- remaining deferred flag: `LEGACY_PIPELINE_ENABLED`.",
        "- rationale: keep current deprecation warning behavior until dedicated admin/UI cleanup PRD.",
    ]
    _write_text(OUT_DIR / "owner_decision_pending.md", "\n".join(body))


def _next_recommendation_report() -> None:
    body = [
        f"# {PRD_ID} Next Recommendation",
        "",
        "- Keep `LEGACY_PIPELINE_ENABLED` diagnostic-only behavior until the dedicated admin dedup / compatibility cleanup PRD.",
        "- After that, the next safe consolidation target is the non-env `EDITABLE_CONFIG` subset (`LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `TOP_K_BLOCKS`, `ENABLE_CACHING`).",
        "- Master-plan follow-up: proceed with god-file decomposition only after this registry becomes the documented source of truth in project docs.",
    ]
    _write_text(OUT_DIR / "next_recommendation.md", "\n".join(body))


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate PRD-047.41 flag consolidation reports.")
    parser.add_argument("--before-json", type=Path, required=True)
    parser.add_argument("--after-json", type=Path, required=True)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    live_payload = _fetch_live_effective_payload()
    _write_json(args.after_json, live_payload)
    _registry_snapshot_report()
    _bucket_a_report()
    _secret_proof_report(live_payload)
    _admin_runtime_diff_report(args.before_json, args.after_json)
    _owner_pending_report()
    _next_recommendation_report()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
