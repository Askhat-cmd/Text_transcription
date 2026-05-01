# api/admin_routes.py
"""
Admin Config Panel — API endpoints.

Все эндпоинты требуют dev-ключ в заголовке X-API-Key.
Роутер регистрируется в main.py через app.include_router(admin_router).
"""

from fastapi import APIRouter, Depends, HTTPException, Header, Query, status
from typing import Any
import importlib
import json
import os
import threading as _threading
from collections import deque as _deque
from datetime import datetime, timezone
from pathlib import Path

from bot_agent.config import config
from bot_agent.config_validation import validate_runtime_config
from bot_agent.data_loader import data_loader
from bot_agent.feature_flags import feature_flags
from bot_agent.multiagent.orchestrator import orchestrator
from bot_agent.multiagent.thread_storage import thread_storage
from bot_agent.prompt_registry_v2 import PROMPT_STACK_ORDER, PROMPT_STACK_VERSION, prompt_registry_v2
from .auth import is_dev_key
from .dependencies import get_identity_service
from .identity import IdentityService, mask_external_id


_agent_metrics_lock = _threading.Lock()
_agent_metrics: dict[str, dict[str, Any]] = {
    "state_analyzer": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
    "thread_manager": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
    "memory_retrieval": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
    "writer": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
    "validator": {"call_count": 0, "total_ms": 0, "error_count": 0, "last_run": None, "enabled": True},
}
_agent_traces: _deque[dict[str, Any]] = _deque(maxlen=200)
_orchestrator_mode: dict[str, str] = {"pipeline_mode": "full_multiagent"}
_agent_prompt_overrides: dict[str, dict[str, str]] = {}
_AGENT_PROMPT_MAP = {
    "writer": "bot_agent.multiagent.agents.writer_agent_prompts",
    "state_analyzer": "bot_agent.multiagent.agents.state_analyzer_prompts",
    "thread_manager": "bot_agent.multiagent.agents.thread_manager_prompts",
}


def _env_flags_snapshot() -> dict[str, str]:
    return {
        "MULTIAGENT_ENABLED": os.getenv("MULTIAGENT_ENABLED", "off"),
        "LEGACY_PIPELINE_ENABLED": os.getenv("LEGACY_PIPELINE_ENABLED", "off"),
        "NEO_MINDBOT_ENABLED": os.getenv("NEO_MINDBOT_ENABLED", "off"),
    }


def _compute_env_pipeline_mode() -> str:
    flags = _env_flags_snapshot()
    multi_on = flags["MULTIAGENT_ENABLED"] == "on"
    legacy_on = flags["LEGACY_PIPELINE_ENABLED"] == "on"
    if multi_on and legacy_on:
        return "hybrid"
    if multi_on:
        return "full_multiagent"
    return "legacy_adaptive"


# ─── Auth dependency ───────────────────────────────────────────────────────────

def require_dev_key(x_api_key: str = Header(..., alias="X-API-Key")) -> str:
    """FastAPI Dependency: доступ только для dev-ключа."""
    if not is_dev_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Доступ запрещён: требуется dev-ключ",
        )
    return x_api_key


# ─── Router ────────────────────────────────────────────────────────────────────

admin_router = APIRouter(
    prefix="/api/admin",
    tags=["⚙️ Admin Config"],
    dependencies=[Depends(require_dev_key)],
)

admin_router_v1 = APIRouter(
    prefix="/api/v1/admin",
    tags=["⚙️ Admin Config v1"],
    dependencies=[Depends(require_dev_key)],
)

ADMIN_SCHEMA_VERSION = "10.5"
ADMIN_EFFECTIVE_SCHEMA_VERSION = "10.5.1"

LEGACY_CONFIG_KEY_MAP = {
    "RETRIEVAL_TOP_K": "TOP_K_BLOCKS",
    "RERANK_TOP_K": "VOYAGE_TOP_K",
}

DEPRECATED_CONFIG_KEYS: set[str] = set()

COMPATIBILITY_ONLY_CONFIG_KEYS: set[str] = set()

DEPRECATED_PROMPT_KEYS: set[str] = set()

PROMPT_STACK_V2_VARIANTS = [
    "inform-rich",
    "mixed-query",
    "first-turn",
    "user-correction",
    "safe-override",
]

PROMPT_STACK_V2_EDITABLE_MAP = {
    "CORE_IDENTITY": "prompt_system_base",
}


def _filter_operational_flags(snapshot: dict[str, bool]) -> dict[str, bool]:
    return {
        key: value
        for key, value in (snapshot or {}).items()
        if not key.startswith("DISABLE_SD_")
    }


def _status_snapshot() -> dict[str, Any]:
    stats = data_loader.get_stats()
    flags_snapshot = _filter_operational_flags(feature_flags.snapshot())
    return {
        "degraded_mode": bool(stats.get("degraded_mode", False)),
        "data_source": stats.get("data_source", "unknown"),
        "blocks_loaded": int(stats.get("total_blocks", 0)),
        "version": "0.7.0",
        "feature_flags": flags_snapshot,
    }


def _prompt_stack_v2_sections_baseline() -> dict[str, str]:
    build = prompt_registry_v2.build(
        query="baseline",
        blocks=[],
        conversation_context="",
        additional_system_context="",
        route="inform",
        mode="CLARIFICATION",
        diagnostics={
            "interaction_mode": "informational",
            "nervous_system_state": "window",
            "request_function": "understand",
            "core_theme": "baseline",
        },
    )
    return dict(build.sections)


