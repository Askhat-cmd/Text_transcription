#!/usr/bin/env python3
"""PRD-047.14-HF1 direct acceptance checks."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any


PRD_ID = "PRD-047.14-HF1"
REPO_ROOT = Path(__file__).resolve().parents[3]
LOG_DIR = REPO_ROOT / "TO_DO_LIST" / "logs" / PRD_ID
BOT_ROOT = REPO_ROOT / "bot_psychologist"
sys.path.insert(0, str(BOT_ROOT))

from bot_agent.multiagent.final_answer_acceptance_gate import build_final_answer_acceptance_gate_v1  # noqa: E402
from bot_agent.multiagent.template_family_guard import (  # noqa: E402
    build_memory_contamination_guard_result,
    detect_template_family_leakage,
)


BAD_TEMPLATE = (
    "В твоем описании важно не свести все к одному общему механизму. "
    "1. Сначала отдели факты от вывода.\n"
    "2. Затем найди центральное убеждение.\n"
    "3. После этого проверь, что это убеждение заставляет делать.\n"
    "4. Практический смысл распутывания здесь в том, чтобы вернуть себе следующий ход."
)
CLEAN_ANSWER = (
    "Ты описываешь не пустоту, а момент, где привычная опора перестала работать: "
    "семья давит ответственностью, риск сокращения бьет по ощущению ценности, а ступор "
    "делает все похожим на один неподъемный узел. Начать стоит с разделения рабочего факта "
    "и внутреннего приговора, чтобы вернуть себе ближайший реальный ход."
)
USER_CASE = (
    "Мне 50 лет, семья, риск сокращения, страх невостребованности, ступор, ощущение что все "
    "упущено. Как распутать этот клубок убеждений?"
)


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, payload: dict[str, Any]) -> None:
    lines = [f"# {path.stem}", ""]
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            lines.append(f"- {key}: `{json.dumps(value, ensure_ascii=False)}`")
        else:
            lines.append(f"- {key}: `{value}`")
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _gate(answer: str) -> dict[str, Any]:
    return build_final_answer_acceptance_gate_v1(
        user_message=USER_CASE,
        final_answer=answer,
        dialogue_act_resolution={"dialogue_act": "concrete_situation_question"},
        answer_obligation_resolution={"answer_obligation": "answer_concrete_situation"},
        unanswered_question_state_before={
            "answer_required": True,
            "last_direct_user_question": USER_CASE,
            "answer_status": "pending",
        },
        last_assistant_offer_before={},
        dialogue_style_state={},
        final_answer_directive={"must_answer": USER_CASE},
        writer_debug={},
        validator_result=SimpleNamespace(is_blocked=False),
        previous_assistant_message="",
    )


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    bad_detector = detect_template_family_leakage(BAD_TEMPLATE)
    clean_detector = detect_template_family_leakage(CLEAN_ANSWER)
    bad_gate = _gate(BAD_TEMPLATE)
    clean_gate = _gate(CLEAN_ANSWER)
    memory_guard = build_memory_contamination_guard_result(final_answer_acceptance_gate=bad_gate)
    cases = [
        {
            "id": "HF1-TL-001",
            "type": "bad_answer_detector",
            "passed": bool(bad_detector.get("leak_detected")),
            "details": bad_detector,
        },
        {
            "id": "HF1-TL-002",
            "type": "clean_answer_detector",
            "passed": not bool(clean_detector.get("leak_detected")),
            "details": clean_detector,
        },
        {
            "id": "HF1-TL-003",
            "type": "final_answer_gate_quarantine",
            "passed": (
                bad_gate.get("status") == "failed"
                and "template_family_leakage_detected" in list(bad_gate.get("failed_checks", []) or [])
                and bad_gate.get("can_save_as_healthy_context") is False
                and bad_gate.get("can_use_as_summary_source") is False
                and bad_gate.get("can_save_last_assistant_offer") is False
            ),
            "details": {
                "status": bad_gate.get("status"),
                "failed_checks": bad_gate.get("failed_checks", []),
                "template_family_guard": bad_gate.get("template_family_guard", {}),
            },
        },
        {
            "id": "HF1-TL-004",
            "type": "clean_answer_gate_pass",
            "passed": clean_gate.get("template_family_guard", {}).get("leak_detected") is False,
            "details": {
                "status": clean_gate.get("status"),
                "template_family_guard": clean_gate.get("template_family_guard", {}),
            },
        },
        {
            "id": "HF1-TL-005",
            "type": "memory_contamination_guard",
            "passed": (
                memory_guard.get("contaminated") is True
                and memory_guard.get("healthy_memory_allowed") is False
                and memory_guard.get("summary_source_allowed") is False
                and memory_guard.get("last_assistant_offer_allowed") is False
            ),
            "details": memory_guard,
        },
    ]
    failed = [case for case in cases if not case["passed"]]
    payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed" if not failed else "failed",
        "cases_passed": len(cases) - len(failed),
        "cases_total": len(cases),
        "cases": cases,
    }
    memory_payload = {
        "generated_at_utc": payload["generated_at_utc"],
        "status": "passed" if cases[-1]["passed"] else "failed",
        **memory_guard,
    }
    _write_json(LOG_DIR / "template_family_guard_acceptance.json", payload)
    _write_md(LOG_DIR / "template_family_guard_acceptance.md", payload)
    _write_json(LOG_DIR / "memory_contamination_guard_result.json", memory_payload)
    _write_md(LOG_DIR / "memory_contamination_guard_result.md", memory_payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
