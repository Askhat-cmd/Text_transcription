from __future__ import annotations

from .admin_surface_bootstrap import *  # noqa: F401,F403

def _env_flags_snapshot() -> dict[str, str]:
    return build_compat_env_flags_snapshot()


def _is_truthy_env(value: str | None) -> bool:
    normalized = str(value or "").strip().lower()
    return normalized in {"1", "true", "on", "yes", "y"}


def _compute_env_pipeline_mode() -> str:
    # PRD-037: admin runtime contract is multiagent-only.
    # Keep this helper for backward-compatible payload fields.
    return "multiagent_only"


def _compute_active_runtime(actual_mode: str | None = None) -> str:
    _ = actual_mode
    return "multiagent"


def _runtime_entrypoint() -> str:
    return "multiagent_adapter"


def _deprecated_runtime_warnings(env_flags: dict[str, str]) -> list[str]:
    warnings: list[str] = []
    if _is_truthy_env(env_flags.get("LEGACY_PIPELINE_ENABLED")):
        warnings.append("LEGACY_PIPELINE_ENABLED is deprecated and ignored")
    return warnings


def _legacy_status_payload() -> dict[str, Any]:
    return {
        "fallback_enabled": False,
        "fallback_used": False,
        "cascade_available": False,
        "cascade_status": "physically_removed",
        "purge_planned_prd": None,
        "purge_completed_prd": "PRD-041",
    }


def _compatibility_runtime_payload() -> dict[str, Any]:
    return {
        "pipeline_mode": "multiagent_only",
        "pipeline_mode_legacy_value": None,
        "pipeline_mode_read_only": True,
        "legacy_modes_selectable": False,
        "dialogue_profile_alias": {
            "primary_profile": "safe_guided",
            "legacy_alias": "safe_guided",
            "modern_label": "guided",
            "surface_role": "compatibility_only",
        },
        "knowledge_graph": {
            "enabled": bool(getattr(config, "ENABLE_KNOWLEDGE_GRAPH", False)),
            "status": (
                "enabled_optional_legacy"
                if bool(getattr(config, "ENABLE_KNOWLEDGE_GRAPH", False))
                else "disabled_legacy"
            ),
            "surface_role": "compatibility_only",
            "note": "Legacy graph subsystem is not a primary runtime control surface.",
        },
    }


def _runtime_agents_contract_payload() -> dict[str, dict[str, Any]]:
    return {
        "state_analyzer": {"kind": "llm"},
        "thread_manager": _thread_manager_llm_meta(),
        "memory_retrieval": {"kind": "retrieval"},
        "writer": {"kind": "llm"},
        "validator": {"kind": "deterministic"},
    }


def _thread_manager_llm_meta() -> dict[str, Any]:
    return {
        "kind": "heuristic",
        "llm_model_effective": False,
        "note": "Model selection is reserved for future LLM thread manager; current implementation is heuristic.",
    }

__all__ = [name for name in globals() if not name.startswith("__")]