def _prompt_history_metadata(prompt_name: str | None) -> dict[str, Any]:
    if not prompt_name:
        return {"version": "v2.0.0", "updated_at": None}
    history = list(config.get_history() or [])
    related = [entry for entry in history if entry.get("key") == prompt_name and str(entry.get("type", "")).startswith("prompt")]
    if not related:
        return {"version": "v2.0.0", "updated_at": None}
    latest = related[-1]
    return {
        "version": f"v2.0.{len(related)}",
        "updated_at": latest.get("timestamp"),
    }


def _build_prompt_stack_v2_meta() -> list[dict[str, Any]]:
    baseline_sections = _prompt_stack_v2_sections_baseline()
    result: list[dict[str, Any]] = []
    for section in PROMPT_STACK_ORDER:
        editable_prompt_name = PROMPT_STACK_V2_EDITABLE_MAP.get(section)
        editable = editable_prompt_name is not None
        if editable:
            prompt_payload = config.get_prompt(editable_prompt_name)
            active_text = prompt_payload.get("text", "")
            is_overridden = bool(prompt_payload.get("is_overridden", False))
        else:
            active_text = baseline_sections.get(section, "")
            is_overridden = False
        history_meta = _prompt_history_metadata(editable_prompt_name)
        result.append(
            {
                "name": section,
                "label": section,
                "preview": str(active_text).replace("\n", " ")[:150],
                "is_overridden": is_overridden,
                "char_count": len(str(active_text)),
                "editable": editable,
                "is_legacy": False,
                "source": "config_prompt" if editable else "runtime_derived",
                "stack_version": PROMPT_STACK_VERSION,
                "variants": list(PROMPT_STACK_V2_VARIANTS),
                "version": history_meta["version"],
                "updated_at": history_meta["updated_at"],
                "legacy_prompt_name": editable_prompt_name,
                "derived_from": editable_prompt_name if editable else "prompt_registry_v2",
                "read_only_reason": None if editable else "runtime_derived_section_not_editable_via_admin",
                "usage_markers": {"used_in_last_turn": False},
            }
        )
    return result


def _build_prompt_stack_v2_detail(section_name: str) -> dict[str, Any]:
    sections = _prompt_stack_v2_sections_baseline()
    if section_name not in PROMPT_STACK_ORDER:
        raise HTTPException(status_code=404, detail=f"Unknown prompt stack section: {section_name}")

    editable_prompt_name = PROMPT_STACK_V2_EDITABLE_MAP.get(section_name)
    editable = editable_prompt_name is not None
    if editable:
        base = config.get_prompt(editable_prompt_name)
        text = str(base.get("text", ""))
        default_text = str(base.get("default_text", ""))
        is_overridden = bool(base.get("is_overridden", False))
    else:
        text = str(sections.get(section_name, ""))
        default_text = text
        is_overridden = False

    history_meta = _prompt_history_metadata(editable_prompt_name)
    return {
        "name": section_name,
        "label": section_name,
        "preview": text.replace("\n", " ")[:150],
        "is_overridden": is_overridden,
        "char_count": len(text),
        "text": text,
        "default_text": default_text,
        "editable": editable,
        "is_legacy": False,
        "source": "config_prompt" if editable else "runtime_derived",
        "stack_version": PROMPT_STACK_VERSION,
        "variants": list(PROMPT_STACK_V2_VARIANTS),
        "version": history_meta["version"],
        "updated_at": history_meta["updated_at"],
        "legacy_prompt_name": editable_prompt_name,
        "derived_from": editable_prompt_name if editable else "prompt_registry_v2",
        "read_only_reason": None if editable else "runtime_derived_section_not_editable_via_admin",
        "usage_markers": {"used_in_last_turn": False},
    }


def _group_feature_flags(snapshot: dict[str, bool]) -> dict[str, dict[str, bool]]:
    groups = {
        "neo_runtime": (
            "NEO_MINDBOT_ENABLED",
            "LEGACY_PIPELINE_ENABLED",
            "DISABLE_USER_LEVEL_ADAPTER",
        ),
        "pipeline": (
            "USE_NEW_DIAGNOSTICS_V1",
            "USE_DETERMINISTIC_ROUTE_RESOLVER",
            "USE_PROMPT_STACK_V2",
            "USE_OUTPUT_VALIDATION",
            "INFORMATIONAL_BRANCH_ENABLED",
        ),
        "quality": (
            "ENABLE_CONDITIONAL_RERANKER",
            "ENABLE_EMBEDDING_PROVIDER",
        ),
    }
    return {
        group: {flag: snapshot.get(flag, False) for flag in flags}
        for group, flags in groups.items()
    }


def _compute_agent_metrics() -> list[dict[str, Any]]:
    runtime_metrics = getattr(orchestrator, "_agent_metrics", None)
    source: dict[str, dict[str, Any]]
    if isinstance(runtime_metrics, dict) and runtime_metrics:
        source = runtime_metrics
    else:
        source = _agent_metrics

    result = []
    for agent_id in sorted(source.keys()):
        metric = source.get(agent_id, {})
        call_count = int(metric.get("call_count", 0))
        total_ms = int(metric.get("total_ms", 0))
        error_count = int(metric.get("error_count", 0))
        avg_ms = round(total_ms / call_count, 1) if call_count > 0 else 0
        result.append(
            {
                "id": agent_id,
                "enabled": bool(metric.get("enabled", True)),
                "call_count": call_count,
                "avg_latency_ms": avg_ms,
                "error_count": error_count,
                "error_rate": round(error_count / call_count, 4) if call_count > 0 else 0.0,
                "last_run": metric.get("last_run"),
            }
        )
    return result


