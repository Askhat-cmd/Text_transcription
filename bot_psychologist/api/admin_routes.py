# api/admin_routes.py
"""
Admin Config Panel — API endpoints.

Все эндпоинты требуют dev-ключ в заголовке X-API-Key.
Роутер регистрируется в main.py через app.include_router(admin_router).
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from typing import Any

from bot_agent.config import config
from bot_agent.data_loader import data_loader
from .auth import is_dev_key


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
    stats = data_loader.get_stats()
    return {
        "degraded_mode": bool(stats.get("degraded_mode", False)),
        "data_source": stats.get("data_source", "unknown"),
        "blocks_loaded": int(stats.get("total_blocks", 0)),
        "version": "0.7.0",
    }


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
async def admin_export_overrides():
    """
    Возвращает полный JSON-файл admin_overrides.json.
    Используется для резервного копирования или переноса между окружениями.
    """
    return config._load_overrides()


@admin_router.post(
    "/import",
    summary="Импортировать overrides из JSON (restore)",
)
async def admin_import_overrides(body: dict):
    """
    Загружает overrides из тела запроса.
    Полностью заменяет текущий admin_overrides.json.
    Валидирует структуру перед сохранением.

    Body: содержимое admin_overrides.json (полученное через /export).
    """
    if not isinstance(body.get("config"), dict):
        raise HTTPException(
            status_code=422, detail="Поле 'config' должно быть объектом"
        )
    if not isinstance(body.get("prompts"), dict):
        raise HTTPException(
            status_code=422, detail="Поле 'prompts' должно быть объектом"
        )
    try:
        config._save_overrides(body)
        return {
            "status": "ok",
            "config_keys": len(body.get("config", {})),
            "prompt_overrides": sum(
                1 for v in body.get("prompts", {}).values() if v is not None
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
