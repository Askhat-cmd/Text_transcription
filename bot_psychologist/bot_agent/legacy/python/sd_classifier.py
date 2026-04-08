"""
SD Classifier - определяет уровень Спиральной Динамики пользователя.

Стратегия (3 уровня):
  1. Быстрая эвристика по ключевым словам (0 API-вызовов)
  2. LLM-классификация если эвристика дала confidence ниже порога
  3. Накопленный профиль если достигнуты пороги стабильности

Принцип безопасности: при неопределённости - выбирать уровень НИЖЕ.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from openai import OpenAI
from .config import config
from .fast_detector import detect_sd_level
from .feature_flags import feature_flags

logger = logging.getLogger(__name__)

# PRD 11.0 Wave 1 protective barrier:
# SD classifier is frozen out of active Neo runtime.
SD_CLASSIFIER_ENABLED = feature_flags.enabled("SD_CLASSIFIER_ENABLED")
assert not SD_CLASSIFIER_ENABLED, (
    "SD classifier is disabled in Neo runtime (PRD 11.0 soft freeze). "
    "Do not enable SD_CLASSIFIER_ENABLED in active runtime."
)

SD_LEVELS_ORDER = [
    "BEIGE",
    "PURPLE",
    "RED",
    "BLUE",
    "ORANGE",
    "GREEN",
    "YELLOW",
    "TURQUOISE",
]

SD_KEYWORDS: Dict[str, List[str]] = {
    "BEIGE": ["не могу дышать", "страшно умереть", "физически плохо", "выживание", "теряю сознание"],
    "PURPLE": [
        "традиции",
        "предки",
        "семья решает",
        "так принято",
        "ритуал",
        "боюсь сглазить",
        "судьба",
        "порча",
        "у нас в семье",
    ],
    # RED — агрессия, доминирование, импульсивность, "я хочу власти/силы"
    "RED": [
        # агрессия и доминирование
        "бесит", "злит", "ненавижу", "достало", "достали", "надоело",
        "все должны", "я лучше", "никто не понимает меня",
        "никто не уважает меня", "не уважает", "не уважают",
        "заставить", "подчинить", "контролировать других",
        "накажу", "не буду терпеть", "должны мне",
        # импульсивность
        "хочу прямо сейчас", "немедленно", "не могу ждать",
        "он меня", "они меня", "надоело терпеть",
    ],
    # NOT_RED — интеллектуальный поиск (НЕ RED, это GREEN/YELLOW)
    "NOT_RED": [
        "хочу разобраться", "хочу понять", "хочу знать", "хочу изучить",
        "понять", "разобраться", "изучить", "исследовать",
        "интересно", "объясни", "расскажи", "научи",
    ],
    "BLUE": [
        "должен",
        "должна",
        "обязан",
        "грех",
        "правильно",
        "нарушил",
        "вина",
        "чувствую вину",
        "дисциплина",
        "как положено",
        "так нельзя",
    ],
    "ORANGE": [
        "успех",
        "результат",
        "эффективно",
        "цели",
        "выгода",
        "карьера",
        "логично",
        "что это даст",
        "стратегия",
        "не работает",
    ],
    "GREEN": [
        "чувствую",
        "хочу понять",
        "принятие",
        "поддержка",
        "вместе",
        "связь",
        "тревога",
        "эмпатия",
        "не могу справиться",
    ],
    "YELLOW": [
        "замечаю паттерн",
        "замечаю что я",
        "система",
        "интеграция",
        "метанаблюдение",
        "контекст",
        "откуда это",
        "всегда так реагирую",
    ],
    "TURQUOISE": ["единство", "целостность быятия", "всё одно", "трансцендентность", "планетарное"],
}

SD_CLASSIFIER_SYSTEM_PROMPT = """
Ты - эксперт по Спиральной Динамике Клэра Грейвза.
Определи, с какого уровня сознания говорит человек.