def _get_thread_storage_dir() -> Path:
    raw = os.getenv("THREAD_STORAGE_DIR")
    if raw:
        return Path(raw).expanduser().resolve()
    storage_dir = getattr(thread_storage, "_dir", None)
    if storage_dir is not None:
        return Path(storage_dir).expanduser().resolve()
    return (Path(__file__).resolve().parent.parent / "data" / "threads").resolve()


def _list_active_threads() -> list[dict[str, Any]]:
    storage_dir = _get_thread_storage_dir()
    if not storage_dir.exists():
        return []
    threads: list[dict[str, Any]] = []
    for file_path in sorted(storage_dir.glob("*_active.json")):
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            threads.append(
                {
                    "thread_id": str(payload.get("thread_id", "")),
                    "user_id": str(payload.get("user_id", "")),
                    "phase": str(payload.get("phase", "unknown")),
                    "response_mode": str(payload.get("response_mode", "unknown")),
                    "core_direction": str(payload.get("core_direction", "")),
                    "turn_count": int(payload.get("turn_count", 0) or 0),
                    "created_at": str(payload.get("created_at", "")),
                    "last_updated_at": str(payload.get("last_updated_at", "")),
                    "status": "active",
                    "open_loops_count": len(payload.get("open_loops", []) or []),
                    "closed_loops_count": len(payload.get("closed_loops", []) or []),
                }
            )
        except Exception:
            continue
    return threads


def _list_archived_threads() -> list[dict[str, Any]]:
    storage_dir = _get_thread_storage_dir()
    if not storage_dir.exists():
        return []
    threads: list[dict[str, Any]] = []
    for file_path in sorted(storage_dir.glob("*_archive.json")):
        user_id = file_path.stem.replace("_archive", "")
        try:
            payload = json.loads(file_path.read_text(encoding="utf-8"))
            for item in payload if isinstance(payload, list) else []:
                threads.append(
                    {
                        "thread_id": str(item.get("thread_id", "")),
                        "user_id": user_id,
                        "final_phase": str(item.get("final_phase", "")),
                        "core_direction": str(item.get("core_direction", "")),
                        "archived_at": str(item.get("archived_at", "")),
                        "archive_reason": str(item.get("archive_reason", "")),
                        "status": "archived",
                    }
                )
        except Exception:
            continue
    return threads


def _get_agent_prompts_raw(agent_id: str) -> dict[str, str]:
    module_path = _AGENT_PROMPT_MAP.get(agent_id)
    if not module_path:
        raise HTTPException(status_code=404, detail=f"No prompts module for agent: {agent_id}")
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise HTTPException(status_code=500, detail=f"Cannot load agent prompts: {exc}") from exc
    result: dict[str, str] = {}
    for attr in dir(module):
        if attr.startswith("_"):
            continue
        value = getattr(module, attr, None)
        if isinstance(value, str) and len(value) > 20:
            result[attr] = value
    return result


def _group_param_value(group_name: str, key: str, default: Any = None) -> Any:
    all_groups = config.get_all_config().get("groups", {})
    group = all_groups.get(group_name, {})
    params = group.get("params", {})
    if key not in params:
        return default
    return params[key].get("value", default)


def _build_runtime_effective_payload(session_id: str | None = None) -> dict[str, Any]:
    status_payload = _status_snapshot()
    flags_snapshot = _filter_operational_flags(feature_flags.snapshot())
    validation = validate_runtime_config(config)
    # session_id retained only for route-level backward compatibility.
    _ = session_id

    return {
        "schema_version": ADMIN_EFFECTIVE_SCHEMA_VERSION,
        "admin_schema_version": ADMIN_SCHEMA_VERSION,
        "prompt_stack_version": PROMPT_STACK_VERSION,
        "status": status_payload,
        "feature_flags": {
            "all": flags_snapshot,
            "groups": _group_feature_flags(flags_snapshot),
        },
        "diagnostics": {
            "contract": "v1",
            "enabled": bool(flags_snapshot.get("USE_NEW_DIAGNOSTICS_V1")),
            "informational_branch_enabled": bool(flags_snapshot.get("INFORMATIONAL_BRANCH_ENABLED")),
        },
        "routing": {
            "deterministic_resolver_enabled": bool(flags_snapshot.get("USE_DETERMINISTIC_ROUTE_RESOLVER")),
            "curiosity_decoupling_enabled": True,
            "false_inform_protection_enabled": bool(flags_snapshot.get("USE_OUTPUT_VALIDATION")),
            "practice_trigger_guard_enabled": bool(_group_param_value("routing", "FREE_CONVERSATION_MODE", True)),
        },
        "validation": {
            "enabled": bool(flags_snapshot.get("USE_OUTPUT_VALIDATION")),
            "config_validation_status": {
                "valid": validation.valid,
                "errors": list(validation.errors),
            },
        },
        "trace": {
            "available": True,
            "developer_trace_supported": True,
            "developer_trace_enabled": True,
            "developer_trace_mode_available": True,
        },
    }


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


