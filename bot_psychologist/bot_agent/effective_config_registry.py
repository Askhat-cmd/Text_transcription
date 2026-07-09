from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from bot_agent.config import config
from bot_agent.multiagent.thread_storage import thread_storage
from bot_agent.runtime_config import RuntimeConfig


FlagStatus = Literal[
    "secret",
    "active_tunable",
    "frozen_constant",
    "retirement_candidate_deferred",
]
FlagSource = Literal["env", "constant"]

REGISTRY_SCHEMA_VERSION = "effective_config_registry_v1"
TOTAL_FLAG_COUNT = 103
EXPECTED_ENV_EDITABLE_COUNT = 35
EXPECTED_NON_ENV_EDITABLE_CONFIG_KEYS = [
    "ENABLE_CACHING",
    "LLM_MAX_TOKENS",
    "LLM_MODEL",
    "LLM_TEMPERATURE",
    "TOP_K_BLOCKS",
]
MULTIAGENT_ENABLED_COMPAT_DEFAULT = "off"
NEO_MINDBOT_ENABLED_COMPAT_DEFAULT = "off"
LEGACY_PIPELINE_ENABLED_DEFAULT = "off"
DIAGNOSTIC_CENTER_CREATOR_USER_ID_DEFAULT = "creator"
DIAGNOSTIC_CENTER_DEVELOPER_USER_IDS_DEFAULT = ""
THREAD_STORAGE_DIR_DEFAULT = (
    Path(__file__).resolve().parents[1] / "data" / "threads"
).resolve()
TELEGRAM_ENABLED_DEFAULT = False
TELEGRAM_MODE_DEFAULT = "mock"
TELEGRAM_WEBHOOK_URL_DEFAULT = None
TELEGRAM_POLLING_TIMEOUT_DEFAULT = 30
TELEGRAM_POLLING_RETRY_DELAY_DEFAULT = 5.0
TELEGRAM_POLLING_MAX_RETRY_DELAY_DEFAULT = 60.0
TELEGRAM_ALLOWED_UPDATES_DEFAULT: tuple[str, ...] = ("message",)

SECRET_FLAGS = (
    "ADMIN_ACCESS_KEY",
    "ADMIN_INVITE_KEY",
    "ADMIN_USERNAME",
    "DEV_API_KEY",
    "INTERNAL_TELEGRAM_KEY",
    "OPENAI_API_KEY",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_WEBHOOK_SECRET",
    "TEST_API_KEY",
    "VOYAGE_API_KEY",
)

FROZEN_CONSTANT_FLAGS = (
    "AUTHOR_BLEND_MODE",
    "BOT_DB_PATH",
    "DATA_ROOT",
    "DEBUG",
    "DIAGNOSTIC_CENTER_CREATOR_USER_ID",
    "DIAGNOSTIC_CENTER_DEVELOPER_USER_IDS",
    "EMBEDDING_DEVICE",
    "EMBEDDING_MODEL",
    "MULTIAGENT_ENABLED",
    "NEO_MINDBOT_ENABLED",
    "PRIMARY_MODEL",
    "PROMPT_MODE_OVERRIDES_SD",
    "RECENT_WINDOW",
    "RERANKER_BLOCK_THRESHOLD",
    "RERANKER_CONFIDENCE_THRESHOLD",
    "RERANKER_ENABLED",
    "RERANKER_MODE_WHITELIST",
    "SUMMARIZER_FALLBACK_ON_EMPTY",
    "SUMMARIZER_FALLBACK_RETRIES",
    "SUMMARIZER_MIN_TURNS",
    "SUMMARIZER_MODEL",
    "SUMMARIZER_REASONING_EFFORT",
    "SUMMARY_WINDOW_SIZE",
    "TELEGRAM_ALLOWED_UPDATES",
    "TELEGRAM_ENABLED",
    "TELEGRAM_MODE",
    "TELEGRAM_POLLING_MAX_RETRY_DELAY",
    "TELEGRAM_POLLING_RETRY_DELAY",
    "TELEGRAM_POLLING_TIMEOUT",
    "TELEGRAM_WEBHOOK_URL",
    "THREAD_STORAGE_DIR",
    "TURN_LLM_SUMMARY_DEBUG_PREVIEW_CHARS",
    "TURN_LLM_SUMMARY_ENABLED",
    "TURN_LLM_SUMMARY_MAX_INPUT_CHARS",
    "TURN_LLM_SUMMARY_MAX_PENDING_PER_RUN",
    "TURN_LLM_SUMMARY_MAX_RETRIES",
    "TURN_LLM_SUMMARY_MAX_SUMMARY_CHARS",
    "TURN_LLM_SUMMARY_MODEL",
    "TURN_LLM_SUMMARY_PROVIDER",
    "TURN_LLM_SUMMARY_TIMEOUT_SECONDS",
    "TURN_LLM_SUMMARY_USE_IN_CONTEXT",
)

