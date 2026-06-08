#!/usr/bin/env python3
"""PRD-047.14 summary/recap routing audit.

Dry mode is static and read-only. Live mode is intentionally conservative and
does not call chat/query endpoints because those can mutate conversation state.
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PRD_ID = "PRD-047.14"
REPO_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID

SUMMARY_CASES = [
    {
        "id": "summary_recap_001",
        "query": "\u041f\u043e\u0434\u0432\u0435\u0434\u0438 \u043a\u0440\u0430\u0442\u043a\u0438\u0439 \u0438\u0442\u043e\u0433 \u043d\u0430\u0448\u0435\u0439 \u0431\u0435\u0441\u0435\u0434\u044b.",
        "expected_dialogue_act": "summary_request",
        "expected_answer_obligation": "summarize_conversation",
    },
    {
        "id": "summary_recap_002",
        "query": "\u041a\u0440\u0430\u0442\u043a\u043e \u0440\u0435\u0437\u044e\u043c\u0438\u0440\u0443\u0439, \u043a \u0447\u0435\u043c\u0443 \u043c\u044b \u043f\u0440\u0438\u0448\u043b\u0438.",
        "expected_dialogue_act": "summary_request",
        "expected_answer_obligation": "summarize_conversation",
    },
    {
        "id": "summary_recap_003",
        "query": "\u0421\u043e\u0431\u0435\u0440\u0438 \u0432\u044b\u0432\u043e\u0434\u044b \u0438\u0437 \u043d\u0430\u0448\u0435\u0433\u043e \u0434\u0438\u0430\u043b\u043e\u0433\u0430.",
        "expected_dialogue_act": "summary_request",
        "expected_answer_obligation": "summarize_conversation",
    },
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def read_source(name: str) -> str:
    path = REPO_ROOT / name
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8-sig", errors="replace")


def dry_audit() -> dict[str, Any]:
    sources = {
        "dialogue_policy": read_source("bot_psychologist/bot_agent/multiagent/dialogue_policy.py"),
        "answer_obligation": read_source("bot_psychologist/bot_agent/multiagent/answer_obligation_resolver.py"),
        "orchestrator": read_source("bot_psychologist/bot_agent/multiagent/orchestrator.py"),
        "writer_contract": read_source("bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py"),
        "response_planner": read_source("bot_psychologist/bot_agent/multiagent/response_planner.py"),
    }
    combined = "\n".join(sources.values()).lower()
    has_summary_act = "summary_request" in combined
    has_summary_obligation = "summarize_conversation" in combined or "summary_obligation" in combined
    has_confirmation_risk = "confirmation_to_last_offer" in combined and "answer_last_offer" in combined

    cases = []
    for case in SUMMARY_CASES:
        risk = "low"
        observed = "dedicated_summary_route_present" if has_summary_act and has_summary_obligation else "no_dedicated_summary_route_detected_static"
        if not (has_summary_act and has_summary_obligation):
            risk = "static_warning"
        cases.append(
            {
                **case,
                "mode": "dry_static",
                "observed_static_route": observed,
                "confirmation_to_last_offer_risk_present": has_confirmation_risk,
                "risk": risk,
                "runtime_mutated": False,
            }
        )

    risk_count = sum(1 for case in cases if case["risk"] != "low")
    payload = {
        "generated_at_utc": now_iso(),
        "mode": "dry",
        "summary_routing_status": "warning_static_risk" if risk_count else "passed",
        "summary_misroute_count": 0,
        "summary_static_risk_count": risk_count,
        "dedicated_summary_dialogue_act_present": has_summary_act,
        "dedicated_summary_answer_obligation_present": has_summary_obligation,
        "confirmation_to_last_offer_risk_present": has_confirmation_risk,
        "cases": cases,
        "runtime_mutated": False,
        "note": "Dry audit is static. It identifies routing risk but does not confirm a live runtime bug.",
    }
    return payload


def live_probe(base_url: str) -> dict[str, Any]:
    health_url = base_url.rstrip("/") + "/api/v1/health"
    try:
        with urllib.request.urlopen(health_url, timeout=3) as response:
            body = response.read().decode("utf-8", errors="replace")
            backend_available = response.status < 500
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "live_status": "skipped_backend_unavailable",
            "backend_available": False,
            "error": str(exc),
            "runtime_mutated": False,
        }
    return {
        "live_status": "skipped_no_read_only_summary_route_endpoint",
        "backend_available": backend_available,
        "health_url": health_url,
        "health_response_sample": body[:300],
        "reason": "Chat/query endpoints can mutate conversation state; audit-only PRD avoids live write paths.",
        "runtime_mutated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["dry", "live"], default="dry")
    parser.add_argument("--base-url", default="http://127.0.0.1:8001")
    args = parser.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    write_json(LOG_DIR / "summary_routing_cases.json", {"generated_at_utc": now_iso(), "cases": SUMMARY_CASES})
    result = dry_audit()
    if args.mode == "live":
        result.update(live_probe(args.base_url))
    else:
        result["live_status"] = "not_requested"
    write_json(LOG_DIR / "summary_routing_audit.json", result)
    write_text(
        LOG_DIR / "summary_routing_audit.md",
        "\n".join(
            [
                "# PRD-047.14 Summary Routing Audit",
                "",
                f"- mode: `{args.mode}`",
                f"- summary_routing_status: `{result['summary_routing_status']}`",
                f"- summary_misroute_count: `{result['summary_misroute_count']}`",
                f"- summary_static_risk_count: `{result['summary_static_risk_count']}`",
                f"- live_status: `{result.get('live_status')}`",
                "- runtime_mutated: `false`",
            ]
        ),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
