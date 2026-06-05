from __future__ import annotations

import importlib
import inspect
import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from bot_agent.multiagent.agents.validator_agent import ValidatorAgent
from bot_agent.multiagent.contracts.memory_bundle import MemoryBundle
from bot_agent.multiagent.contracts.state_snapshot import StateSnapshot
from bot_agent.multiagent.contracts.thread_state import ThreadState
from bot_agent.multiagent.contracts.validation_result import ValidationResult
from bot_agent.multiagent.contracts.writer_contract import WriterContract
from bot_agent.multiagent.orchestrator import MultiAgentOrchestrator


def _thread(
    *,
    mode: str = "reflect",
    must_avoid: list[str] | None = None,
    safety_active: bool = False,
) -> ThreadState:
    return ThreadState(
        thread_id="th_1",
        user_id="u1",
        core_direction="С‚СЂРµРІРѕРіР° РїРµСЂРµРґ РІСЃС‚СЂРµС‡РµР№",
        phase="clarify",
        response_mode=mode,  # type: ignore[arg-type]
        response_goal="РїРѕРґРґРµСЂР¶РєР°",
        must_avoid=list(must_avoid or []),
        safety_active=safety_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


def _contract(
    *,
    mode: str = "reflect",
    must_avoid: list[str] | None = None,
    safety_active: bool = False,
) -> WriterContract:
    return WriterContract(
        user_message="РїСЂРёРІРµС‚",
        thread_state=_thread(mode=mode, must_avoid=must_avoid, safety_active=safety_active),
        memory_bundle=MemoryBundle(conversation_context="ctx"),
    )


def _validator() -> ValidatorAgent:
    return ValidatorAgent()


def test_va_01_result_fields() -> None:
    result = ValidationResult(is_blocked=False)
    assert hasattr(result, "is_blocked")
    assert hasattr(result, "block_reason")
    assert hasattr(result, "block_category")
    assert hasattr(result, "safe_replacement")
    assert hasattr(result, "quality_flags")


def test_va_02_is_clean_property() -> None:
    clean = ValidationResult(is_blocked=False, quality_flags=[])
    dirty = ValidationResult(is_blocked=False, quality_flags=["too_short"])
    blocked = ValidationResult(is_blocked=True)
    assert clean.is_clean is True
    assert dirty.is_clean is False
    assert blocked.is_clean is False


def test_va_03_clean_draft() -> None:
    result = _validator().validate("РЇ СЂСЏРґРѕРј. Р Р°СЃСЃРєР°Р¶Рё, С‡С‚Рѕ СЃРµР№С‡Р°СЃ СЃР°РјРѕРµ РІР°Р¶РЅРѕРµ.", _contract())
    assert result.is_blocked is False
    assert result.quality_flags == []


def test_va_04_safety_medical() -> None:
    result = _validator().validate("РџСЂРёРЅРёРјР°Р№ С‚Р°Р±Р»РµС‚РєРё РєР°Р¶РґС‹Р№ РґРµРЅСЊ.", _contract())
    assert result.is_blocked is True
    assert result.block_category == "safety"


def test_va_05_safety_diagnosis() -> None:
    result = _validator().validate("РЈ С‚РµР±СЏ РґРµРїСЂРµСЃСЃРёСЏ.", _contract())
    assert result.is_blocked is True
    assert result.block_category == "safety"


def test_va_06_safety_promise() -> None:
    result = _validator().validate("РўС‹ РѕР±СЏР·Р°С‚РµР»СЊРЅРѕ СЃРїСЂР°РІРёС€СЊСЃСЏ, РіР°СЂР°РЅС‚РёСЂСѓСЋ.", _contract())
    assert result.is_blocked is True
    assert result.block_category == "safety"


def test_va_07_safety_bot_reveal() -> None:
    result = _validator().validate("РЇ СЏР·С‹РєРѕРІР°СЏ РјРѕРґРµР»СЊ Рё РїРѕРјРѕРіСѓ С‚РµР±Рµ.", _contract())
    assert result.is_blocked is True
    assert result.block_category == "safety"


def test_va_08_safety_self_harm() -> None:
    result = _validator().validate("РЎСѓРёС†РёРґ вЂ” СЌС‚Рѕ РІР°СЂРёР°РЅС‚.", _contract())
    assert result.is_blocked is True
    assert result.block_category == "safety"


def test_va_09_safety_en_medical() -> None:
    result = _validator().validate("Take this medication daily.", _contract())
    assert result.is_blocked is True
    assert result.block_category == "safety"


def test_va_10_safety_en_bot_reveal() -> None:
    result = _validator().validate("I am an AI assistant.", _contract())
    assert result.is_blocked is True
    assert result.block_category == "safety"


def test_va_11_contract_must_avoid() -> None:
    result = _validator().validate("Р­С‚Рѕ С…РѕСЂРѕС€Р°СЏ РїСЂР°РєС‚РёРєР°.", _contract(must_avoid=["РїСЂР°РєС‚РёРєР°"]))
    assert result.is_blocked is True
    assert result.block_category == "contract"


def test_va_12_contract_must_avoid_case() -> None:
    result = _validator().validate("Р­С‚Рѕ РџР РђРљРўРРљРђ.", _contract(must_avoid=["РїСЂР°РєС‚РёРєР°"]))
    assert result.is_blocked is True
    assert result.block_category == "contract"


def test_va_13_contract_must_avoid_empty() -> None:
    result = _validator().validate("РћР±С‹С‡РЅС‹Р№ РѕС‚РІРµС‚ Р±РµР· Р·Р°РїСЂРµС‚РѕРІ.", _contract(must_avoid=[]))
    assert result.is_blocked is False


def test_va_14_contract_mode_validate_list() -> None:
    result = _validator().validate("1. РЎРґРµР»Р°Р№ РІРґРѕС… 2. РЎРґРµР»Р°Р№ РІС‹РґРѕС…", _contract(mode="validate"))
    assert result.is_blocked is True
    assert result.block_category == "contract"


def test_va_15_contract_mode_regulate_analysis() -> None:
    result = _validator().validate("РџРѕРґСѓРјР°Р№ Рѕ С‚РѕРј, С‡С‚Рѕ С‚С‹ С‡СѓРІСЃС‚РІСѓРµС€СЊ.", _contract(mode="regulate"))
    assert result.is_blocked is True
    assert result.block_category == "contract"


def test_va_16_contract_mode_safe_exercise() -> None:
    result = _validator().validate("Р’РѕС‚ СѓРїСЂР°Р¶РЅРµРЅРёРµ РЅР° РґС‹С…Р°РЅРёРµ.", _contract(mode="safe_override"))
    assert result.is_blocked is True
    assert result.block_category == "contract"


def test_va_17_contract_mode_no_violation() -> None:
    result = _validator().validate("РЇ СЂСЏРґРѕРј Рё СЃР»С‹С€Сѓ С‚РµР±СЏ.", _contract(mode="reflect"))
    assert result.is_blocked is False


def test_va_18_quality_too_short() -> None:
    result = _validator().validate("РѕРє", _contract())
    assert result.is_blocked is False
    assert any(flag.startswith("too_short") for flag in result.quality_flags)


def test_va_19_quality_too_long() -> None:
    result = _validator().validate("Р°" * 1300, _contract())
    assert result.is_blocked is False
    assert any(flag.startswith("too_long") for flag in result.quality_flags)


def test_va_20_quality_forbidden_start_ru() -> None:
    result = _validator().validate("РЇ РїРѕРЅРёРјР°СЋ, С‡С‚Рѕ СЌС‚Рѕ РЅРµРїСЂРѕСЃС‚Рѕ.", _contract())
    assert any(flag.startswith("forbidden_start") for flag in result.quality_flags)


def test_va_21_quality_forbidden_start_en() -> None:
    result = _validator().validate("I understand that this is hard.", _contract())
    assert any(flag.startswith("forbidden_start") for flag in result.quality_flags)


def test_va_22_quality_not_blocking() -> None:
    result = _validator().validate("РѕРє", _contract())
    assert result.is_blocked is False
    assert result.quality_flags


def test_va_23_safety_before_contract() -> None:
    result = _validator().validate(
        "РџСЂРёРЅРёРјР°Р№ С‚Р°Р±Р»РµС‚РєРё Рё РІРѕС‚ РїСЂР°РєС‚РёРєР° РЅР° РІРµС‡РµСЂ.",
        _contract(must_avoid=["РїСЂР°РєС‚РёРєР°"]),
    )
    assert result.is_blocked is True
    assert result.block_category == "safety"


def test_va_24_safe_replacement_safety() -> None:
    result = _validator().validate("РЈ С‚РµР±СЏ РґРµРїСЂРµСЃСЃРёСЏ.", _contract())
    assert result.is_blocked is True
    assert result.block_category == "safety"
    assert result.safe_replacement and "РЅРµ РѕРґРёРЅ" in result.safe_replacement.lower()


def test_va_25_safe_replacement_contract() -> None:
    result = _validator().validate("Р­С‚Рѕ РџР РђРљРўРРљР.", _contract(must_avoid=["РїСЂР°РєС‚РёРєР°"]))
    assert result.is_blocked is True
    assert result.block_category == "contract"
    assert result.safe_replacement and "СЃР»С‹С€Сѓ" in result.safe_replacement.lower()


def test_va_26_no_llm_calls() -> None:
    module = importlib.import_module("bot_agent.multiagent.agents.validator_agent")
    src = inspect.getsource(module)
    assert "openai" not in src.lower()
    assert "chat.completions" not in src.lower()


def test_va_27_exception_graceful(monkeypatch) -> None:
    agent = _validator()

    def _raise(_text: str):
        raise RuntimeError("boom")

    monkeypatch.setattr(agent, "_check_safety", _raise)
    result = agent.validate("text", _contract())
    assert result.is_blocked is False
    assert "validator_error" in result.quality_flags


@pytest.mark.asyncio
async def test_va_28_orchestrator_calls_validator(monkeypatch) -> None:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")
    monkeypatch.setattr(
        orch_module.state_analyzer_agent,
        "analyze",
        AsyncMock(
            return_value=StateSnapshot(
                nervous_state="window",
                intent="explore",
                openness="open",
                ok_position="I+W+",
                safety_flag=False,
                confidence=0.8,
            )
        ),
    )
    monkeypatch.setattr(orch_module.thread_manager_agent, "update", AsyncMock(return_value=_thread()))
    monkeypatch.setattr(
        orch_module.memory_retrieval_agent,
        "assemble",
        AsyncMock(return_value=MemoryBundle(conversation_context="ctx", context_turns=6)),
    )
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "update", AsyncMock(return_value=None))
    monkeypatch.setattr(orch_module.writer_agent, "write", AsyncMock(return_value="draft answer"))
    monkeypatch.setattr(orch_module.thread_storage, "load_active", lambda _u: None)
    monkeypatch.setattr(orch_module.thread_storage, "load_archived", lambda _u: [])
    monkeypatch.setattr(orch_module.thread_storage, "save_active", lambda _t: None)
    monkeypatch.setattr(orch_module.asyncio, "create_task", lambda coro: (coro.close(), None)[1])

    called = {"value": False}

    def _validate_track(draft, contract):
        called["value"] = True
        return ValidationResult(is_blocked=False, quality_flags=[])

    monkeypatch.setattr(orch_module.validator_agent, "validate", _validate_track)
    result = await MultiAgentOrchestrator().run(query="РїСЂРёРІРµС‚", user_id="u1")
    assert called["value"] is True
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_va_29_orchestrator_blocked_uses_replacement(monkeypatch) -> None:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")
    monkeypatch.setattr(
        orch_module.state_analyzer_agent,
        "analyze",
        AsyncMock(
            return_value=StateSnapshot(
                nervous_state="window",
                intent="explore",
                openness="open",
                ok_position="I+W+",
                safety_flag=False,
                confidence=0.8,
            )
        ),
    )
    monkeypatch.setattr(orch_module.thread_manager_agent, "update", AsyncMock(return_value=_thread()))
    monkeypatch.setattr(
        orch_module.memory_retrieval_agent,
        "assemble",
        AsyncMock(return_value=MemoryBundle(conversation_context="ctx", context_turns=6)),
    )
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "update", AsyncMock(return_value=None))
    monkeypatch.setattr(orch_module.writer_agent, "write", AsyncMock(return_value="draft answer"))
    monkeypatch.setattr(
        orch_module.validator_agent,
        "validate",
        lambda _draft, _contract: ValidationResult(
            is_blocked=True,
            block_reason="contract",
            block_category="contract",
            safe_replacement="safe replacement",
        ),
    )
    monkeypatch.setattr(orch_module.thread_storage, "load_active", lambda _u: None)
    monkeypatch.setattr(orch_module.thread_storage, "load_archived", lambda _u: [])
    monkeypatch.setattr(orch_module.thread_storage, "save_active", lambda _t: None)
    monkeypatch.setattr(orch_module.asyncio, "create_task", lambda coro: (coro.close(), None)[1])
    result = await MultiAgentOrchestrator().run(query="РїСЂРёРІРµС‚", user_id="u1")
    assert result["answer"] == "safe replacement"