RECLASSIFIED_ACTIVE_FLAGS = (
    "ARCHIVE_RETENTION_DAYS",
    "AUTO_CLEANUP_ENABLED",
    "CLASSIFIER_MODEL",
    "CONVERSATION_HISTORY_DEPTH",
    "ENABLE_CONVERSATION_SUMMARY",
    "ENABLE_KNOWLEDGE_GRAPH",
    "ENABLE_SEMANTIC_MEMORY",
    "ENABLE_SESSION_STORAGE",
    "ENABLE_STREAMING",
    "MAX_CONTEXT_SIZE",
    "MAX_CONVERSATION_TURNS",
    "REASONING_EFFORT",
    "SEMANTIC_MAX_CHARS",
    "SEMANTIC_MIN_SIMILARITY",
    "SEMANTIC_SEARCH_TOP_K",
    "SESSION_RETENTION_DAYS",
    "SUMMARY_MAX_CHARS",
    "SUMMARY_UPDATE_INTERVAL",
    "WARMUP_ON_START",
)

ACTIVE_ENV_FLAGS = (
    "ALL_BLOCKS_MERGED_PATH",
    "APP_ENV",
    "BOT_DB_CIRCUIT_BREAKER_ENABLED",
    "BOT_DB_CIRCUIT_BREAKER_TTL_SECONDS",
    "BOT_DB_FAST_FAIL_ON_503",
    "BOT_DB_TIMEOUT",
    "BOT_DB_URL",
    "CHROMA_API_URL",
    "CHROMA_COLLECTION",
    "DATA_SOURCE",
    "DB_EXPORT_FILE",
    "DB_JSON_DIR",
    "DECISION_GATE_RULE_THRESHOLD",
    "DEGRADED_MODE",
    "KNOWLEDGE_SOURCE",
    "RETRIEVAL_TOP_K",
)

ACTIVE_EDITABLE_ENV_FLAGS = (
    "CONFIDENCE_CAP_HIGH",
    "CONFIDENCE_CAP_LOW",
    "CONFIDENCE_CAP_MEDIUM",
    "CONFIDENCE_CAP_ZERO",
    "DIALOGUE_PROFILE",
    "FAST_DETECTOR_CONFIDENCE_THRESHOLD",
    "FAST_DETECTOR_ENABLED",
    "FREE_CONVERSATION_MODE",
    "MAX_TOKENS",
    "MAX_TOKENS_SOFT_CAP",
    "MIN_RELEVANCE_SCORE",
    "STATE_CLASSIFIER_CONFIDENCE_THRESHOLD",
    "STATE_CLASSIFIER_ENABLED",
    "VOYAGE_ENABLED",
    "VOYAGE_MODEL",
    "VOYAGE_TOP_K",
)

RETIREMENT_CANDIDATE_FLAGS = ("LEGACY_PIPELINE_ENABLED",)


@dataclass(frozen=True)
class EffectiveConfigFlag:
    name: str
    status: FlagStatus
    source: FlagSource
    admin_hot_editable: bool
    notes: str


def _note_for_secret() -> str:
    return "Secret flag: export only is_set, never raw value."


def _note_for_frozen_constant(name: str) -> str:
    if name.startswith("TELEGRAM_"):
        return (
            "Frozen constant in PRD-047.41; reactivate as real config when Telegram "
            "deployment PRD lands."
        )
    if name in {"MULTIAGENT_ENABLED", "NEO_MINDBOT_ENABLED"}:
        return "Deprecated compatibility marker kept as literal constant after PRD-036."
    return "Frozen constant per PRD-047.41 bucket A."


def _note_for_reclassified_active() -> str:
    return (
        "Reclassified from frozen_default_only per PRD-047.41, owner decision (a) "
        "2026-07-09; no EDITABLE_CONFIG/UI change."
    )


def _note_for_active_env() -> str:
    return "Active env-backed runtime surface; visible in registry, not admin hot-editable."


def _note_for_active_editable() -> str:
    return "Active env-backed runtime surface already represented in EDITABLE_CONFIG."


def _note_for_retirement_candidate() -> str:
    return "Deferred legacy compatibility marker awaiting explicit owner decision."