# ══════════════════════════════════════════════════════════════════════
# CONFIG ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/config",
    summary="Все параметры конфига (сгруппированные)",
    response_description="Параметры разбиты по группам: llm, retrieval, memory, storage, runtime",
)
@admin_router_v1.get(
    "/config",
    summary="Все параметры конфига (v1)",
)
async def admin_get_config():
    """
    Возвращает все редактируемые параметры конфига с метаданными.
    Для каждого параметра: текущее значение, дефолт, флаг is_overridden.
    """
    return config.get_all_config()


@admin_router.get(
    "/config/schema",
    summary="Схема параметров конфига",
)
@admin_router_v1.get(
    "/config/schema",
    summary="Схема параметров конфига (v1)",
)
async def admin_get_config_schema():
    """
    Возвращает схему редактируемых параметров по группам.
    Используется фронтендом для динамического рендера форм.
    """
    schema: dict[str, dict[str, Any]] = {}
    editable = getattr(config, "EDITABLE_CONFIG", {})
    for key, meta in editable.items():
        group = str(meta.get("group", "runtime"))
        schema.setdefault(group, {})
        schema[group][key] = {
            "type": meta.get("type"),
            "min": meta.get("min"),
            "max": meta.get("max"),
            "default": getattr(config.__class__, key, None),
            "nullable": False,
            "label": meta.get("label", key),
            "options": meta.get("options"),
        }
    # Специальное поле c nullable-интом для нового режима токенов.
    if "llm" in schema:
        schema["llm"]["MAX_TOKENS"] = {
            "type": "int_or_null",
            "min": 256,
            "max": 16000,
            "default": None,
            "nullable": True,
            "label": "Лимит токенов (null = без ограничения)",
            "options": None,
        }
    return schema


@admin_router.get(
    "/config/schema-v104",
    summary="Schema v10.4 для admin surface (editable/read-only/deprecated)",
)
@admin_router_v1.get(
    "/config/schema-v104",
    summary="Schema v10.4 для admin surface (v1 route)",
)
async def admin_get_config_schema_v104():
    return _build_config_schema_v104()


@admin_router.put(
    "/config",
    summary="Сохранить значение одного параметра",
)
@admin_router.post(
    "/config",
    summary="Сохранить параметры конфига (single/group payload)",
)
@admin_router_v1.put(
    "/config",
    summary="Сохранить параметры конфига (v1)",
)
@admin_router_v1.post(
    "/config",
    summary="Сохранить параметры конфига (v1, grouped)",
)
async def admin_set_config(body: dict):
    """
    Сохраняет override одного параметра конфига.

    Body: `{"key": "LLM_TEMPERATURE", "value": 0.5}`

    Валидирует тип и диапазон перед сохранением.
    Изменение применяется к следующему запросу бота без рестарта.
    """
    # Legacy single-key payload: {"key": "...", "value": ...}
    key = body.get("key")
    value = body.get("value")
    if key is not None:
        if value is None:
            raise HTTPException(status_code=422, detail="Поле 'value' обязательно")
        try:
            return config.set_config_override(key, value)
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))

    # New grouped payload:
    # {"llm": {"MAX_TOKENS": null}, "routing": {"FREE_CONVERSATION_MODE": true}}
    updated: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for group_name, params in body.items():
        if not isinstance(params, dict):
            continue
        for param_key, param_value in params.items():
            try:
                if param_key == "MAX_TOKENS":
                    setattr(config, "MAX_TOKENS", None if param_value is None else int(param_value))
                    updated[param_key] = getattr(config, "MAX_TOKENS")
                else:
                    result = config.set_config_override(param_key, param_value)
                    updated[param_key] = result.get("value")
            except Exception as exc:  # noqa: BLE001
                errors[param_key] = str(exc)

    if not updated and not errors:
        raise HTTPException(status_code=422, detail="Payload не содержит параметров для обновления")
    return {"status": "ok", "updated": updated, "errors": errors}


@admin_router.delete(
    "/config/{key}",
    summary="Сбросить один параметр к дефолту",
)
@admin_router_v1.delete(
    "/config/{key}",
    summary="Сбросить один параметр к дефолту (v1)",
)
async def admin_reset_config_param(key: str):
    """Удаляет override параметра. Параметр вернётся к дефолту из config.py."""
    try:
        return config.reset_config_override(key)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@admin_router.post(
    "/config/reset-all",
    summary="Сбросить ВСЕ параметры конфига к дефолтам",
)
@admin_router_v1.post(
    "/config/reset-all",
    summary="Сбросить все параметры конфига к дефолтам (v1)",
)
async def admin_reset_all_config():
    """Удаляет все config-overrides. Промты не затрагивает."""
    config.reset_all_config_overrides()
    return {"status": "ok", "message": "Все параметры конфига сброшены к дефолтам"}


@admin_router.get(
    "/status",
    summary="Runtime-статус источника данных",
)
@admin_router_v1.get(
    "/status",
    summary="Runtime-статус источника данных (v1)",
)
async def admin_status():
    status_payload = _status_snapshot()
    return {
        "degraded_mode": status_payload["degraded_mode"],
        "data_source": status_payload["data_source"],
        "blocks_loaded": status_payload["blocks_loaded"],
        "version": status_payload["version"],
        "feature_flags": status_payload["feature_flags"],
    }


