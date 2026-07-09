from __future__ import annotations

from .admin_surface_bootstrap import *  # noqa: F401,F403
from .admin_runtime_compat import *  # noqa: F401,F403
from .admin_surface_helpers import *  # noqa: F401,F403

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


# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# MULTIAGENT: AGENT PROMPTS
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

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

@admin_router.get(
    "/agents/llm-config",
    summary="Получить LLM-модели всех агентов",
)
async def admin_get_agents_llm_config():
    agents = get_all_agent_models()
    thread_manager = agents.get("thread_manager")
    if isinstance(thread_manager, dict):
        thread_manager.update(_thread_manager_llm_meta())
    return {
        "agents": agents,
        "allowed_models": list(ALLOWED_MODELS),
    }


@admin_router.patch(
    "/agents/{agent_id}/llm-config",
    summary="Изменить LLM-конфиг конкретного агента",
)
async def admin_patch_agent_llm_config(agent_id: str, body: dict):
    model_raw = body.get("model")
    model = str(model_raw).strip() if model_raw is not None else ""
    temperature_raw = body.get("temperature")
    if not model and temperature_raw is None:
        raise HTTPException(status_code=422, detail="At least one field is required: 'model' or 'temperature'")
    try:
        if model:
            set_model_for_agent(agent_id, model)
        if temperature_raw is not None:
            set_temperature_for_agent(agent_id, float(temperature_raw))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    agents = get_all_agent_models()
    if agent_id not in agents:
        raise HTTPException(status_code=422, detail=f"Unknown agent_id '{agent_id}'")
    payload = agents[agent_id]
    response = {
        "status": "ok",
        "agent_id": agent_id,
        "model": payload["model"],
        "temperature": payload["temperature"],
        "is_overridden": payload["is_overridden"],
        "is_temperature_overridden": payload["is_temperature_overridden"],
    }
    if agent_id == "thread_manager":
        response.update(_thread_manager_llm_meta())
    return response


@admin_router.post(
    "/agents/{agent_id}/llm-config/reset",
    summary="Сбросить LLM-модель агента к дефолту",
)
async def admin_reset_agent_llm_config(agent_id: str):
    try:
        reset_model_for_agent(agent_id)
        reset_temperature_for_agent(agent_id)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    agents = get_all_agent_models()
    response = {
        "status": "ok",
        "agent_id": agent_id,
        "model": agents[agent_id]["model"],
        "temperature": agents[agent_id]["temperature"],
        "is_overridden": False,
        "is_temperature_overridden": False,
    }
    if agent_id == "thread_manager":
        response.update(_thread_manager_llm_meta())
    return response

# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ
# FULL RESET
# в•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђв•ђ

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