def _register(
    target: dict[str, EffectiveConfigFlag],
    names: tuple[str, ...],
    *,
    status: FlagStatus,
    source: FlagSource,
    admin_hot_editable: bool,
    note_factory,
) -> None:
    for name in names:
        if name in target:
            raise RuntimeError(f"duplicate_effective_config_flag:{name}")
        target[name] = EffectiveConfigFlag(
            name=name,
            status=status,
            source=source,
            admin_hot_editable=admin_hot_editable,
            notes=note_factory(name) if callable(note_factory) else str(note_factory),
        )


def _build_registry() -> dict[str, EffectiveConfigFlag]:
    registry: dict[str, EffectiveConfigFlag] = {}
    _register(
        registry,
        SECRET_FLAGS,
        status="secret",
        source="env",
        admin_hot_editable=False,
        note_factory=lambda _name: _note_for_secret(),
    )
    _register(
        registry,
        FROZEN_CONSTANT_FLAGS,
        status="frozen_constant",
        source="constant",
        admin_hot_editable=False,
        note_factory=_note_for_frozen_constant,
    )
    _register(
        registry,
        RECLASSIFIED_ACTIVE_FLAGS,
        status="active_tunable",
        source="env",
        admin_hot_editable=True,
        note_factory=lambda _name: _note_for_reclassified_active(),
    )
    _register(
        registry,
        ACTIVE_ENV_FLAGS,
        status="active_tunable",
        source="env",
        admin_hot_editable=False,
        note_factory=lambda _name: _note_for_active_env(),
    )
    _register(
        registry,
        ACTIVE_EDITABLE_ENV_FLAGS,
        status="active_tunable",
        source="env",
        admin_hot_editable=True,
        note_factory=lambda _name: _note_for_active_editable(),
    )
    _register(
        registry,
        RETIREMENT_CANDIDATE_FLAGS,
        status="retirement_candidate_deferred",
        source="env",
        admin_hot_editable=False,
        note_factory=lambda _name: _note_for_retirement_candidate(),
    )
    return dict(sorted(registry.items()))


FLAG_REGISTRY = _build_registry()


def _validate_registry() -> None:
    if len(FLAG_REGISTRY) != TOTAL_FLAG_COUNT:
        raise RuntimeError(
            f"effective_config_registry_flag_count_mismatch:{len(FLAG_REGISTRY)}:{TOTAL_FLAG_COUNT}"
        )
    admin_hot_editable = {
        name for name, entry in FLAG_REGISTRY.items() if entry.admin_hot_editable
    }
    editable_env_intersection = set(RuntimeConfig.EDITABLE_CONFIG).intersection(FLAG_REGISTRY)
    if admin_hot_editable != editable_env_intersection:
        raise RuntimeError(
            "effective_config_registry_editable_alignment_mismatch:"
            f"{sorted(admin_hot_editable)} != {sorted(editable_env_intersection)}"
        )
    if len(admin_hot_editable) != EXPECTED_ENV_EDITABLE_COUNT:
        raise RuntimeError(
            "effective_config_registry_editable_count_mismatch:"
            f"{len(admin_hot_editable)}:{EXPECTED_ENV_EDITABLE_COUNT}"
        )
    non_env_editable = sorted(set(RuntimeConfig.EDITABLE_CONFIG) - set(FLAG_REGISTRY))
    if non_env_editable != EXPECTED_NON_ENV_EDITABLE_CONFIG_KEYS:
        raise RuntimeError(
            "effective_config_registry_non_env_editable_mismatch:"
            f"{non_env_editable} != {EXPECTED_NON_ENV_EDITABLE_CONFIG_KEYS}"
        )


_validate_registry()


def _thread_storage_dir_value() -> str:
    storage_dir = getattr(thread_storage, "_dir", None)
    if storage_dir is not None:
        return str(Path(storage_dir).expanduser().resolve())
    return str(THREAD_STORAGE_DIR_DEFAULT)


def _diagnostic_center_developer_ids_value() -> list[str]:
    if DIAGNOSTIC_CENTER_DEVELOPER_USER_IDS_DEFAULT.strip():
        raw = DIAGNOSTIC_CENTER_DEVELOPER_USER_IDS_DEFAULT
        return [item.strip() for item in raw.replace(",", "\n").splitlines() if item.strip()]
    return [DIAGNOSTIC_CENTER_CREATOR_USER_ID_DEFAULT]