@admin_router.get(
    "/runtime/effective",
    summary="Effective runtime truth payload for operational admin surface",
)
@admin_router_v1.get(
    "/runtime/effective",
    summary="Effective runtime truth payload (v1 route)",
)
async def admin_runtime_effective(session_id: str | None = Query(default=None)):
    return _build_runtime_effective_payload(session_id=session_id)


@admin_router.get(
    "/diagnostics/effective",
    summary="Effective diagnostics payload for operational admin surface",
)
@admin_router_v1.get(
    "/diagnostics/effective",
    summary="Effective diagnostics payload (v1 route)",
)
async def admin_diagnostics_effective(session_id: str | None = Query(default=None)):
    return _build_diagnostics_effective_payload(session_id=session_id)


@admin_router.get(
    "/trace/last",
    summary="Deprecated admin trace endpoint",
)
@admin_router_v1.get(
    "/trace/last",
    summary="Deprecated admin trace endpoint (v1 route)",
)
async def admin_trace_last(session_id: str | None = Query(default=None)):
    _ = session_id
    raise HTTPException(
        status_code=410,
        detail="Admin trace endpoint deprecated. Use developer trace in chat runtime.",
    )


@admin_router.get(
    "/trace/recent",
    summary="Deprecated admin trace endpoint",
)
@admin_router_v1.get(
    "/trace/recent",
    summary="Deprecated admin trace endpoint (v1 route)",
)
async def admin_trace_recent(
    session_id: str | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=50),
):
    _ = (session_id, limit)
    raise HTTPException(
        status_code=410,
        detail="Admin trace endpoint deprecated. Use developer trace in chat runtime.",
    )


@admin_router.post(
    "/reload-data",
    summary="Перезагрузить базу знаний в data_loader",
)
@admin_router_v1.post(
    "/reload-data",
    summary="Перезагрузить базу знаний в data_loader (v1)",
)
async def admin_reload_data():
    blocks = data_loader.reload()
    stats = data_loader.get_stats()
    return {
        "status": "ok",
        "message": "Data loader reloaded",
        "blocks_loaded": len(blocks),
        "data_source": stats.get("data_source", "unknown"),
        "degraded_mode": bool(stats.get("degraded_mode", False)),
    }


# ══════════════════════════════════════════════════════════════════════
# PROMPT ENDPOINTS
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/prompts",
    summary="Список всех промтов с превью",
)
@admin_router_v1.get(
    "/prompts",
    summary="Список всех промтов (v1)",
)
async def admin_get_prompts():
    """
    Возвращает список всех 10 редактируемых промтов.
    Для каждого: label, превью 150 символов, флаг is_overridden, char_count.
    """
    return config.get_all_prompts()


@admin_router.get(
    "/prompts/stack-v2",
    summary="Prompt stack v2 surface для Neo runtime",
)
@admin_router_v1.get(
    "/prompts/stack-v2",
    summary="Prompt stack v2 surface (v1 route)",
)
async def admin_get_prompts_stack_v2():
    return _build_prompt_stack_v2_meta()


@admin_router.get(
    "/prompts/stack-v2/usage",
    summary="Deprecated prompt stack usage endpoint",
)
@admin_router_v1.get(
    "/prompts/stack-v2/usage",
    summary="Deprecated prompt stack usage endpoint (v1 route)",
)
async def admin_get_prompts_stack_v2_usage(session_id: str | None = Query(default=None)):
    _ = session_id
    raise HTTPException(
        status_code=410,
        detail="Prompt stack usage endpoint deprecated. Prompt stack usage is no longer provided by admin API.",
    )


@admin_router.get(
    "/prompts/{name}",
    summary="Полный текст промта",
)
@admin_router_v1.get(
    "/prompts/{name}",
    summary="Полный текст промта (v1)",
)
async def admin_get_prompt(name: str):
    """
    Возвращает полный текст промта: актуальный (с override) и дефолтный (из .md).
    """
    try:
        data = config.get_prompt(name)
        # Alias for web-ui versions expecting "content".
        data["content"] = data.get("text", "")
        return data
    except (ValueError, FileNotFoundError) as e:
        raise HTTPException(status_code=404, detail=str(e))


@admin_router.get(
    "/prompts/stack-v2/{name}",
    summary="Детали секции prompt stack v2",
)
@admin_router_v1.get(
    "/prompts/stack-v2/{name}",
    summary="Детали секции prompt stack v2 (v1 route)",
)
async def admin_get_prompt_stack_v2(name: str):
    return _build_prompt_stack_v2_detail(name)


@admin_router.put(
    "/prompts/{name}",
    summary="Сохранить новый текст промта",
)
@admin_router_v1.put(
    "/prompts/{name}",
    summary="Сохранить новый текст промта (v1)",
)
async def admin_set_prompt(name: str, body: dict):
    """
    Сохраняет override текста промта.

    Body: `{"text": "Новый текст промта..."}`

    Изменение применяется к следующему запросу бота без рестарта
    (только если промт читается внутри функции, а не на уровне модуля).
    """
    text = body.get("text", body.get("content", ""))
    try:
        result = config.set_prompt_override(name, text)
        result["content"] = result.get("text", "")
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@admin_router.put(
    "/prompts/stack-v2/{name}",
    summary="Сохранить editable секцию prompt stack v2",
)
@admin_router_v1.put(
    "/prompts/stack-v2/{name}",
    summary="Сохранить editable секцию prompt stack v2 (v1 route)",
)
async def admin_set_prompt_stack_v2(name: str, body: dict):
    detail = _build_prompt_stack_v2_detail(name)
    if not detail.get("editable"):
        raise HTTPException(status_code=422, detail=f"Section '{name}' is read-only")
    text = str(body.get("text", body.get("content", ""))).strip()
    if len(text) < 20:
        raise HTTPException(status_code=422, detail="Prompt text too short (min 20 chars)")
    prompt_name = detail.get("legacy_prompt_name")
    assert prompt_name
    updated = config.set_prompt_override(prompt_name, text)
    payload = _build_prompt_stack_v2_detail(name)
    payload["content"] = payload.get("text", "")
    payload["legacy_updated"] = updated.get("name")
    return payload