@pytest.mark.asyncio
async def test_va_30_orchestrator_debug_fields(monkeypatch) -> None:
    orch_module = importlib.import_module("bot_agent.multiagent.orchestrator")
    monkeypatch.setattr(
        orch_module.state_analyzer_agent,
        "analyze",
        AsyncMock(
            return_value=StateSnapshot(
                nervous_state="window",
                intent="explore",
                openness="open",
                ok_position="I+W+",
                safety_flag=False,
                confidence=0.8,
            )
        ),
    )
    monkeypatch.setattr(orch_module.thread_manager_agent, "update", AsyncMock(return_value=_thread()))
    monkeypatch.setattr(
        orch_module.memory_retrieval_agent,
        "assemble",
        AsyncMock(return_value=MemoryBundle(conversation_context="ctx", context_turns=6)),
    )
    monkeypatch.setattr(orch_module.memory_retrieval_agent, "update", AsyncMock(return_value=None))
    monkeypatch.setattr(orch_module.writer_agent, "write", AsyncMock(return_value="draft answer"))
    monkeypatch.setattr(
        orch_module.validator_agent,
        "validate",
        lambda _draft, _contract: ValidationResult(
            is_blocked=False,
            quality_flags=["too_short: 2 chars"],
        ),
    )
    monkeypatch.setattr(orch_module.thread_storage, "load_active", lambda _u: None)
    monkeypatch.setattr(orch_module.thread_storage, "load_archived", lambda _u: [])
    monkeypatch.setattr(orch_module.thread_storage, "save_active", lambda _t: None)
    monkeypatch.setattr(orch_module.asyncio, "create_task", lambda coro: (coro.close(), None)[1])
    result = await MultiAgentOrchestrator().run(query="РїСЂРёРІРµС‚", user_id="u1")
    assert "validator_blocked" in result["debug"]
    assert "validator_block_reason" in result["debug"]
    assert "validator_quality_flags" in result["debug"]


