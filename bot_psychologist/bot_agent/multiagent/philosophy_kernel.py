"""NEO philosophy kernel and writer freedom contract helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any


PHILOSOPHY_KERNEL_VERSION = "neo_philosophy_kernel_v1"
WRITER_FREEDOM_CONTRACT_VERSION = "writer_freedom_contract_v1"
MAX_KERNEL_PROMPT_CHARS = 1800
MAX_FREEDOM_PROMPT_CHARS = 1000
MAX_COMBINED_PROMPT_CHARS = 2600
MAX_SELECTED_LENSES = 3
MAX_PRINCIPLES_IN_PROMPT = 4
MAX_BOUNDARIES_IN_PROMPT = 8


@dataclass(frozen=True)
class PhilosophyKernel:
    version: str
    identity: dict[str, Any]
    principles: list[str]
    boundaries: list[str]
    response_posture: list[str]
    lens_map: dict[str, dict[str, Any]]
    practice_policy: dict[str, Any]
    quote_policy: dict[str, Any]
    wakeup_reference_policy: dict[str, Any]


def build_philosophy_kernel() -> PhilosophyKernel:
    return PhilosophyKernel(
        version=PHILOSOPHY_KERNEL_VERSION,
        identity={
            "bot_identity": "NEO / Bot Psychologist",
            "role": "само-диагностирующаяся диалоговая система",
            "functions": ["зеркало", "навигатор", "мягкий катализатор осознавания"],
            "not_roles": [
                "психотерапевт",
                "духовный авторитет",
                "гуру",
                "замена специалиста",
            ],
        },
        principles=[
            "С человеком в основе все в порядке.",
            "Паттерн и автоматизм не равны личности.",
            "Сначала увидеть механизм, потом менять действие.",
            "Ответ возвращает авторство, а не подменяет его авторитетом бота.",
            "Практика уместна только через gate-запрос или safety-необходимость.",
            "Материалы ядра используются как внутренняя линза, не как цитатник.",
        ],
        boundaries=[
            "no_diagnosis",
            "no_spiritual_authority",
            "no_medical_legal_financial_directives",
            "no_unsolicited_practice",
            "no_raw_kb_quote_dumping",
            "privacy_sanitized_trace_only",
        ],
        response_posture=[
            "живой и конкретный ответ по текущему смыслу",
            "минимум клише и теоретизации",
            "один следующий ход без перегруза",
        ],
        lens_map={
            "neurostalking": {
                "label": "internal_pattern_observer",
                "guidance": (
                    "Объясняй нейросталкинг как внутреннее наблюдение за паттернами, "
                    "триггерами и автоматическими реакциями, без внешнего surveillance frame."
                ),
            },
            "imperfect_self_program": {
                "label": "not_broken_mechanism_frame",
                "guidance": (
                    "Формулируй переживание как защитный механизм, а не дефект личности."
                ),
            },
            "drivers": {
                "label": "inner_driver_pressure",
                "guidance": (
                    "Отражай давление внутреннего драйвера мягко, без жестких ярлыков."
                ),
            },
            "autopilot": {
                "label": "autopilot_inner_loop",
                "guidance": (
                    "Если человек описывает повторяющийся внутренний круг, "
                    "покажи автоматический цикл и пространство выбора."
                ),
            },
            "resource_first_contact": {
                "label": "short_resource_fit_contact",
                "guidance": (
                    "При low-resource запросе отвечай коротким поддерживающим контактом "
                    "без анализа и без практики по умолчанию."
                ),
            },
        },
        practice_policy={
            "practice_requires_gate": True,
            "unsolicited_practice_default": "forbidden",
        },
        quote_policy={
            "internal_lens_not_citation": True,
            "raw_quote_dumping_forbidden": True,
        },
        wakeup_reference_policy={
            "allowed": False,
            "note": "mechanism_only_no_style_copy",
        },
    )


KERNEL_V1 = build_philosophy_kernel()


_NEUROSTALKING_RE = re.compile(r"\bнейро[-\s]?сталкинг\w*", re.IGNORECASE)
_IMPERFECT_SELF_RE = re.compile(
    r"(не\s+справлюсь|опоздал\w*|ничего\s+не\s+получит\w+|я\s+недостаточ\w*|со\s+мной\s+что-?то\s+не\s+так|все\s+упустил|уже\s+поздно|прошивк\w+|потерплю\s+неудач\w*)",
    re.IGNORECASE,
)
_DRIVER_RE = re.compile(
    r"(надо\s+старать\w+|надо\s+быть\s+сильн\w+|должен\s+быть\s+сильн\w+|должен\s+быть\s+лучш\w+|постоянно\s+спеш\w+|опаздыва\w+\s+жить|не\s+буду\s+сильн\w+)",
    re.IGNORECASE,
)
_SHORT_SUPPORT_RE = re.compile(
    r"(без\s+анализ\w+|пару\s+спокойн\w+\s+слов|я\s+устал|не\s+нужн\w+\s+практик\w+|побудь\s+со\s+мной\s+коротк\w+)",
    re.IGNORECASE,
)
_GREETING_RE = re.compile(r"^(привет|здравствуй|добрый\s+день|hello|hi)\b", re.IGNORECASE)
_AUTOPILOT_RE = re.compile(r"(по\s+кругу|одному\s+и\s+тому\s+же|автопилот\w*|внутренн\w+\s+круг\w*)", re.IGNORECASE)


def _normalize(text: str) -> str:
    value = str(text or "").strip().lower()
    value = value.replace("ё", "е")
    return re.sub(r"\s+", " ", value)


def select_philosophy_lenses(
    *,
    user_message: str,
    safety_active: bool,
    response_mode: str,
    kernel_enabled: bool = True,
) -> dict[str, Any]:
    message = _normalize(user_message)
    selected: list[str] = []
    reasons: list[str] = []
    depth = "guided"
    prompt_block_included = bool(kernel_enabled)
    if not kernel_enabled:
        depth = "suppressed"
        reasons.append("kernel_disabled")
        return {
            "kernel_version": PHILOSOPHY_KERNEL_VERSION,
            "selected_lenses": [],
            "selection_reason": reasons,
            "depth_mode": depth,
            "prompt_block_included": False,
        }

    if safety_active:
        depth = "suppressed"
        prompt_block_included = False
        reasons.append("safety_active")
    elif _GREETING_RE.search(message):
        depth = "light"
        reasons.append("greeting_light_contact")
    elif _SHORT_SUPPORT_RE.search(message):
        selected.append("resource_first_contact")
        depth = "suppressed"
        prompt_block_included = False
        reasons.append("short_support_request")

    if _NEUROSTALKING_RE.search(message):
        selected.append("neurostalking")
        reasons.append("known_concept_neurostalking")

    if _IMPERFECT_SELF_RE.search(message):
        selected.append("imperfect_self_program")
        reasons.append("imperfect_self_signal")

    if _DRIVER_RE.search(message):
        selected.append("drivers")
        reasons.append("driver_pressure_signal")

    if _AUTOPILOT_RE.search(message):
        selected.append("autopilot")
        reasons.append("autopilot_loop_signal")

    if response_mode == "safe_override":
        depth = "suppressed"
        prompt_block_included = False
        reasons.append("safe_override_mode")

    selected = list(dict.fromkeys(selected))[:MAX_SELECTED_LENSES]
    if not selected and depth == "guided":
        reasons.append("no_deep_lens_selected")
    return {
        "kernel_version": PHILOSOPHY_KERNEL_VERSION,
        "selected_lenses": selected,
        "selection_reason": reasons,
        "depth_mode": depth,
        "prompt_block_included": prompt_block_included,
    }


def render_kernel_prompt_block(
    *,
    selection: dict[str, Any],
    kernel: PhilosophyKernel | None = None,
) -> str:
    active = kernel or KERNEL_V1
    if not bool(selection.get("prompt_block_included", True)):
        return ""
    selected_lenses = list(selection.get("selected_lenses", []) or [])
    lens_lines: list[str] = []
    for lens in selected_lenses[:MAX_SELECTED_LENSES]:
        lens_payload = active.lens_map.get(str(lens), {})
        guidance = str(lens_payload.get("guidance", "") or "").strip()
        if guidance:
            lens_lines.append(f"- {lens}: {guidance}")
    if not lens_lines:
        lens_lines.append("- default: держи живой контакт, без перегруза и без клише.")

    principle_lines = "\n".join(f"- {line}" for line in active.principles[:MAX_PRINCIPLES_IN_PROMPT])
    boundary_lines = "\n".join(f"- {line}" for line in active.boundaries[:MAX_BOUNDARIES_IN_PROMPT])

    return (
        "NEO PHILOSOPHY KERNEL:\n"
        f"version={active.version}\n"
        "identity=NEO / Bot Psychologist\n"
        "policy=internal_lens_not_quote_source\n"
        f"depth_mode={selection.get('depth_mode', 'guided')}\n"
        "core_principles:\n"
        f"{principle_lines}\n"
        "selected_lenses:\n"
        f"{chr(10).join(lens_lines)}\n"
        "hard_boundaries:\n"
        f"{boundary_lines}"
    )


def build_philosophy_kernel_prompt_block(
    *,
    selection: dict[str, Any],
    kernel: PhilosophyKernel | None = None,
) -> str:
    return render_kernel_prompt_block(selection=selection, kernel=kernel)


def build_writer_freedom_contract(
    *,
    response_mode: str,
    practice_allowed: bool,
) -> dict[str, Any]:
    return {
        "version": WRITER_FREEDOM_CONTRACT_VERSION,
        "enabled": True,
        "freedom_level": "guided",
        "mode_hint": str(response_mode or ""),
        "mode_is_hint_not_cage": True,
        "question_limit": 1,
        "practice_requires_gate": True,
        "practice_allowed": bool(practice_allowed),
        "must_follow_exact_mode": False,
        "hard_boundaries": [
            "no_diagnosis",
            "no_spiritual_authority",
            "no_raw_kb_quote_dumping",
            "no_unsolicited_practice",
        ],
    }


def render_writer_freedom_contract_prompt_block(
    *,
    freedom_contract: dict[str, Any],
) -> str:
    hard_boundaries = [
        str(item)
        for item in list(freedom_contract.get("hard_boundaries", []) or [])
        if str(item).strip()
    ]
    return (
        f"version={freedom_contract.get('version', WRITER_FREEDOM_CONTRACT_VERSION)}\n"
        f"freedom_level={freedom_contract.get('freedom_level', 'guided')}\n"
        f"mode_hint={freedom_contract.get('mode_hint', 'reflect')}\n"
        f"mode_is_hint_not_cage={str(bool(freedom_contract.get('mode_is_hint_not_cage', True))).lower()}\n"
        f"practice_requires_gate={str(bool(freedom_contract.get('practice_requires_gate', True))).lower()}\n"
        f"question_limit={int(freedom_contract.get('question_limit', 1) or 1)}\n"
        f"hard_boundaries={','.join(hard_boundaries) if hard_boundaries else 'none'}"
    )


def build_prompt_compactness_report(
    *,
    kernel_prompt_block: str,
    writer_freedom_prompt_block: str,
    selection: dict[str, Any],
    principles_count: int,
    boundaries_count: int,
) -> dict[str, Any]:
    kernel_chars = len(str(kernel_prompt_block or ""))
    freedom_chars = len(str(writer_freedom_prompt_block or ""))
    selected_lenses_count = len(list(selection.get("selected_lenses", []) or []))
    combined_chars = kernel_chars + freedom_chars
    within_budget = (
        kernel_chars <= MAX_KERNEL_PROMPT_CHARS
        and freedom_chars <= MAX_FREEDOM_PROMPT_CHARS
        and combined_chars <= MAX_COMBINED_PROMPT_CHARS
        and selected_lenses_count <= MAX_SELECTED_LENSES
    )
    return {
        "philosophy_kernel_prompt_block_chars": kernel_chars,
        "writer_freedom_contract_chars": freedom_chars,
        "combined_chars": combined_chars,
        "selected_lenses_count": selected_lenses_count,
        "principles_count": int(principles_count),
        "boundaries_count": int(boundaries_count),
        "budgets": {
            "max_kernel_chars": MAX_KERNEL_PROMPT_CHARS,
            "max_freedom_chars": MAX_FREEDOM_PROMPT_CHARS,
            "max_combined_chars": MAX_COMBINED_PROMPT_CHARS,
            "max_selected_lenses": MAX_SELECTED_LENSES,
            "max_principles_in_prompt": MAX_PRINCIPLES_IN_PROMPT,
            "max_boundaries_in_prompt": MAX_BOUNDARIES_IN_PROMPT,
        },
        "within_budget": bool(within_budget),
    }


def build_philosophy_kernel_runtime_payload(
    *,
    user_message: str,
    safety_active: bool,
    response_mode: str,
    practice_allowed: bool,
    kernel_enabled: bool = True,
) -> dict[str, Any]:
    selection = select_philosophy_lenses(
        user_message=user_message,
        safety_active=safety_active,
        response_mode=response_mode,
        kernel_enabled=kernel_enabled,
    )
    prompt_block = render_kernel_prompt_block(selection=selection, kernel=KERNEL_V1)
    writer_freedom_contract = build_writer_freedom_contract(
        response_mode=response_mode,
        practice_allowed=practice_allowed,
    )
    writer_freedom_prompt_block = render_writer_freedom_contract_prompt_block(
        freedom_contract=writer_freedom_contract
    )
    prompt_compactness = build_prompt_compactness_report(
        kernel_prompt_block=prompt_block,
        writer_freedom_prompt_block=writer_freedom_prompt_block,
        selection=selection,
        principles_count=min(len(KERNEL_V1.principles), MAX_PRINCIPLES_IN_PROMPT),
        boundaries_count=min(len(KERNEL_V1.boundaries), MAX_BOUNDARIES_IN_PROMPT),
    )
    return {
        "kernel_version": PHILOSOPHY_KERNEL_VERSION,
        "kernel_enabled": bool(kernel_enabled),
        "quote_policy": "internal_lens_not_citation",
        "practice_policy": "gate_required",
        "selection": selection,
        "prompt_block": prompt_block,
        "writer_freedom_contract": writer_freedom_contract,
        "writer_freedom_prompt_block": writer_freedom_prompt_block,
        "prompt_compactness": prompt_compactness,
    }


__all__ = [
    "PHILOSOPHY_KERNEL_VERSION",
    "WRITER_FREEDOM_CONTRACT_VERSION",
    "PhilosophyKernel",
    "KERNEL_V1",
    "build_philosophy_kernel",
    "select_philosophy_lenses",
    "render_kernel_prompt_block",
    "build_philosophy_kernel_prompt_block",
    "build_prompt_compactness_report",
    "render_writer_freedom_contract_prompt_block",
    "build_writer_freedom_contract",
    "build_philosophy_kernel_runtime_payload",
    "MAX_KERNEL_PROMPT_CHARS",
    "MAX_FREEDOM_PROMPT_CHARS",
    "MAX_COMBINED_PROMPT_CHARS",
    "MAX_SELECTED_LENSES",
]
