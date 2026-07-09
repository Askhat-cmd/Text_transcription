from __future__ import annotations

from .admin_surface_bootstrap import *  # noqa: F401,F403
from .admin_surface_helpers import *  # noqa: F401,F403

def _build_config_schema_v104() -> dict[str, Any]:
    current = config.get_all_config()
    groups = current.get("groups", {})
    schema_groups: dict[str, dict[str, Any]] = {}

    for group_key, group in groups.items():
        params = group.get("params", {})
        schema_params: dict[str, dict[str, Any]] = {}
        for key, payload in params.items():
            schema_params[key] = {
                **payload,
                "editable": True,
                "read_only": False,
                "deprecated": key in DEPRECATED_CONFIG_KEYS,
                "compatibility_only": key in COMPATIBILITY_ONLY_CONFIG_KEYS,
            }
        schema_groups[group_key] = {
            "label": group.get("label", group_key),
            "params": schema_params,
        }

    status = _status_snapshot()
    read_only = {
        "runtime_status": {
            "degraded_mode": {
                "value": status["degraded_mode"],
                "editable": False,
                "read_only": True,
                "deprecated": False,
                "compatibility_only": False,
                "type": "bool",
                "label": "DEGRADED_MODE",
            },
            "data_source": {
                "value": status["data_source"],
                "editable": False,
                "read_only": True,
                "deprecated": False,
                "compatibility_only": False,
                "type": "string",
                "label": "Источник данных",
            },
            "blocks_loaded": {
                "value": status["blocks_loaded"],
                "editable": False,
                "read_only": True,
                "deprecated": False,
                "compatibility_only": False,
                "type": "int",
                "label": "Загружено блоков",
            },
            "version": {
                "value": status["version"],
                "editable": False,
                "read_only": True,
                "deprecated": False,
                "compatibility_only": False,
                "type": "string",
                "label": "Версия runtime",
            },
        },
        "feature_flags": {
            key: {
                "value": value,
                "editable": False,
                "read_only": True,
                "deprecated": False,
                "compatibility_only": False,
                "type": "bool",
                "label": key,
            }
            for key, value in status["feature_flags"].items()
        },
    }

    return {
        "schema_version": ADMIN_SCHEMA_VERSION,
        "editable": {"groups": schema_groups},
        "read_only": read_only,
        "deprecated": {
            "config_keys": sorted(DEPRECATED_CONFIG_KEYS),
            "prompt_keys": sorted(DEPRECATED_PROMPT_KEYS),
        },
        "compatibility_only": {"config_keys": sorted(COMPATIBILITY_ONLY_CONFIG_KEYS)},
    }


def _validate_import_overrides_payload(body: dict) -> dict:
    if not isinstance(body.get("config"), dict):
        raise HTTPException(
            status_code=422, detail="Поле 'config' должно быть объектом"
        )
    if not isinstance(body.get("prompts"), dict):
        raise HTTPException(
            status_code=422, detail="Поле 'prompts' должно быть объектом"
        )

    editable = getattr(config, "EDITABLE_CONFIG", {})
    normalized_config: dict[str, Any] = {}
    ignored_config_keys: list[str] = []
    for raw_key, value in body["config"].items():
        key = LEGACY_CONFIG_KEY_MAP.get(raw_key, raw_key)
        if key not in editable:
            ignored_config_keys.append(raw_key)
            continue
        normalized_config[key] = value

    editable_prompts = set(getattr(config, "EDITABLE_PROMPTS", []))
    normalized_prompts: dict[str, str | None] = {}
    ignored_prompt_keys: list[str] = []
    for key, value in body["prompts"].items():
        if key not in editable_prompts:
            ignored_prompt_keys.append(key)
            continue
        if value is not None and not isinstance(value, str):
            raise HTTPException(status_code=422, detail=f"Prompt '{key}' must be string or null")
        normalized_prompts[key] = value

    # Validate critical runtime constraints against effective values after import.
    effective = {
        "TOP_K_BLOCKS": normalized_config.get("TOP_K_BLOCKS", getattr(config, "TOP_K_BLOCKS", 5)),
        "MIN_RELEVANCE_SCORE": normalized_config.get("MIN_RELEVANCE_SCORE", getattr(config, "MIN_RELEVANCE_SCORE", 0.1)),
        "VOYAGE_TOP_K": normalized_config.get("VOYAGE_TOP_K", getattr(config, "VOYAGE_TOP_K", 5)),
        "MAX_CONTEXT_SIZE": normalized_config.get("MAX_CONTEXT_SIZE", getattr(config, "MAX_CONTEXT_SIZE", 2200)),
        "LLM_MODEL": normalized_config.get("LLM_MODEL", getattr(config, "LLM_MODEL", "")),
    }
    validation = validate_runtime_config(type("Cfg", (), effective)())
    if not validation.valid:
        raise HTTPException(
            status_code=422,
            detail={"message": "Invalid runtime config in import payload", "errors": validation.errors},
        )

    meta = dict(body.get("meta", {})) if isinstance(body.get("meta"), dict) else {}
    incoming_version = str(meta.get("schema_version", "legacy-v1"))
    normalized = {
        "config": normalized_config,
        "prompts": normalized_prompts,
        "history": list(body.get("history", [])) if isinstance(body.get("history"), list) else [],
        "meta": {
            **meta,
            "imported_schema_version": incoming_version,
            "schema_version": ADMIN_SCHEMA_VERSION,
            "ignored_config_keys": ignored_config_keys,
            "ignored_prompt_keys": ignored_prompt_keys,
        },
    }
    return normalized

__all__ = [name for name in globals() if not name.startswith("__")]