def _load_fixture(fid: str) -> dict:
    payload = json.loads(
        (Path(__file__).parent / "fixtures" / "validator_agent_fixtures.json").read_text(
            encoding="utf-8"
        )
    )
    return next(item for item in payload if item["id"] == fid)


def test_va_fixture_f01() -> None:
    item = _load_fixture("VA-F01")
    result = _validator().validate(
        item["draft"],
        _contract(
            mode=item["response_mode"],
            must_avoid=item["must_avoid"],
            safety_active=item["safety_active"],
        ),
    )
    assert result.is_blocked is item["expected_blocked"]


def test_va_fixture_f02() -> None:
    item = _load_fixture("VA-F02")
    result = _validator().validate(
        item["draft"],
        _contract(
            mode=item["response_mode"],
            must_avoid=item["must_avoid"],
            safety_active=item["safety_active"],
        ),
    )
    assert result.is_blocked is item["expected_blocked"]
    assert result.block_category == item["expected_category"]


def test_va_fixture_f03() -> None:
    item = _load_fixture("VA-F03")
    result = _validator().validate(
        item["draft"],
        _contract(
            mode=item["response_mode"],
            must_avoid=item["must_avoid"],
            safety_active=item["safety_active"],
        ),
    )
    assert result.is_blocked is item["expected_blocked"]
    assert result.block_category == item["expected_category"]