_SPECIAL_VALUE_GETTERS: dict[str, Any] = {
    "APP_ENV": lambda: os.getenv("APP_ENV", ""),
    "DIAGNOSTIC_CENTER_CREATOR_USER_ID": lambda: DIAGNOSTIC_CENTER_CREATOR_USER_ID_DEFAULT,
    "DIAGNOSTIC_CENTER_DEVELOPER_USER_IDS": _diagnostic_center_developer_ids_value,
    "LEGACY_PIPELINE_ENABLED": lambda: os.getenv(
        "LEGACY_PIPELINE_ENABLED",
        LEGACY_PIPELINE_ENABLED_DEFAULT,
    ),
    "MULTIAGENT_ENABLED": lambda: MULTIAGENT_ENABLED_COMPAT_DEFAULT,
    "NEO_MINDBOT_ENABLED": lambda: NEO_MINDBOT_ENABLED_COMPAT_DEFAULT,
    "PRIMARY_MODEL": lambda: getattr(config, "LLM_MODEL"),
    "TELEGRAM_ALLOWED_UPDATES": lambda: list(TELEGRAM_ALLOWED_UPDATES_DEFAULT),
    "TELEGRAM_ENABLED": lambda: TELEGRAM_ENABLED_DEFAULT,
    "TELEGRAM_MODE": lambda: TELEGRAM_MODE_DEFAULT,
    "TELEGRAM_POLLING_MAX_RETRY_DELAY": lambda: TELEGRAM_POLLING_MAX_RETRY_DELAY_DEFAULT,
    "TELEGRAM_POLLING_RETRY_DELAY": lambda: TELEGRAM_POLLING_RETRY_DELAY_DEFAULT,
    "TELEGRAM_POLLING_TIMEOUT": lambda: TELEGRAM_POLLING_TIMEOUT_DEFAULT,
    "TELEGRAM_WEBHOOK_URL": lambda: TELEGRAM_WEBHOOK_URL_DEFAULT,
    "THREAD_STORAGE_DIR": _thread_storage_dir_value,
}


def _serialize_value(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, tuple):
        return [_serialize_value(item) for item in value]
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize_value(item) for key, item in value.items()}
    return value


def _is_secret_set(name: str) -> bool:
    return bool(str(os.getenv(name, "")).strip())


def _resolve_effective_value(name: str) -> Any:
    getter = _SPECIAL_VALUE_GETTERS.get(name)
    if getter is not None:
        return getter() if callable(getter) else getter
    attr_name = "LLM_MODEL" if name == "PRIMARY_MODEL" else name
    if hasattr(config, attr_name):
        return getattr(config, attr_name)
    return os.getenv(name, "")


def get_flag_registry() -> dict[str, EffectiveConfigFlag]:
    return FLAG_REGISTRY


def get_admin_hot_editable_env_flags() -> set[str]:
    return {name for name, entry in FLAG_REGISTRY.items() if entry.admin_hot_editable}


def get_non_env_editable_config_keys() -> list[str]:
    return list(EXPECTED_NON_ENV_EDITABLE_CONFIG_KEYS)


def build_effective_config_payload() -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    source_counts: dict[str, int] = {}
    entries: dict[str, Any] = {}

    for name, entry in FLAG_REGISTRY.items():
        status_counts[entry.status] = status_counts.get(entry.status, 0) + 1
        source_counts[entry.source] = source_counts.get(entry.source, 0) + 1
        current_value = (
            {"is_set": _is_secret_set(name)}
            if entry.status == "secret"
            else _serialize_value(_resolve_effective_value(name))
        )
        entries[name] = {
            "status": entry.status,
            "source": entry.source,
            "admin_hot_editable": entry.admin_hot_editable,
            "notes": entry.notes,
            "current_value": current_value,
        }

    return {
        "schema_version": REGISTRY_SCHEMA_VERSION,
        "flag_count": len(FLAG_REGISTRY),
        "status_counts": dict(sorted(status_counts.items())),
        "source_counts": dict(sorted(source_counts.items())),
        "admin_hot_editable_count": len(get_admin_hot_editable_env_flags()),
        "editable_config_env_intersection_count": len(
            set(RuntimeConfig.EDITABLE_CONFIG).intersection(FLAG_REGISTRY)
        ),
        "editable_config_non_env_keys": list(EXPECTED_NON_ENV_EDITABLE_CONFIG_KEYS),
        "entries": entries,
    }


def build_compat_env_flags_snapshot() -> dict[str, str]:
    return {
        "MULTIAGENT_ENABLED": str(_resolve_effective_value("MULTIAGENT_ENABLED")),
        "LEGACY_PIPELINE_ENABLED": str(_resolve_effective_value("LEGACY_PIPELINE_ENABLED")),
        "NEO_MINDBOT_ENABLED": str(_resolve_effective_value("NEO_MINDBOT_ENABLED")),
    }
