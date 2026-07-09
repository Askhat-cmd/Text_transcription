from __future__ import annotations

from .admin_surface_bootstrap import *  # noqa: F401,F403
from .admin_runtime_compat import *  # noqa: F401,F403
from .admin_surface_helpers import *  # noqa: F401,F403
from .admin_runtime_effective_payload import *  # noqa: F401,F403
from .admin_diagnostics_payload import *  # noqa: F401,F403
from .admin_config_schema import *  # noqa: F401,F403

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
    "/diagnostic-center/effective",
    summary="Diagnostic Center admin control effective payload",
)
@admin_router_v1.get(
    "/diagnostic-center/effective",
    summary="Diagnostic Center admin control effective payload (v1)",
)
async def admin_diagnostic_center_effective():
    return build_diagnostic_center_effective_payload()


@admin_router.post(
    "/diagnostic-center/control",
    summary="Update Diagnostic Center admin control state",
)
@admin_router_v1.post(
    "/diagnostic-center/control",
    summary="Update Diagnostic Center admin control state (v1)",
)
async def admin_diagnostic_center_control_update(body: dict):
    try:
        return apply_diagnostic_center_control_update(body, updated_by="dev")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@admin_router.post(
    "/diagnostic-center/reset",
    summary="Reset Diagnostic Center admin control to safe default",
)
@admin_router_v1.post(
    "/diagnostic-center/reset",
    summary="Reset Diagnostic Center admin control to safe default (v1)",
)
async def admin_diagnostic_center_control_reset():
    return reset_diagnostic_center_control_state(updated_by="dev")


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
