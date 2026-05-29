#!/usr/bin/env python3
"""CLI capture for guided live feedback records."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from bot_agent.live_testing.feedback_capture import (  # noqa: E402
    append_feedback_record,
    build_trace_summary,
    create_feedback_record,
)


def _load_trace_json(path_raw: str | None) -> dict[str, Any]:
    if not path_raw:
        return {}
    path = Path(path_raw)
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Capture one guided live feedback record")
    parser.add_argument("--session-id", required=True)
    parser.add_argument("--turn-id", required=True)
    parser.add_argument("--scenario-id", default=None)
    parser.add_argument("--rating", default=None)
    parser.add_argument("--felt-alive", default=None)
    parser.add_argument("--felt-understood", default=None)
    parser.add_argument("--felt-too-rigid", default=None)
    parser.add_argument("--felt-too-generic", default=None)
    parser.add_argument("--felt-too-long", default=None)
    parser.add_argument("--felt-too-short", default=None)
    parser.add_argument("--too-much-practice", default=None)
    parser.add_argument("--too-many-questions", default=None)
    parser.add_argument("--missed-context", default=None)
    parser.add_argument("--safety-concern", default=None)
    parser.add_argument("--comment", default="")
    parser.add_argument("--trace-json", default=None)
    parser.add_argument("--user-message-preview", default="")
    parser.add_argument("--answer-preview", default="")
    parser.add_argument("--user-id", default="")
    parser.add_argument("--backend-url", default="")
    parser.add_argument("--frontend-url", default="")
    parser.add_argument("--scenario-set", default="guided_live_v1")
    args = parser.parse_args()

    trace_payload = _load_trace_json(args.trace_json)
    debug_payload = trace_payload.get("debug") if isinstance(trace_payload.get("debug"), dict) else trace_payload

    record = create_feedback_record(
        session_id=args.session_id,
        turn_id=args.turn_id,
        scenario_id=args.scenario_id,
        user_rating=args.rating,
        felt_alive=args.felt_alive,
        felt_understood=args.felt_understood,
        felt_too_rigid=args.felt_too_rigid,
        felt_too_generic=args.felt_too_generic,
        felt_too_long=args.felt_too_long,
        felt_too_short=args.felt_too_short,
        too_much_practice=args.too_much_practice,
        too_many_questions=args.too_many_questions,
        missed_context=args.missed_context,
        safety_concern=args.safety_concern,
        comment=args.comment,
        trace_summary=build_trace_summary(
            debug_payload=debug_payload if isinstance(debug_payload, dict) else {},
            user_message_preview=args.user_message_preview,
            answer_preview=args.answer_preview,
            user_id=args.user_id,
        ),
    )

    payload = append_feedback_record(
        record=record,
        backend_url=args.backend_url,
        frontend_url=args.frontend_url,
        scenario_set=args.scenario_set,
    )

    print(
        json.dumps(
            {
                "session_id": payload.get("session_id"),
                "feedback_count": payload.get("feedback_count"),
                "drift_warning_count": payload.get("drift_warning_count"),
                "drift_critical_count": payload.get("drift_critical_count"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