@admin_router.delete(
    "/prompts/{name}",
    summary="Сбросить промт к дефолту (из .md файла)",
)
@admin_router_v1.delete(
    "/prompts/{name}",
    summary="Сбросить промт к дефолту (v1)",
)
@admin_router.post(
    "/prompts/{name}/reset",
    summary="Сбросить промт к дефолту",
)
@admin_router_v1.post(
    "/prompts/{name}/reset",
    summary="Сбросить промт к дефолту (v1)",
)
async def admin_reset_prompt(name: str):
    """Удаляет override промта. Бот вернётся к тексту из .md файла."""
    try:
        result = config.reset_prompt_override(name)
        result["content"] = result.get("text", "")
        return result
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@admin_router.post(
    "/prompts/stack-v2/{name}/reset",
    summary="Сбросить editable секцию prompt stack v2",
)
@admin_router_v1.post(
    "/prompts/stack-v2/{name}/reset",
    summary="Сбросить editable секцию prompt stack v2 (v1 route)",
)
async def admin_reset_prompt_stack_v2(name: str):
    detail = _build_prompt_stack_v2_detail(name)
    if not detail.get("editable"):
        raise HTTPException(status_code=422, detail=f"Section '{name}' is read-only")
    prompt_name = detail.get("legacy_prompt_name")
    assert prompt_name
    config.reset_prompt_override(prompt_name)
    payload = _build_prompt_stack_v2_detail(name)
    payload["content"] = payload.get("text", "")
    return payload


@admin_router.post(
    "/prompts/reset-all",
    summary="Сбросить ВСЕ промты к дефолтам",
)
async def admin_reset_all_prompts():
    """Удаляет все prompt-overrides. Config не затрагивает."""
    config.reset_all_prompt_overrides()
    return {"status": "ok", "message": "Все промты сброшены к дефолтам"}


# ══════════════════════════════════════════════════════════════════════
# HISTORY
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/history",
    summary="История изменений (последние 50)",
)
async def admin_get_history():
    """
    Возвращает хронологический список последних 50 изменений конфига и промтов.
    Каждая запись: key, type, old, new, timestamp.
    """
    return {"history": config.get_history()}


# ══════════════════════════════════════════════════════════════════════
# EXPORT / IMPORT
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/export",
    summary="Экспортировать все overrides (backup)",
)
@admin_router_v1.get(
    "/export",
    summary="Экспортировать все overrides (backup, v1)",
)
async def admin_export_overrides():
    """
    Возвращает полный JSON-файл admin_overrides.json.
    Используется для резервного копирования или переноса между окружениями.
    """
    payload = config._load_overrides()
    payload.setdefault("config", {})
    payload.setdefault("prompts", {})
    payload.setdefault("history", [])
    meta = dict(payload.get("meta", {}))
    meta.setdefault("schema_family", "admin_overrides")
    meta.setdefault("schema_version", ADMIN_SCHEMA_VERSION)
    payload["meta"] = meta
    return payload


@admin_router.post(
    "/import",
    summary="Импортировать overrides из JSON (restore)",
)
@admin_router_v1.post(
    "/import",
    summary="Импортировать overrides из JSON (restore, v1)",
)
async def admin_import_overrides(body: dict):
    """
    Загружает overrides из тела запроса.
    Полностью заменяет текущий admin_overrides.json.
    Валидирует структуру перед сохранением.

    Body: содержимое admin_overrides.json (полученное через /export).
    """
    normalized = _validate_import_overrides_payload(body)
    previous = config._load_overrides()
    try:
        config._save_overrides(normalized)
        return {
            "status": "ok",
            "schema_version": ADMIN_SCHEMA_VERSION,
            "imported_schema_version": normalized.get("meta", {}).get("imported_schema_version"),
            "config_keys": len(normalized.get("config", {})),
            "prompt_overrides": sum(
                1 for v in normalized.get("prompts", {}).values() if v is not None
            ),
            "ignored_config_keys": normalized.get("meta", {}).get("ignored_config_keys", []),
            "ignored_prompt_keys": normalized.get("meta", {}).get("ignored_prompt_keys", []),
        }
    except Exception as e:
        try:
            config._save_overrides(previous)
        except Exception:
            pass
        raise HTTPException(
            status_code=500,
            detail={"message": str(e), "rollback_applied": True},
        )


# ══════════════════════════════════════════════════════════════════════
# MULTIAGENT: AGENTS STATUS
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/agents/status",
    summary="Статус агентов мультиагентного пайплайна",
)
async def admin_agents_status():
    pipeline_version = getattr(orchestrator, "pipeline_version", "multiagent_v1")
    return {"pipeline_version": pipeline_version, "agents": _compute_agent_metrics()}