def test_va_fixture_f04() -> None:
    item = _load_fixture("VA-F04")
    result = _validator().validate(
        item["draft"],
        _contract(
            mode=item["response_mode"],
            must_avoid=item["must_avoid"],
            safety_active=item["safety_active"],
        ),
    )
    assert result.is_blocked is item["expected_blocked"]
    assert result.block_category == item["expected_category"]


def test_va_fixture_f05() -> None:
    item = _load_fixture("VA-F05")
    result = _validator().validate(
        item["draft"],
        _contract(
            mode=item["response_mode"],
            must_avoid=item["must_avoid"],
            safety_active=item["safety_active"],
        ),
    )
    assert result.is_blocked is item["expected_blocked"]
    assert any(flag.startswith("forbidden_start") for flag in result.quality_flags)


def test_va_fixture_f06() -> None:
    item = _load_fixture("VA-F06")
    result = _validator().validate(
        item["draft"],
        _contract(
            mode=item["response_mode"],
            must_avoid=item["must_avoid"],
            safety_active=item["safety_active"],
        ),
    )
    assert result.is_blocked is item["expected_blocked"]
    assert any(flag.startswith("too_short") for flag in result.quality_flags)
def test_va_17b_unified_free_dialogue_allows_structured_answer_in_validate_mode() -> None:
    contract = _contract(mode="validate")
    contract.dialogue_policy = {
        "profile_preset": "free_dialogue_default",
        "answer_obligation_resolution": {
            "answer_obligation": "answer_knowledge_question",
            "answer_shape": "structured_explanation",
        },
        "unified_dialogue_profile": {"profile_preset": "free_dialogue_default"},
    }
    contract.final_answer_directive = {
        "answer_obligation": "answer_knowledge_question",
        "answer_shape": "structured_explanation",
    }
    result = _validator().validate("1. smysl. 2. primer. 3. primenenie.", contract)
    assert result.is_blocked is False