Анализируй: язык, ценности, что считается проблемой, что считается решением,
эмоциональный фокус, отношение к правилам и другим людям.

УРОВНИ:
- BEIGE: выживание, физические страхи, "не могу", инстинктивные реакции
- PURPLE: "так принято", семья/коллектив важнее личного, магическое мышление
- RED: "я хочу", сила, власть, немедленный результат, ego-центризм
- BLUE: "должен/обязан", правила, вина, дисциплина, иерархия
- ORANGE: цели, эффективность, "что мне даёт", логика, конкуренция
- GREEN: чувства, эмпатия, принятие, "мы вместе", самопонимание
- YELLOW: паттерны, системность, метанаблюдение, "замечаю что..."
- TURQUOISE: единство всего, трансличностное, целостность

ПРАВИЛА:
1. Смотри на то, ЧТО человек считает проблемой и ЧТО считает решением
2. Если два уровня равновесны - выбери более НИЗКИЙ (безопаснее)
3. Острое эмоциональное состояние временно снижает доступный уровень
4. confidence < 0.65 - сигнал неопределённости

Верни ТОЛЬКО JSON:
{"primary":"LEVEL","secondary":"LEVEL_or_null","confidence":0.0-1.0,"indicator":"краткий маркер"}
"""


def _default_settings() -> Dict[str, object]:
    return {
        "model": "gpt-4o-mini",
        "temperature": 0.1,
        "heuristic_confidence_threshold": 0.65,
        "profile_min_messages": 15,
        "profile_min_confidence": 0.80,
        "update_profile_every_n_messages": 5,
        "uncertainty_fallback": "one_level_down",
        "default_level": "GREEN",
        "compatibility_base": {
            "BEIGE": ["BEIGE", "PURPLE"],
            "PURPLE": ["PURPLE", "RED"],
            "RED": ["RED", "BLUE"],
            "BLUE": ["BLUE", "ORANGE"],
            "ORANGE": ["ORANGE", "GREEN"],
            "GREEN": ["GREEN", "YELLOW"],
            "YELLOW": ["GREEN", "YELLOW", "TURQUOISE"],
            "TURQUOISE": ["YELLOW", "TURQUOISE"],
        },
        "crisis_overrides": [
            {"condition": ["ORANGE", "overwhelmed"], "allowed": ["BLUE", "ORANGE"]},
            {"condition": ["ORANGE", "crisis"], "allowed": ["BLUE", "ORANGE"]},
            {"condition": ["BLUE", "overwhelmed"], "allowed": ["GREEN", "BLUE"]},
            {"condition": ["BLUE", "crisis"], "allowed": ["GREEN", "BLUE"]},
            {"condition": ["GREEN", "overwhelmed"], "allowed": ["ORANGE", "GREEN"]},
            {"condition": ["GREEN", "exhausted"], "allowed": ["ORANGE", "GREEN"]},
            {"condition": ["RED", "crisis"], "allowed": ["PURPLE", "RED"]},
            {"condition": ["RED", "overwhelmed"], "allowed": ["PURPLE", "RED"]},
            {"condition": ["YELLOW", "overwhelmed"], "allowed": ["GREEN", "YELLOW"]},
            {"condition": ["YELLOW", "crisis"], "allowed": ["GREEN", "YELLOW"]},
            {"condition": ["ORANGE", "stagnant"], "allowed": ["GREEN", "ORANGE"]},
        ],
    }


def _load_sd_settings() -> Dict[str, object]:
    defaults = _default_settings()
    config_path = Path(__file__).resolve().parents[1] / "config" / "sd_classification.yaml"
    if not config_path.exists():
        logger.warning(f"[SD_CLASSIFIER] config not found: {config_path}, using defaults")
        return defaults
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        section = loaded.get("sd_classification", {})
        merged = dict(defaults)
        merged.update(section)
        return merged
    except Exception as exc:
        logger.warning(f"[SD_CLASSIFIER] failed to load config: {exc}, using defaults")
        return defaults


_SD_SETTINGS = _load_sd_settings()
DEFAULT_LEVEL = str(_SD_SETTINGS.get("default_level", "GREEN"))
SD_COMPATIBILITY_BASE: Dict[str, List[str]] = dict(_SD_SETTINGS.get("compatibility_base", {}))


def get_sd_settings() -> Dict[str, object]:
    """Вернуть загруженные SD-настройки (копия)."""
    return dict(_SD_SETTINGS)


@dataclass
class SDClassificationResult:
    primary: str
    secondary: Optional[str]
    confidence: float
    indicator: str
    method: str  # "heuristic" | "llm" | "profile" | "fallback"
    allowed_blocks: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.allowed_blocks = SD_COMPATIBILITY_BASE.get(self.primary, [DEFAULT_LEVEL])

    def to_detail(self) -> Dict[str, object]:
        return {
            "method": self.method,
            "primary": self.primary,
            "secondary": self.secondary,
            "confidence": float(self.confidence),
            "indicator": self.indicator,
            "allowed_levels": [str(level) for level in (self.allowed_blocks or [])],
        }


class SDCompatibilityResolver:
    """Динамическая матрица совместимости уровней СД."""

    def __init__(self, compatibility_base: Optional[Dict[str, List[str]]] = None) -> None:
        self.compatibility_base = compatibility_base or SD_COMPATIBILITY_BASE
        self.crisis_overrides = self._build_crisis_overrides()

    def _build_crisis_overrides(self) -> Dict[tuple, List[str]]:
        raw = _SD_SETTINGS.get("crisis_overrides", [])
        overrides: Dict[tuple, List[str]] = {}
        for item in raw if isinstance(raw, list) else []:
            try:
                condition = item.get("condition", [])
                allowed = item.get("allowed", [])
                if len(condition) != 2 or not allowed:
                    continue
                key = (str(condition[0]).upper(), str(condition[1]).lower())
                overrides[key] = [str(level).upper() for level in allowed]
            except Exception:
                continue
        return overrides

    def get_allowed_levels(
        self,
        sd_level: str,
        user_state: Optional[str] = None,
        sd_secondary: Optional[str] = None,
        sd_confidence: float = 1.0,
        is_first_session: bool = False,
    ) -> List[str]:
        heuristic_threshold = float(_SD_SETTINGS.get("heuristic_confidence_threshold", 0.65))
        low_confidence_threshold = max(0.0, min(heuristic_threshold - 0.05, 0.60))
        sd_level = (sd_level or DEFAULT_LEVEL).upper()

        if sd_confidence < low_confidence_threshold:
            safer_level = self._one_level_down(sd_level)
            allowed = list(self.compatibility_base.get(safer_level, [DEFAULT_LEVEL]))
            logger.info(
                f"conservative: {sd_level}->{safer_level}, allowed={allowed}"
            )
            return allowed

        state_norm = (user_state or "").lower()
        crisis_key = (sd_level, state_norm)
        if crisis_key in self.crisis_overrides:
            allowed = self.crisis_overrides[crisis_key]
            return allowed

        if is_first_session:
            allowed = list(self.compatibility_base.get(sd_level, [DEFAULT_LEVEL]))
            return allowed

        allowed = list(self.compatibility_base.get(sd_level, [DEFAULT_LEVEL]))
        if sd_secondary and sd_secondary != sd_level:
            try:
                secondary = sd_secondary.upper()
                secondary_idx = SD_LEVELS_ORDER.index(secondary)
                primary_idx = SD_LEVELS_ORDER.index(sd_level)
                if secondary_idx > primary_idx and secondary not in allowed:
                    allowed.append(secondary)
            except ValueError:
                pass

        return allowed

    @staticmethod
    def _one_level_down(level: str) -> str:
        idx = SD_LEVELS_ORDER.index(level) if level in SD_LEVELS_ORDER else SD_LEVELS_ORDER.index(DEFAULT_LEVEL)
        return SD_LEVELS_ORDER[max(0, idx - 1)]


class SDClassifier:
    """Классификатор уровня СД пользователя: эвристика -> LLM -> профиль."""

    def __init__(self, model: Optional[str] = None, temperature: Optional[float] = None):
        # Приоритет: явный аргумент → PRIMARY_MODEL из .env → YAML default → hardcoded default
        # Это гарантирует что SDClassifier всегда использует ту же модель, что и весь бот
        self.model = model or config.CLASSIFIER_MODEL or str(_SD_SETTINGS.get("model", "gpt-4o-mini"))
        self.temperature = float(temperature if temperature is not None else _SD_SETTINGS.get("temperature", 0.1))
        logger.debug(f"[SD_CLASSIFIER] Initialized with model={self.model}")
        self.heuristic_threshold = float(_SD_SETTINGS.get("heuristic_confidence_threshold", 0.65))
        self.profile_min_messages = int(_SD_SETTINGS.get("profile_min_messages", 15))
        self.profile_min_confidence = float(_SD_SETTINGS.get("profile_min_confidence", 0.80))
        self.default_level = str(_SD_SETTINGS.get("default_level", "GREEN")).upper()
        self.client: Optional[OpenAI] = None
        try:
            self.client = OpenAI()
        except Exception as exc:
            logger.warning(f"[SD_CLASSIFIER] OpenAI client unavailable: {exc}")

    def classify(
        self,
        message: str,
        conversation_history: Optional[List[dict]] = None,
        user_sd_profile: Optional[dict] = None,
    ) -> SDClassificationResult:
        if (
            user_sd_profile
            and user_sd_profile.get("message_count", 0) >= self.profile_min_messages
            and user_sd_profile.get("confidence", 0) >= self.profile_min_confidence
            and user_sd_profile.get("primary")
        ):
            return SDClassificationResult(
                primary=str(user_sd_profile["primary"]).upper(),
                secondary=(str(user_sd_profile["secondary"]).upper() if user_sd_profile.get("secondary") else None),
                confidence=float(user_sd_profile["confidence"]),
                indicator="accumulated_profile",
                method="profile",
            )

        fast = detect_sd_level(message) if feature_flags.enabled("ENABLE_FAST_SD_DETECTOR") else None
        if fast and fast.confidence >= 0.85:
            logger.info(
                f"[SD_CLASSIFIER] fast detector hit: {fast.label} "
                f"(confidence={fast.confidence:.2f}, indicator={fast.indicator})"
            )
            return SDClassificationResult(
                primary=fast.label,
                secondary=None,
                confidence=float(fast.confidence),
                indicator=fast.indicator,
                method="fast",
            )

        heuristic = self._heuristic_classify(message, conversation_history)
        if heuristic.confidence >= self.heuristic_threshold:
            return heuristic

        return self._llm_classify(message, conversation_history)

    async def classify_user(
        self,
        message: str,
        conversation_history: Optional[List[dict]] = None,
        user_sd_profile: Optional[dict] = None,
    ) -> SDClassificationResult:
        """Async wrapper for parallel classification."""
        return await asyncio.to_thread(
            self.classify,
            message,
            conversation_history,
            user_sd_profile,
        )

    def _heuristic_classify(
        self,
        message: str,
        history: Optional[List[dict]] = None,
    ) -> SDClassificationResult:
        text = (message or "").lower()
        if history:
            for turn in history[-5:]:
                text += " " + str(turn.get("content") or "").lower()

        # Проверка NOT_RED — интеллектуальный поиск (GREEN/YELLOW)
        # Если найдены NOT_RED маркеры — понижаем RED score до 0
        not_red_keywords = SD_KEYWORDS.get("NOT_RED", [])
        is_not_red = any(keyword in text for keyword in not_red_keywords)

        scores = {level: 0 for level in SD_LEVELS_ORDER}
        for level, keywords in SD_KEYWORDS.items():
            # Пропускаем NOT_RED — это не уровень, а фильтр
            if level == "NOT_RED":
                continue
            for keyword in keywords:
                if keyword in text:
                    scores[level] += 1

        # Если обнаружены NOT_RED маркеры — RED не может быть лучшим
        if is_not_red:
            scores["RED"] = 0

        best_level = max(scores, key=scores.get)
        best_score = scores[best_level]
        if best_score == 0:
            return SDClassificationResult(
                primary=self.default_level,
                secondary=None,
                confidence=0.40,
                indicator="no_keywords_found",
                method="heuristic",
            )

        total = sum(scores.values())
        confidence = min(0.85, (best_score / total) * 2) if total > 0 else 0.40
        sorted_levels = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        secondary = sorted_levels[1][0] if len(sorted_levels) > 1 and sorted_levels[1][1] > 0 else None
        return SDClassificationResult(
            primary=best_level,
            secondary=secondary,
            confidence=confidence,
            indicator=f"keywords_matched_{best_score}",
            method="heuristic",
        )

    def _llm_classify(
        self,
        message: str,
        history: Optional[List[dict]] = None,
    ) -> SDClassificationResult:
        if not self.client:
            return SDClassificationResult(
                primary=self.default_level,
                secondary=None,
                confidence=0.50,
                indicator="llm_client_unavailable",
                method="fallback",
            )

        context = ""
        if history:
            context = "\n".join(
                [f"Пользователь: {t['content']}" for t in history[-5:] if t.get("role") == "user"]
            )
        user_content = f"Текущее сообщение: {message}"
        if context:
            user_content = f"История:\n{context}\n\n{user_content}"

        try:
            token_param = config.get_token_param_name(self.model)
            request_params = {
                "model": self.model,
                token_param: 2000,
                "messages": [
                    {"role": "system", "content": SD_CLASSIFIER_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                "response_format": {"type": "json_object"},
            }
            if config.supports_custom_temperature(self.model):
                request_params["temperature"] = self.temperature

            response = self.client.chat.completions.create(**request_params)
            raw = (response.choices[0].message.content or "").strip()

            # Очистка markdown-обёртки (```json ... ``` или ``` ... ```)
            if "```" in raw:
                import re
                raw = re.sub(r"```(?:json)?\s*", "", raw).strip()

            # Защита от пустого ответа — GPT-5 mini иногда возвращает пустую строку
            if not raw:
                logger.warning("[SD_CLASSIFIER] LLM returned empty content, using fallback")
                return SDClassificationResult(
                    primary=self.default_level,
                    secondary=None,
                    confidence=0.50,
                    indicator="llm_empty_response",
                    method="fallback",
                )

            data = json.loads(raw)
            primary = str(data.get("primary", self.default_level)).upper()
            secondary = data.get("secondary")
            return SDClassificationResult(
                primary=primary,
                secondary=(str(secondary).upper() if secondary else None),
                confidence=float(data.get("confidence", 0.60)),
                indicator=str(data.get("indicator", "llm_classified")),
                method="llm",
            )
        except Exception as exc:
            logger.error(f"[SD_CLASSIFIER] LLM error: {exc}")
            return SDClassificationResult(
                primary=self.default_level,
                secondary=None,
                confidence=0.50,
                indicator="llm_fallback_on_error",
                method="fallback",
            )

    def one_level_down(self, level: str) -> str:
        idx = SD_LEVELS_ORDER.index(level) if level in SD_LEVELS_ORDER else SD_LEVELS_ORDER.index(self.default_level)
        return SD_LEVELS_ORDER[max(0, idx - 1)]


try:
    sd_classifier = SDClassifier()
    sd_compatibility_resolver = SDCompatibilityResolver()
except Exception as _e:
    logger.warning(f"[SD_CLASSIFIER] Deferred init due to: {_e}")
    sd_classifier = None  # type: ignore
    sd_compatibility_resolver = None  # type: ignore