@admin_router.post(
    "/agents/{agent_id}/toggle",
    summary="Включить/выключить агента",
)
async def admin_agents_toggle(agent_id: str, body: dict):
    if agent_id not in _agent_metrics:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}. Valid: {sorted(_agent_metrics)}")
    with _agent_metrics_lock:
        _agent_metrics[agent_id]["enabled"] = bool(body.get("enabled", True))
        enabled = bool(_agent_metrics[agent_id]["enabled"])
    return {"agent_id": agent_id, "enabled": enabled, "status": "ok"}


@admin_router.post(
    "/agents/metrics/record",
    summary="Записать метрику прогона агента (internal)",
)
async def admin_agents_record_metric(body: dict):
    agent_id = str(body.get("agent_id", ""))
    if agent_id not in _agent_metrics:
        raise HTTPException(status_code=404, detail=f"Unknown agent_id: {agent_id}")
    with _agent_metrics_lock:
        metric = _agent_metrics[agent_id]
        metric["call_count"] += 1
        metric["total_ms"] += int(body.get("latency_ms", 0) or 0)
        if bool(body.get("error", False)):
            metric["error_count"] += 1
        metric["last_run"] = datetime.utcnow().isoformat() + "Z"
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════════════
# MULTIAGENT: ORCHESTRATOR CONFIG
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/orchestrator/config",
    summary="Конфигурация оркестратора",
)
async def admin_orchestrator_get_config():
    runtime_metrics = getattr(orchestrator, "_agent_metrics", None)
    source = runtime_metrics if isinstance(runtime_metrics, dict) and runtime_metrics else _agent_metrics
    with _agent_metrics_lock:
        agents_enabled = {agent_id: bool(metric.get("enabled", True)) for agent_id, metric in source.items()}
    env_flags = _env_flags_snapshot()
    actual_mode = _compute_env_pipeline_mode()
    return {
        "pipeline_mode": _orchestrator_mode["pipeline_mode"],
        "actual_pipeline_mode": actual_mode,
        "env_flags": env_flags,
        "agents_enabled": agents_enabled,
        "pipeline_version": getattr(orchestrator, "pipeline_version", "multiagent_v1"),
    }


@admin_router.patch(
    "/orchestrator/config",
    summary="Изменить режим пайплайна",
)
async def admin_orchestrator_patch_config(body: dict):
    valid_modes = {"full_multiagent", "hybrid", "legacy_adaptive"}
    mode = str(body.get("pipeline_mode", ""))
    if mode not in valid_modes:
        raise HTTPException(status_code=422, detail=f"Invalid pipeline_mode '{mode}'. Valid: {sorted(valid_modes)}")
    _orchestrator_mode["pipeline_mode"] = mode
    return {"pipeline_mode": mode, "status": "ok"}


# ══════════════════════════════════════════════════════════════════════
# MULTIAGENT: AGENT TRACES
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/agents/traces",
    summary="Трассировки агентов по последним запросам",
)
async def admin_agents_traces(
    limit: int = Query(default=50, ge=1, le=200),
    agent_id: str | None = Query(default=None),
):
    runtime_traces = getattr(orchestrator, "_agent_traces", None)
    if isinstance(runtime_traces, list) and runtime_traces:
        traces = list(runtime_traces)
    else:
        with _agent_metrics_lock:
            traces = list(_agent_traces)
    if agent_id:
        traces = [trace for trace in traces if trace.get("agent_id") == agent_id]
    return {"traces": traces[-limit:][::-1], "total": len(traces)}


@admin_router.get(
    "/overview",
    summary="Обзор состояния multiagent runtime",
)
async def admin_overview():
    env_flags = _env_flags_snapshot()
    pipeline_mode = _compute_env_pipeline_mode()
    agents = _compute_agent_metrics()
    traces = getattr(orchestrator, "_agent_traces", None)
    if isinstance(traces, list):
        recent_traces = traces[-5:][::-1]
    else:
        recent_traces = list(_agent_traces)[-5:][::-1]
    return {
        "pipeline_mode": pipeline_mode,
        "feature_flags": env_flags,
        "agents": [
            {
                "agent_id": item.get("id"),
                "enabled": item.get("enabled", True),
                "calls": item.get("call_count", 0),
                "errors": item.get("error_count", 0),
                "avg_ms": item.get("avg_latency_ms", 0),
                "last_run": item.get("last_run"),
            }
            for item in agents
        ],
        "recent_traces": recent_traces,
        "server_time": datetime.now(timezone.utc).isoformat(),
        "schema_version": ADMIN_SCHEMA_VERSION,
    }


