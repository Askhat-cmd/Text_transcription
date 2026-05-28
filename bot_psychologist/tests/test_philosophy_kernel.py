from __future__ import annotations

from bot_agent.multiagent.philosophy_kernel import (
    KERNEL_V1,
    PHILOSOPHY_KERNEL_VERSION,
    build_philosophy_kernel_runtime_payload,
    render_kernel_prompt_block,
    select_philosophy_lenses,
)


def test_kernel_has_required_sections() -> None:
    assert KERNEL_V1.version == PHILOSOPHY_KERNEL_VERSION
    assert KERNEL_V1.identity.get("bot_identity")
    assert len(KERNEL_V1.principles) >= 4
    assert len(KERNEL_V1.boundaries) >= 4
    assert "neurostalking" in KERNEL_V1.lens_map


def test_kernel_does_not_contain_long_raw_source_excerpts() -> None:
    assert all(len(item) < 280 for item in KERNEL_V1.principles)
    assert all(len(item) < 280 for item in KERNEL_V1.response_posture)
    assert all(len(str(value.get("guidance", ""))) < 320 for value in KERNEL_V1.lens_map.values())


def test_selector_picks_neurostalking_lens() -> None:
    payload = select_philosophy_lenses(
        user_message="Что такое нейросталкинг?",
        safety_active=False,
        response_mode="reflect",
    )
    assert "neurostalking" in payload["selected_lenses"]


def test_selector_picks_imperfect_self_lens() -> None:
    payload = select_philosophy_lenses(
        user_message="Я боюсь, что уже все упустил и не справлюсь",
        safety_active=False,
        response_mode="reflect",
    )
    assert "imperfect_self_program" in payload["selected_lenses"]


def test_selector_picks_driver_lens_for_pressure_language() -> None:
    payload = select_philosophy_lenses(
        user_message="Я постоянно спешу и будто опаздываю жить",
        safety_active=False,
        response_mode="reflect",
    )
    assert "drivers" in payload["selected_lenses"]


def test_selector_uses_autopilot_for_inner_loop_phrase() -> None:
    payload = select_philosophy_lenses(
        user_message="Почему я возвращаюсь к одному и тому же внутреннему кругу?",
        safety_active=False,
        response_mode="reflect",
    )
    assert "autopilot" in payload["selected_lenses"]


def test_greeting_does_not_activate_deep_lens() -> None:
    payload = select_philosophy_lenses(
        user_message="Привет, как ты?",
        safety_active=False,
        response_mode="reflect",
    )
    assert payload["depth_mode"] in {"light", "guided"}
    assert "neurostalking" not in payload["selected_lenses"]


def test_safety_suppresses_kernel_prompt_block() -> None:
    payload = select_philosophy_lenses(
        user_message="Мне очень плохо",
        safety_active=True,
        response_mode="safe_override",
    )
    assert payload["prompt_block_included"] is False
    assert payload["depth_mode"] == "suppressed"


def test_prompt_block_includes_selected_lens_without_raw_quotes() -> None:
    selection = select_philosophy_lenses(
        user_message="Как самореализация связана с нейросталкингом?",
        safety_active=False,
        response_mode="reflect",
    )
    prompt_block = render_kernel_prompt_block(selection=selection)
    assert "NEO PHILOSOPHY KERNEL" in prompt_block
    assert "neurostalking" in prompt_block
    assert "Согласно Кузнице" not in prompt_block
    assert len(prompt_block) < 2200


def test_runtime_payload_contains_writer_freedom_contract() -> None:
    payload = build_philosophy_kernel_runtime_payload(
        user_message="Дай пару спокойных слов без анализа",
        safety_active=False,
        response_mode="reflect",
        practice_allowed=False,
    )
    assert payload["kernel_version"] == PHILOSOPHY_KERNEL_VERSION
    freedom = payload["writer_freedom_contract"]
    assert freedom["mode_is_hint_not_cage"] is True
    assert freedom["practice_requires_gate"] is True


def test_runtime_payload_supports_kernel_disabled_mode() -> None:
    payload = build_philosophy_kernel_runtime_payload(
        user_message="Что такое нейросталкинг?",
        safety_active=False,
        response_mode="reflect",
        practice_allowed=False,
        kernel_enabled=False,
    )
    assert payload["kernel_enabled"] is False
    assert payload["prompt_block"] == ""
    selection = payload["selection"]
    assert selection["prompt_block_included"] is False
    assert "kernel_disabled" in selection["selection_reason"]


def test_short_support_suppresses_prompt_block() -> None:
    payload = build_philosophy_kernel_runtime_payload(
        user_message="Я устал, скажи пару спокойных слов без анализа",
        safety_active=False,
        response_mode="reflect",
        practice_allowed=False,
    )
    selection = payload["selection"]
    assert selection["depth_mode"] == "suppressed"
    assert selection["prompt_block_included"] is False
