from __future__ import annotations

from .admin_runtime_effective_payload import *  # noqa: F401,F403

def _build_diagnostics_effective_payload(session_id: str | None = None) -> dict[str, Any]:
    flags_snapshot = feature_flags.snapshot()
    active_contract = {
        "contract_version": "diagnostics-v1",
        "interaction_mode_policy": "system-level",
        "nervous_system_taxonomy": "hyper|window|hypo",
        "request_function_taxonomy": "discharge|understand|solution|validation|explore|contact",
        "core_theme_extraction": "enabled",
    }

    return {
        "schema_version": ADMIN_EFFECTIVE_SCHEMA_VERSION,
        "contract": "diagnostics-v1",
        "policies": {
            "informational_narrowing_enabled": bool(flags_snapshot.get("INFORMATIONAL_BRANCH_ENABLED")),
            "mixed_query_handling_enabled": bool(flags_snapshot.get("USE_NEW_DIAGNOSTICS_V1")),
            "user_correction_protocol_enabled": bool(_group_param_value("routing", "STATE_CLASSIFIER_ENABLED", True)),
            "first_turn_richness_policy_enabled": bool(flags_snapshot.get("USE_OUTPUT_VALIDATION")),
            "curiosity_decoupling_enabled": True,
        },
        "active_contract": active_contract,
        "last_snapshot": {},
        "trace_available": False,
    }

__all__ = [name for name in globals() if not name.startswith("__")]