@admin_router.post(
    "/agents/traces/record",
    summary="Записать трассировку агента (internal)",
)
async def admin_agents_traces_record(body: dict):
    trace = {
        "agent_id": str(body.get("agent_id", "unknown")),
        "request_id": str(body.get("request_id", "")),
        "user_id": str(body.get("user_id", "")),
        "input_preview": str(body.get("input_preview", ""))[:300],
        "output_preview": str(body.get("output_preview", ""))[:300],
        "latency_ms": int(body.get("latency_ms", 0) or 0),
        "error": body.get("error"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    with _agent_metrics_lock:
        _agent_traces.append(trace)
    return {"status": "ok"}


# ══════════════════════════════════════════════════════════════════════
# MULTIAGENT: THREADS
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/threads",
    summary="Список тредов (активные/архивные)",
)
async def admin_threads_list(
    status: str | None = Query(default="active"),
    user_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    if status == "active":
        threads = _list_active_threads()
    elif status == "archived":
        threads = _list_archived_threads()
    else:
        threads = _list_active_threads() + _list_archived_threads()
    if user_id:
        threads = [thread for thread in threads if thread.get("user_id") == user_id]
    return {"threads": threads[:limit], "total": len(threads)}


@admin_router.delete(
    "/threads/{user_id}",
    summary="Удалить активный тред пользователя",
)
async def admin_threads_delete(user_id: str):
    active_path = _get_thread_storage_dir() / f"{user_id}_active.json"
    if not active_path.exists():
        raise HTTPException(status_code=404, detail=f"No active thread for user: {user_id}")
    active_path.unlink()
    return {"status": "ok", "user_id": user_id, "deleted": "active_thread"}


# ══════════════════════════════════════════════════════════════════════
# MULTIAGENT: AGENT PROMPTS
# ══════════════════════════════════════════════════════════════════════

@admin_router.get(
    "/agents/{agent_id}/prompts",
    summary="Промпты конкретного агента",
)
async def admin_agent_prompts_get(agent_id: str):
    if agent_id not in _AGENT_PROMPT_MAP:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_id}' has no managed prompts. Valid: {sorted(_AGENT_PROMPT_MAP)}",
        )
    raw = _get_agent_prompts_raw(agent_id)
    overrides = _agent_prompt_overrides.get(agent_id, {})
    prompts = []
    for key, text in sorted(raw.items()):
        text_override = overrides.get(key)
        effective_text = text_override if text_override is not None else text
        prompts.append(
            {
                "key": key,
                "text": effective_text,
                "default_text": text,
                "is_overridden": text_override is not None,
                "char_count": len(effective_text),
            }
        )
    return {"agent_id": agent_id, "prompts": prompts}


@admin_router.put(
    "/agents/{agent_id}/prompts/{prompt_key}",
    summary="Обновить промпт агента (in-memory override)",
)
async def admin_agent_prompts_update(agent_id: str, prompt_key: str, body: dict):
    if agent_id not in _AGENT_PROMPT_MAP:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    raw = _get_agent_prompts_raw(agent_id)
    if prompt_key not in raw:
        raise HTTPException(status_code=404, detail=f"Unknown prompt_key: {prompt_key}")
    text = str(body.get("text", "") or "")
    if len(text.strip()) < 20:
        raise HTTPException(status_code=422, detail="Prompt text too short")
    overrides = _agent_prompt_overrides.setdefault(agent_id, {})
    overrides[prompt_key] = text
    return {
        "status": "ok",
        "agent_id": agent_id,
        "prompt_key": prompt_key,
        "is_overridden": True,
        "char_count": len(text),
    }


@admin_router.post(
    "/agents/{agent_id}/prompts/{prompt_key}/reset",
    summary="Сбросить override промпта агента",
)
async def admin_agent_prompts_reset(agent_id: str, prompt_key: str):
    if agent_id not in _AGENT_PROMPT_MAP:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_id}")
    raw = _get_agent_prompts_raw(agent_id)
    if prompt_key not in raw:
        raise HTTPException(status_code=404, detail=f"Unknown prompt_key: {prompt_key}")
    _agent_prompt_overrides.setdefault(agent_id, {}).pop(prompt_key, None)
    return {"status": "ok", "agent_id": agent_id, "prompt_key": prompt_key, "is_overridden": False}


# ══════════════════════════════════════════════════════════════════════
# FULL RESET
# ══════════════════════════════════════════════════════════════════════

@admin_router.post(
    "/reset-all",
    summary="Полный сброс — и конфиг, и промты",
)
async def admin_reset_everything():
    """Удаляет ВСЕ overrides. Бот вернётся к состоянию 'из коробки'."""
    config.reset_all_overrides()
    return {"status": "ok", "message": "Все overrides удалены. Восстановлены дефолты."}

async def _admin_user_identity_payload(
    user_id: str,
    identity_service: IdentityService,
) -> dict[str, Any]:
    user = await identity_service.get_user(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User not found: {user_id}")

    linked = await identity_service.get_linked_identities(user_id)
    sessions = await identity_service.get_active_sessions(user_id, limit=50)

    return {
        "user_id": user.id,
        "created_at": user.created_at.isoformat(),
        "status": user.status,
        "linked_identities": [
            {
                "provider": item.provider,
                "external_id": mask_external_id(item.provider, item.external_id),
                "verified_at": item.verified_at.isoformat() if item.verified_at else None,
            }
            for item in linked
        ],
        "active_sessions": [
            {
                "session_id": item.session_id,
                "channel": item.channel,
                "last_seen_at": item.last_seen_at.isoformat() if item.last_seen_at else None,
            }
            for item in sessions
        ],
    }


@admin_router.get(
    "/users/{user_id}/identity",
    summary="Identity details for a user",
)
@admin_router_v1.get(
    "/users/{user_id}/identity",
    summary="Identity details for a user (v1 route)",
)
async def admin_get_user_identity(
    user_id: str,
    identity_service: IdentityService = Depends(get_identity_service),
):
    return await _admin_user_identity_payload(user_id=user_id, identity_service=identity_service)
