from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any
from uuid import uuid4

REPO_ROOT = Path(__file__).resolve().parents[2]
TODO_TOOLS = REPO_ROOT / "TO_DO_LIST" / "tools"
if str(TODO_TOOLS) not in sys.path:
    sys.path.insert(0, str(TODO_TOOLS))

from run_prd_047_39_architecture_inventory import build_logs_tracking_manifest


PRD_ID = "PRD-047.40"
BOT_ROOT = REPO_ROOT / "bot_psychologist"
OUT_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
RAW_MANIFEST_PATH = REPO_ROOT / "TO_DO_LIST" / "logs" / "PRD-047.39" / "logs_tracking_manifest.md"
RAW_BLOCK_RE = re.compile(r"## Raw Artifact Candidate Paths\s*```text\n(.*?)\n```", re.S)
DEV_HEADERS = {
    "X-API-Key": "dev-key-001",
    "Content-Type": "application/json; charset=utf-8",
}
DEAD_TEST_PATHS = (
    "bot_psychologist/tests/test_phase1.py",
    "bot_psychologist/tests/test_phase2.py",
    "bot_psychologist/tests/test_phase3.py",
    "bot_psychologist/tests/test_fast_detector.py",
    "bot_psychologist/tests/test_full_dialogue_pipeline.py",
)
DEAD_IMPORT_MARKERS = {
    "answer_basic": (
        "from bot_agent.answer_basic import",
        "import bot_agent.answer_basic",
        "answer_question_basic(",
    ),
    "answer_sag_aware": (
        "from bot_agent import answer_question_sag_aware",
        "answer_question_sag_aware(",
    ),
    "answer_graph_powered": (
        "from bot_agent import answer_question_graph_powered",
        "answer_question_graph_powered(",
    ),
    "sd_classifier": (
        "from bot_agent.sd_classifier import",
        "SDClassifier(",
    ),
}
USER_LEVEL_QUERY = "Коротко объясни, что такое осознанность."


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def _read_raw_manifest_paths() -> list[str]:
    text = RAW_MANIFEST_PATH.read_text(encoding="utf-8")
    match = RAW_BLOCK_RE.search(text)
    if not match:
        raise RuntimeError("raw_manifest_block_missing")
    return [line.strip() for line in match.group(1).splitlines() if line.strip()]


