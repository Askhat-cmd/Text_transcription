from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
BOT_PSYCHOLOGIST_ROOT = REPO_ROOT / "bot_psychologist"
if str(BOT_PSYCHOLOGIST_ROOT) not in sys.path:
    sys.path.insert(0, str(BOT_PSYCHOLOGIST_ROOT))

from bot_agent.multiagent.agents.writer_agent import WriterAgent


class _SnapshotWriterAgent(WriterAgent):
    def __init__(self, *, llm_result: str | None = None, llm_error: Exception | None = None) -> None:
        super().__init__(client=object(), model="snapshot-model")
        self._snapshot_llm_result = llm_result
        self._snapshot_llm_error = llm_error

    async def _call_llm(
        self,
        contract: Any,
        *,
        prompt_constraint_decision: dict[str, Any] | None = None,
    ) -> str:
        if self._snapshot_llm_error is not None:
            raise self._snapshot_llm_error
        return self._snapshot_llm_result or ""

    def _enforce_answer_compliance(self, result: str, contract: Any) -> str:
        return result

    def _apply_name_continuity(self, result: str, contract: Any) -> str:
        return result

    @staticmethod
    def _static_fallback(contract: Any) -> str:
        return "STATIC_FALLBACK"

    @staticmethod
    def _detect_language(text: str) -> str:
        return "ru"


def _contract(*, safety_active: bool, dialogue_profile: str = "safe_guided") -> Any:
    return SimpleNamespace(
        user_message="Мне сейчас тяжело, ответь спокойно.",
        response_language=None,
        dialogue_policy={"profile": dialogue_profile},
        thread_state=SimpleNamespace(safety_active=safety_active),
    )


def _serialize_case(name: str, *, returned_text: str, agent: _SnapshotWriterAgent) -> dict[str, Any]:
    debug = dict(agent.last_debug)
    return {
        "case": name,
        "returned_text": returned_text,
        "fallback_used": debug.get("fallback_used"),
        "error": debug.get("error"),
        "dialogue_profile": debug.get("dialogue_profile"),
        "model": debug.get("model"),
        "temperature": debug.get("temperature"),
        "max_tokens": debug.get("max_tokens"),
        "timeout": debug.get("timeout"),
        "system_prompt_kind": (
            "mvp_free_dialogue"
            if debug.get("dialogue_profile") == "mvp_free_dialogue"
            else "safe_guided"
        ),
    }


async def _run_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    safety_success_agent = _SnapshotWriterAgent(llm_result="SAFE_OK")
    safety_success_result = await safety_success_agent.write(_contract(safety_active=True))
    cases.append(_serialize_case("safety_success", returned_text=safety_success_result, agent=safety_success_agent))

    safety_exception_agent = _SnapshotWriterAgent(llm_error=RuntimeError("SAFE_BOOM"))
    safety_exception_result = await safety_exception_agent.write(_contract(safety_active=True))
    cases.append(
        _serialize_case("safety_exception", returned_text=safety_exception_result, agent=safety_exception_agent)
    )

    normal_empty_agent = _SnapshotWriterAgent(llm_result="   ")
    normal_empty_result = await normal_empty_agent.write(_contract(safety_active=False))
    cases.append(_serialize_case("normal_empty", returned_text=normal_empty_result, agent=normal_empty_agent))

    normal_exception_agent = _SnapshotWriterAgent(llm_error=RuntimeError("NORMAL_BOOM"))
    normal_exception_result = await normal_exception_agent.write(_contract(safety_active=False))
    cases.append(
        _serialize_case("normal_exception", returned_text=normal_exception_result, agent=normal_exception_agent)
    )

    return cases


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "prd_047_42_apply_5_write_snapshot_v1",
        "cases": asyncio.run(_run_cases()),
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
