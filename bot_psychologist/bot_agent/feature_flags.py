"""Feature flags for PRD modernization phases."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(_PROJECT_ROOT / ".env")
_PROCESS_START_TIME_UTC = datetime.now(timezone.utc).isoformat()


_DEFAULTS: Dict[str, bool] = {
    # PRD 11.0 Wave 1 (Soft Freeze): Neo runtime is default.
    "NEO_MINDBOT_ENABLED": True,
    "LEGACY_PIPELINE_ENABLED": False,
    # Compatibility runtime switch.
    "DISABLE_USER_LEVEL_ADAPTER": True,
    # Explicit migration flag.
    "USER_LEVEL_ADAPTER_ENABLED": False,
    "PRE_ROUTING_ENABLED": False,
    # Neo runtime feature flags.
    "USE_NEW_DIAGNOSTICS_V1": True,
    "USE_DETERMINISTIC_ROUTE_RESOLVER": True,
    "USE_PROMPT_STACK_V2": True,
    "USE_OUTPUT_VALIDATION": True,
    "INFORMATIONAL_BRANCH_ENABLED": True,
    # Phase 1
    "ENABLE_EMBEDDING_PROVIDER": True,
    # Phase 2
    "ENABLE_CONDITIONAL_RERANKER": True,
    # Phase 3
    "ENABLE_FAST_STATE_DETECTOR": True,
    # Deprecated compatibility flag.
    # Multiagent runtime is always active after PRD-036.
    # Retained only for old tests/tools until PRD-041/PRD-042 cleanup.
    "MULTIAGENT_ENABLED": True,
    # PRD-046.1.6 controlled prompt-constraint pilot (default-off).
    "PROMPT_CONSTRAINT_PILOT_ENABLED": False,
    "PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED": True,
    "OVERLAY_SHADOW_TRACE_ENABLED": False,
    "WRITER_KB_PAYLOAD_ENABLED": False,
    "RETRIEVAL_CURRENT_TURN_FOCUS_ENABLED": False,
    "SEMANTIC_CARDS_PILOT_ENABLED": False,
}

_STRING_DEFAULTS: Dict[str, str] = {
    "THREAD_MANAGER_MODEL": "gpt-5-nano",
    "STATE_ANALYZER_MODEL": "gpt-5-nano",
    "WRITER_MODEL": "gpt-5-mini",
    "MULTIAGENT_LLM_TIMEOUT": "30",
    "MULTIAGENT_MAX_TOKENS": "600",
    "MULTIAGENT_TEMPERATURE": "0.7",
    "WRITER_MAX_TOKENS": "400",
    "WRITER_TEMPERATURE": "0.7",
    "MEMORY_RAG_N_RESULTS": "4",
    "MEMORY_RAG_MIN_SCORE": "0.45",
    "MEMORY_CONV_TURNS_DEFAULT": "6",
    "THREAD_STORAGE_DIR": "bot_psychologist/data/threads",
    # PRD-046.1.6 prompt-constraint pilot settings.
    "PROMPT_CONSTRAINT_PILOT_MODE": "shadow",
    "PROMPT_CONSTRAINT_PILOT_ALLOWED_USER_IDS": "",
    "PROMPT_CONSTRAINT_PILOT_TEST_USER_PREFIX": "pilot_",
    "PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_CHARS": "2500",
    "PROMPT_CONSTRAINT_PILOT_MAX_PROMPT_DELTA_RATIO": "0.35",
    "HYBRID_RETRIEVAL_PLANNER_MODE": "shadow",
    "HYBRID_RETRIEVAL_PLANNER_MODEL": "gpt-5-nano",
    "HYBRID_RETRIEVAL_PLANNER_MAX_TOKENS": "320",
    "OVERLAY_SHADOW_TRACE_MODE": "trace_only",
    "OVERLAY_SHADOW_OVERLAY_FILE": "TO_DO_LIST/logs/PRD-047.20/batch_1_accepted_overlay_preview.json",
    "OVERLAY_SHADOW_MAX_MATCHES": "5",
    "OVERLAY_SHADOW_MIN_SCORE": "0.0",
    "WRITER_KB_PAYLOAD_MAX_CHUNKS": "2",
    "WRITER_KB_PAYLOAD_MAX_TOTAL_CHARS": "3600",
    "WRITER_KB_PAYLOAD_EXCERPT_TARGET_CHARS": "1200",
    "WRITER_KB_PAYLOAD_EXCERPT_MAX_CHARS": "1600",
    "WRITER_KB_PAYLOAD_SENTENCE_BOUNDARY": "true",
    "WRITER_KB_PAYLOAD_USE_OVERLAY_METADATA": "false",
    "SEMANTIC_CARDS_PILOT_MAX_CARDS": "3",
}

_DEPRECATED_RUNTIME_FLAGS: Dict[str, str] = {
    "MULTIAGENT_ENABLED": "ignored_as_runtime_switch_after_PRD_036",
    "LEGACY_PIPELINE_ENABLED": "legacy_runtime_disabled_after_PRD_036",
}

_LOCAL_RUNTIME_MODES = {"local", "dev", "pilot", "test"}
_PRODUCTION_RUNTIME_MODES = {"production", "prod", "staging"}


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class FeatureFlags:
    """Env-backed feature flags (read on each access)."""

    @staticmethod
    def app_env() -> str:
        raw = str(os.getenv("APP_ENV", "") or "").strip().lower()
        if raw in _LOCAL_RUNTIME_MODES:
            return raw
        if raw in _PRODUCTION_RUNTIME_MODES:
            return "production" if raw in {"production", "prod"} else "staging"
        return "unknown"

    @staticmethod
    def resolve_bool(name: str) -> Dict[str, Any]:
        if name not in _DEFAULTS:
            return {
                "key": name,
                "effective_value": False,
                "source": "unknown_flag",
                "raw_value": None,
                "default_value": False,
                "runtime_mode": FeatureFlags.app_env(),
            }

        runtime_mode = FeatureFlags.app_env()
        default_value = _DEFAULTS[name]
        default_source = "default"
        if name in {"WRITER_KB_PAYLOAD_ENABLED", "RETRIEVAL_CURRENT_TURN_FOCUS_ENABLED"}:
            default_value = runtime_mode in _LOCAL_RUNTIME_MODES
            default_source = "default_local" if default_value else "default_safe_off"

        raw_value = os.getenv(name)
        if raw_value is not None:
            effective_value = _as_bool(raw_value, default_value)
            source = "env"
        else:
            effective_value = default_value
            source = default_source

        return {
            "key": name,
            "effective_value": bool(effective_value),
            "source": source,
            "raw_value": raw_value,
            "default_value": bool(default_value),
            "runtime_mode": runtime_mode,
        }

    @staticmethod
    def resolve_free_bool(name: str, default: bool) -> Dict[str, Any]:
        raw_value = os.getenv(name)
        return {
            "key": name,
            "effective_value": _as_bool(raw_value, default),
            "source": "env" if raw_value is not None else "default",
            "raw_value": raw_value,
            "default_value": bool(default),
            "runtime_mode": FeatureFlags.app_env(),
        }

    @staticmethod
    def runtime_config_trace() -> Dict[str, Any]:
        writer_payload = FeatureFlags.resolve_bool("WRITER_KB_PAYLOAD_ENABLED")
        overlay_shadow = FeatureFlags.resolve_bool("OVERLAY_SHADOW_TRACE_ENABLED")
        retrieval_current_turn = FeatureFlags.resolve_bool("RETRIEVAL_CURRENT_TURN_FOCUS_ENABLED")
        semantic_cards_pilot = FeatureFlags.resolve_bool("SEMANTIC_CARDS_PILOT_ENABLED")
        debug_trace = FeatureFlags.resolve_free_bool("DEBUG_TRACE_ENABLED", True)
        return {
            "schema_version": "runtime_config_trace_v1",
            "app_env": FeatureFlags.app_env(),
            "backend_pid": os.getpid(),
            "backend_start_time": _PROCESS_START_TIME_UTC,
            "writer_kb_payload_enabled": writer_payload["effective_value"],
            "writer_kb_payload_enabled_source": writer_payload["source"],
            "writer_kb_payload_raw_value": writer_payload["raw_value"],
            "writer_kb_payload_default_value": writer_payload["default_value"],
            "overlay_shadow_trace_enabled": overlay_shadow["effective_value"],
            "overlay_shadow_trace_enabled_source": overlay_shadow["source"],
            "retrieval_current_turn_focus_enabled": retrieval_current_turn["effective_value"],
            "retrieval_current_turn_focus_enabled_source": retrieval_current_turn["source"],
            "semantic_cards_pilot_enabled": semantic_cards_pilot["effective_value"],
            "semantic_cards_pilot_enabled_source": semantic_cards_pilot["source"],
            "semantic_cards_pilot_raw_value": semantic_cards_pilot["raw_value"],
            "semantic_cards_pilot_default_value": semantic_cards_pilot["default_value"],
            "debug_trace_enabled": debug_trace["effective_value"],
            "debug_trace_enabled_source": debug_trace["source"],
        }

    @staticmethod
    def enabled(name: str) -> bool:
        if name not in _DEFAULTS:
            return False
        return bool(FeatureFlags.resolve_bool(name)["effective_value"])

    @staticmethod
    def is_enabled(name: str) -> bool:
        return FeatureFlags.enabled(name)

    @staticmethod
    def snapshot() -> Dict[str, bool]:
        return {name: FeatureFlags.enabled(name) for name in _DEFAULTS}

    @staticmethod
    def deprecated_runtime_flags() -> Dict[str, str]:
        return dict(_DEPRECATED_RUNTIME_FLAGS)

    @staticmethod
    def value(name: str, default: str = "") -> str:
        if name in _STRING_DEFAULTS:
            return os.getenv(name, _STRING_DEFAULTS[name])
        return os.getenv(name, default)


feature_flags = FeatureFlags()