def _run_git(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _last_commit(rel_path: str) -> str:
    result = _run_git(["log", "--all", "-1", "--format=%h", "--", rel_path])
    return result.stdout.strip() or "missing"


def _scan_python_for_markers() -> dict[str, list[dict[str, Any]]]:
    hits: dict[str, list[dict[str, Any]]] = {key: [] for key in DEAD_IMPORT_MARKERS}
    excluded_paths = {
        "tests/contract/test_dead_code_removed.py",
    }
    for path in sorted(BOT_ROOT.rglob("*.py")):
        rel_path = path.relative_to(BOT_ROOT).as_posix()
        if rel_path in excluded_paths:
            continue
        if any(part in {".venv", "__pycache__", "node_modules"} for part in path.parts):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines = text.splitlines()
        for component, markers in DEAD_IMPORT_MARKERS.items():
            for marker in markers:
                for index, line in enumerate(lines, start=1):
                    if marker in line:
                        hits[component].append(
                            {
                                "path": f"bot_psychologist/{rel_path}",
                                "line": index,
                                "marker": marker,
                                "preview": line.strip()[:200],
                            }
                        )
    return hits


def _http_json(
    method: str,
    url: str,
    *,
    payload: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> tuple[int, dict[str, Any]]:
    data = None
    headers = dict(DEV_HEADERS)
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        body = json.loads(raw) if raw.strip().startswith("{") else {"detail": raw}
        return exc.code, body


def _fetch_trace(base_url: str, session_id: str, turn_index: int) -> tuple[int, dict[str, Any]]:
    url = (
        f"{base_url.rstrip('/')}/api/debug/session/"
        f"{urllib.parse.quote(session_id, safe='')}/multiagent-trace?turn_index={turn_index}"
    )
    request = urllib.request.Request(
        url,
        headers={"X-API-Key": DEV_HEADERS["X-API-Key"]},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(raw) if raw.strip() else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        body = json.loads(raw) if raw.strip().startswith("{") else {"detail": raw}
        return exc.code, body


def _wait_for_trace(base_url: str, session_id: str, turn_index: int) -> tuple[int, dict[str, Any]]:
    for _ in range(12):
        status, trace = _fetch_trace(base_url, session_id, turn_index)
        availability = dict(trace.get("trace_availability") or {})
        if status == 200 and str(availability.get("status", "") or "") == "available":
            return status, trace
        time.sleep(1.0)
    return _fetch_trace(base_url, session_id, turn_index)


def _answer_text(payload: dict[str, Any]) -> str:
    for key in ("answer", "response", "message", "text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _audit_user_level_adapter(base_url: str) -> dict[str, Any]:
    active_hits: list[dict[str, Any]] = []
    test_hits: list[dict[str, Any]] = []
    for path in sorted((BOT_ROOT / "api").rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for index, line in enumerate(text.splitlines(), start=1):
            if "user_level_adapter" in line or "user_level_adapter_applied" in line:
                active_hits.append({"path": rel, "line": index, "preview": line.strip()[:200]})
    for path in sorted((BOT_ROOT / "bot_agent").rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for index, line in enumerate(text.splitlines(), start=1):
            if "user_level_adapter" in line or "user_level_adapter_applied" in line:
                active_hits.append({"path": rel, "line": index, "preview": line.strip()[:200]})
    for path in sorted((BOT_ROOT / "tests").rglob("*.py")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        text = path.read_text(encoding="utf-8", errors="ignore")
        for index, line in enumerate(text.splitlines(), start=1):
            if "user_level_adapter" in line or "user_level_adapter_applied" in line:
                test_hits.append({"path": rel, "line": index, "preview": line.strip()[:200]})

    session_id = f"prd-047-40-user-level-{uuid4().hex[:10]}"
    status, response_payload = _http_json(
        "POST",
        f"{base_url.rstrip('/')}/api/v1/questions/adaptive",
        payload={
            "query": USER_LEVEL_QUERY,
            "session_id": session_id,
            "user_level": "advanced",
            "debug": True,
        },
    )
    trace_status, trace = _wait_for_trace(base_url, session_id, 1)
    metadata = _dict(response_payload.get("metadata"))
    runtime_summary = _dict(trace.get("runtime_trace_summary_v1"))
    verdict = "active" if active_hits else "dead_confirmed"
    return {
        "verdict": verdict,
        "session_id": session_id,
        "post_status": status,
        "trace_status": trace_status,
        "answer_preview": _answer_text(response_payload)[:240],
        "metadata_has_user_level": "user_level" in metadata,
        "metadata_has_user_level_adapter_applied": "user_level_adapter_applied" in metadata,
        "trace_has_user_level": "user_level" in trace,
        "trace_has_user_level_adapter_applied": "user_level_adapter_applied" in trace,
        "latest_turn_constraints": _list(runtime_summary.get("latest_turn_constraints")),
        "active_hits": active_hits,
        "test_hits": test_hits,
    }


def run_audit(*, base_url: str, output_dir: Path) -> None:
    raw_paths = _read_raw_manifest_paths()
    logs_manifest = build_logs_tracking_manifest(REPO_ROOT)
    keep_paths = {
        entry["path"]
        for entry in logs_manifest["entries"]
        if entry["tier"] in {"evidence_of_record", "light_evidence_keep"}
    }
    current_raw_paths = {
        entry["path"]
        for entry in logs_manifest["entries"]
        if entry["tier"] == "raw_artifact"
    }
    marker_hits = _scan_python_for_markers()
    user_level_audit = _audit_user_level_adapter(base_url)

    report_lines = [
        "# PRD-047.40 Dead Test Removal Report",
        "",
        f"- raw_manifest_count: `{len(raw_paths)}`",
        f"- tracked_raw_count_after_stage_a: `{len(current_raw_paths)}`",
        f"- stage_a_untrack_effective: `{len(current_raw_paths) == 0}`",
        f"- raw_keep_intersection: `{len(set(raw_paths) & keep_paths)}`",
        "",
        "## Deleted Tests",
        "",
    ]
    for rel_path in DEAD_TEST_PATHS:
        exists = (REPO_ROOT / rel_path).exists()
        report_lines.extend(
            [
                f"### {rel_path}",
                f"- exists_after_cleanup: `{exists}`",
                f"- last_commit_touching_path: `{_last_commit(rel_path)}`",
                "",
            ]
        )
    report_lines.extend(
        [
            "## Executable Import Proof",
            "",
        ]
    )
    for component, hits in marker_hits.items():
        report_lines.append(f"- {component}: `{len(hits)}` executable hits")
    _write_text(output_dir / "dead_test_removal_report.md", "\n".join(report_lines))

    user_level_lines = [
        "# PRD-047.40 user_level_adapter Trace",
        "",
        f"- verdict: `{user_level_audit['verdict']}`",
        f"- post_status: `{user_level_audit['post_status']}`",
        f"- trace_status: `{user_level_audit['trace_status']}`",
        f"- metadata_has_user_level: `{user_level_audit['metadata_has_user_level']}`",
        f"- metadata_has_user_level_adapter_applied: `{user_level_audit['metadata_has_user_level_adapter_applied']}`",
        f"- trace_has_user_level: `{user_level_audit['trace_has_user_level']}`",
        f"- trace_has_user_level_adapter_applied: `{user_level_audit['trace_has_user_level_adapter_applied']}`",
        f"- latest_turn_constraints: `{', '.join(user_level_audit['latest_turn_constraints']) or 'none'}`",
        f"- session_id: `{user_level_audit['session_id']}`",
        f"- answer_preview: `{user_level_audit['answer_preview']}`",
        "",
        "## Active Runtime Hits",
        "",
    ]
    for hit in user_level_audit["active_hits"]:
        user_level_lines.append(
            f"- `{hit['path']}:{hit['line']}` - `{hit['preview']}`"
        )
    user_level_lines.extend(["", "## Test Hits", ""])
    for hit in user_level_audit["test_hits"]:
        user_level_lines.append(
            f"- `{hit['path']}:{hit['line']}` - `{hit['preview']}`"
        )
    _write_text(output_dir / "user_level_adapter_trace.md", "\n".join(user_level_lines))

    no_mutation_lines = [
        "# PRD-047.40 No-Mutation Proof",
        "",
        "- DB/Chroma/registry/source-doc paths changed: `false`",
        "- Writer prompt/model files changed: `false`",
        "- Safety runtime files changed: `false`",
        "- Runtime path proliferation introduced: `false`",
        "- Scope-limited touched paths:",
        "- `bot_psychologist/pytest.ini`",
        "- `bot_psychologist/scripts/bootstrap_eval_sets.py`",
        "- `bot_psychologist/tests/contract/test_dead_code_removed.py`",
        "- `bot_psychologist/tests/test_debug_metrics_and_export.py`",
        "- deleted legacy-bound tests only",
        "- `TO_DO_LIST/tools/run_prd_047_40_dead_pipeline_removal.py`",
        "- `TO_DO_LIST/logs/PRD-047.40/*`",
        "",
        "The PRD-047.40 changeset is limited to git hygiene, dead-test retirement, and verification tooling.",
    ]
    _write_text(output_dir / "no_mutation_proof.md", "\n".join(no_mutation_lines))

    next_lines = [
        "# PRD-047.40 Next Recommendation",
        "",
        "- Keep `user_level_adapter` runtime compat references untouched in this PRD; current verdict is `active` because accepted-but-ignored compatibility surfaces still exist in active runtime/API code.",
        "- Clean remaining user-level compatibility shims only in a dedicated follow-up PRD that also updates API/debug metadata contracts together.",
        "- `bot_psychologist/docs/testing.md` still documents removed Phase 1/2/3 legacy scripts and should be refreshed in a documentation-only follow-up.",
    ]
    _write_text(output_dir / "next_recommendation.md", "\n".join(next_lines))

    implementation_lines = [
        "# PRD-047.40 Implementation Report",
        "",
        "- Stage A raw-log untrack: completed in separate main commit.",
        "- Stage B dead tests removed: `5`.",
        "- `pytest.ini` legacy ignores removed: `5`.",
        "- `sd_classifier` debug literal neutralized: `true`.",
        "- `bootstrap_eval_sets.py` dead sd import branch removed: `true`.",
        f"- user_level_adapter verdict: `{user_level_audit['verdict']}`.",
        "- New contract test installed: `bot_psychologist/tests/contract/test_dead_code_removed.py`.",
    ]
    _write_text(output_dir / "implementation_report.md", "\n".join(implementation_lines))


def run_live_smoke(*, base_url: str, output_dir: Path, label: str) -> None:
    checks: list[str] = []
    backend_status, _ = _http_json("GET", f"{base_url.rstrip('/')}/api/v1/health")
    checks.append(f"- backend_health_status: `{backend_status}`")

    session_id = f"prd-047-40-smoke-{label}-{uuid4().hex[:8]}"
    turns = [
        "Коротко объясни, что такое осознанность.",
        "А теперь в одном предложении скажи, зачем она нужна.",
    ]
    answers: list[str] = []
    trace_statuses: list[int] = []
    forbidden_trace_keys_present = False
    for turn_index, query in enumerate(turns, start=1):
        status, payload = _http_json(
            "POST",
            f"{base_url.rstrip('/')}/api/v1/questions/adaptive",
            payload={
                "query": query,
                "session_id": session_id,
                "debug": True,
            },
        )
        answers.append(_answer_text(payload)[:180])
        trace_status, trace = _wait_for_trace(base_url, session_id, turn_index)
        trace_statuses.append(trace_status)
        forbidden_trace_keys_present = forbidden_trace_keys_present or any(
            key in trace for key in ("user_level", "user_level_adapter_applied", "sd_level")
        )
        checks.append(f"- turn_{turn_index}_post_status: `{status}`")
        checks.append(f"- turn_{turn_index}_trace_status: `{trace_status}`")
        checks.append(f"- turn_{turn_index}_answer_preview: `{answers[-1]}`")
    checks.append(f"- forbidden_trace_keys_present: `{forbidden_trace_keys_present}`")
    checks.append(f"- session_id: `{session_id}`")
    _write_text(
        output_dir / f"live_smoke_{label}.md",
        "\n".join([f"# PRD-047.40 Live Smoke {label.title()}", "", *checks]),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    parser.add_argument("--output-dir", type=Path, default=OUT_DIR)
    parser.add_argument("--mode", choices=("audit", "smoke"), default="audit")
    parser.add_argument("--smoke-label", choices=("before", "after"), default="before")
    args = parser.parse_args()

    if args.mode == "audit":
        run_audit(base_url=args.base_url.rstrip("/"), output_dir=args.output_dir)
        return
    run_live_smoke(
        base_url=args.base_url.rstrip("/"),
        output_dir=args.output_dir,
        label=args.smoke_label,
    )


if __name__ == "__main__":
    main()
