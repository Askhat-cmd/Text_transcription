from __future__ import annotations

from .admin_surface_bootstrap import *  # noqa: F401,F403
from .admin_surface_helpers import *  # noqa: F401,F403
from .admin_config_schema import *  # noqa: F401,F403

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


# ======================================================================
# HISTORY
# ======================================================================

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


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# EXPORT / IMPORT
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

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
