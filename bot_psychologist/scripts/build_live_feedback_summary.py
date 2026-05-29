#!/usr/bin/env python3
"""Build sanitized live feedback summary reports."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.live_testing.feedback_capture import (  # noqa: E402
    get_feedback_reports_dir,
    load_session_payload,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_bool(value: Any) -> bool:
    return bool(value) if value is not None else False


def _recommend_next_action(summary: dict[str, Any]) -> str:
    safety_concern_count = int(summary.get("safety_concern_count", 0) or 0)
    drift_critical_count = int(summary.get("drift_critical_count", 0) or 0)
    too_rigid_count = int(summary.get("too_rigid_count", 0) or 0)
    too_generic_count = int(summary.get("too_generic_count", 0) or 0)
    too_many_questions_count = int(summary.get("too_many_questions_count", 0) or 0)
    too_much_practice_count = int(summary.get("too_much_practice_count", 0) or 0)

    if safety_concern_count > 0 or drift_critical_count > 0:
        return "evaluator_hotfix"
    if too_many_questions_count > 1 or too_much_practice_count > 1:
        return "planner_calibration"
    if too_rigid_count > 1 or too_generic_count > 1:
        return "prompt_tuning"
    if too_rigid_count > 0 or too_generic_count > 0:
        return "live_tone_calibration_prd"
    return "no_op"


def build_summary_payload(session_payload: dict[str, Any]) -> dict[str, Any]:
    records = [item for item in list(session_payload.get("records", []) or []) if isinstance(item, dict)]
    ratings = [
        int(item.get("user_rating"))
        for item in records
        if isinstance(item.get("user_rating"), int)
    ]

    comments = [
        str(item.get("comment", "") or "").strip()
        for item in records
        if str(item.get("comment", "") or "").strip()
    ]

    too_rigid_count = sum(1 for item in records if _safe_bool(item.get("felt_too_rigid")))
    too_generic_count = sum(1 for item in records if _safe_bool(item.get("felt_too_generic")))
    too_much_practice_count = sum(1 for item in records if _safe_bool(item.get("too_much_practice")))
    too_many_questions_count = sum(1 for item in records if _safe_bool(item.get("too_many_questions")))
    safety_concern_count = sum(1 for item in records if _safe_bool(item.get("safety_concern")))

    summary: dict[str, Any] = {
        "schema_version": "live_feedback_summary_v1",
        "generated_at_utc": _now_iso(),
        "session_id": str(session_payload.get("session_id", "") or ""),
        "feedback_count": len(records),
        "ratings_count": len(ratings),
        "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
        "too_rigid_count": too_rigid_count,
        "too_generic_count": too_generic_count,
        "too_much_practice_count": too_much_practice_count,
        "too_many_questions_count": too_many_questions_count,
        "safety_concern_count": safety_concern_count,
        "drift_warning_count": int(session_payload.get("drift_warning_count", 0) or 0),
        "drift_critical_count": int(session_payload.get("drift_critical_count", 0) or 0),
        "top_comments": comments[:5],
        "recommended_next_action": "",
    }
    summary["recommended_next_action"] = _recommend_next_action(summary)
    return summary


def build_summary_artifacts(
    *,
    session_payload: dict[str, Any],
    session_id: str,
    output_dir: Path | None = None,
) -> tuple[Path, Path, dict[str, Any]]:
    summary = build_summary_payload(session_payload)
    reports_dir = output_dir or get_feedback_reports_dir()
    reports_dir.mkdir(parents=True, exist_ok=True)

    json_path = reports_dir / f"{session_id}_summary.json"
    md_path = reports_dir / f"{session_id}_summary.md"

    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        f"# Guided Live Feedback Summary: {session_id}",
        "",
        f"- generated_at_utc: `{summary['generated_at_utc']}`",
        f"- feedback_count: `{summary['feedback_count']}`",
        f"- average_rating: `{summary['average_rating']}`",
        f"- too_rigid_count: `{summary['too_rigid_count']}`",
        f"- too_generic_count: `{summary['too_generic_count']}`",
        f"- too_much_practice_count: `{summary['too_much_practice_count']}`",
        f"- too_many_questions_count: `{summary['too_many_questions_count']}`",
        f"- drift_warning_count: `{summary['drift_warning_count']}`",
        f"- drift_critical_count: `{summary['drift_critical_count']}`",
        f"- recommended_next_action: `{summary['recommended_next_action']}`",
        "",
        "## Top Comments",
    ]
    if summary["top_comments"]:
        lines.extend([f"- {comment}" for comment in summary["top_comments"]])
    else:
        lines.append("- (none)")
    md_text = "\n".join(lines)
    md_path.write_text(md_text + "\n", encoding="utf-8")

    return json_path, md_path, summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Build guided live feedback summary")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    session_id = str(args.session_id)
    payload = load_session_payload(session_id)
    if not isinstance(payload, dict):
        raise ValueError(f"session not found: {session_id}")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else None
    json_path, md_path, summary = build_summary_artifacts(
        session_payload=payload,
        session_id=session_id,
        output_dir=output_dir,
    )

    print(
        json.dumps(
            {
                "session_id": session_id,
                "summary_json": str(json_path),
                "summary_md": str(md_path),
                "recommended_next_action": summary.get("recommended_next_action"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
