# PRD-047.41 Bucket A Constant Conversion Report

- converted_flags: `41`
- audit_rule: git-grep only for `getattr(config, FLAG)` and residual `os.getenv(FLAG)`.
- interpretation: `Remaining env reads` must stay zero outside declared conversion sites.

| Flag | Known conversion paths | getattr(config, FLAG) hits | getattr preview | Remaining env reads | env read preview |
| --- | --- | --- | --- | --- | --- |
| AUTHOR_BLEND_MODE | bot_psychologist/bot_agent/config.py | 0 | none | 0 | none |
| BOT_DB_PATH | bot_psychologist/bot_agent/config.py | 0 | none | 0 | none |
| DATA_ROOT | bot_psychologist/bot_agent/config.py | 0 | none | 0 | none |
| DEBUG | bot_psychologist/bot_agent/config.py | 0 | none | 0 | none |
| DIAGNOSTIC_CENTER_CREATOR_USER_ID | bot_psychologist/bot_agent/diagnostic_center_control.py, bot_psychologist/bot_agent/multiagent/diagnostic_center_creator_live_activation.py | 0 | none | 0 | none |
| DIAGNOSTIC_CENTER_DEVELOPER_USER_IDS | bot_psychologist/bot_agent/diagnostic_center_control.py | 0 | none | 0 | none |
| EMBEDDING_DEVICE | bot_psychologist/bot_agent/config.py | 3 | bot_psychologist/bot_agent/chroma_loader.py:283:            device=str(getattr(config, "EMBEDDING_DEVICE", "auto")),<br>bot_psychologist/bot_agent/retriever.py:256:                device=str(getattr(config, "EMBEDDING_DEVICE", "auto")),<br>bot_psychologist/bot_agent/semantic_memory.py:115:                model_device = getattr(config, "EMBEDDING_DEVICE", "auto") | 0 | none |
| EMBEDDING_MODEL | bot_psychologist/bot_agent/config.py | 6 | bot_psychologist/bot_agent/chroma_loader.py:282:            model_name=str(getattr(config, "EMBEDDING_MODEL", "")),<br>bot_psychologist/bot_agent/retriever.py:128:        hasher.update(str(getattr(config, "EMBEDDING_MODEL", "")).encode())<br>bot_psychologist/bot_agent/retriever.py:179:                    if cached_model == str(getattr(config, "EMBEDDING_MODEL", "")):<br>bot_psychologist/bot_agent/retriever.py:208:                    "embedding_model": str(getattr(config, "EMBEDDING_MODEL", "")), | 0 | none |
| MULTIAGENT_ENABLED | bot_psychologist/api/admin_routes.py | 0 | none | 0 | none |
| NEO_MINDBOT_ENABLED | bot_psychologist/api/admin_routes.py | 0 | none | 0 | none |
| PRIMARY_MODEL | bot_psychologist/bot_agent/config.py | 0 | none | 0 | none |
| PROMPT_MODE_OVERRIDES_SD | bot_psychologist/bot_agent/config.py | 0 | none | 0 | none |
| RECENT_WINDOW | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/memory_updater.py:51:            recent_window=int(getattr(config, "RECENT_WINDOW", 4) or 4), | 0 | none |
| RERANKER_BLOCK_THRESHOLD | bot_psychologist/bot_agent/config.py | 0 | none | 0 | none |
| RERANKER_CONFIDENCE_THRESHOLD | bot_psychologist/bot_agent/config.py | 0 | none | 0 | none |
| RERANKER_ENABLED | bot_psychologist/bot_agent/config.py | 0 | none | 0 | none |
| RERANKER_MODE_WHITELIST | bot_psychologist/bot_agent/config.py | 0 | none | 0 | none |
| SUMMARIZER_FALLBACK_ON_EMPTY | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/conversation_memory.py:933:        if bool(getattr(config, "SUMMARIZER_FALLBACK_ON_EMPTY", True)): | 0 | none |
| SUMMARIZER_FALLBACK_RETRIES | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/conversation_memory.py:886:            getattr(config, "SUMMARIZER_FALLBACK_RETRIES", 2) | 0 | none |
| SUMMARIZER_MIN_TURNS | bot_psychologist/bot_agent/config.py | 2 | bot_psychologist/bot_agent/conversation_memory.py:946:        min_turns = int(getattr(config, "SUMMARIZER_MIN_TURNS", 3) or 3)<br>bot_psychologist/bot_agent/conversation_memory.py:1064:        min_turns = int(getattr(config, "SUMMARIZER_MIN_TURNS", 3) or 3) | 0 | none |
| SUMMARIZER_MODEL | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/conversation_memory.py:884:        model_name = str(getattr(config, "SUMMARIZER_MODEL", "") or config.LLM_MODEL) | 0 | none |
| SUMMARIZER_REASONING_EFFORT | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/conversation_memory.py:904:                        getattr(config, "SUMMARIZER_REASONING_EFFORT", "") or "" | 0 | none |
| SUMMARY_WINDOW_SIZE | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/memory_updater.py:50:            summary_window_size=int(getattr(config, "SUMMARY_WINDOW_SIZE", 5) or 5), | 0 | none |
| TELEGRAM_ALLOWED_UPDATES | bot_psychologist/api/telegram_adapter/config.py | 0 | none | 0 | none |
| TELEGRAM_ENABLED | bot_psychologist/api/telegram_adapter/config.py | 0 | none | 0 | none |
| TELEGRAM_MODE | bot_psychologist/api/telegram_adapter/config.py | 0 | none | 0 | none |
| TELEGRAM_POLLING_MAX_RETRY_DELAY | bot_psychologist/api/telegram_adapter/config.py | 0 | none | 0 | none |
| TELEGRAM_POLLING_RETRY_DELAY | bot_psychologist/api/telegram_adapter/config.py | 0 | none | 0 | none |
| TELEGRAM_POLLING_TIMEOUT | bot_psychologist/api/telegram_adapter/config.py | 0 | none | 0 | none |
| TELEGRAM_WEBHOOK_URL | bot_psychologist/api/telegram_adapter/config.py | 0 | none | 0 | none |
| THREAD_STORAGE_DIR | bot_psychologist/api/admin_routes.py | 0 | none | 0 | none |
| TURN_LLM_SUMMARY_DEBUG_PREVIEW_CHARS | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/multiagent/turn_summary_service.py:93:    preview_len = int(getattr(config, "TURN_LLM_SUMMARY_DEBUG_PREVIEW_CHARS", 160) or 160) | 0 | none |
| TURN_LLM_SUMMARY_ENABLED | bot_psychologist/bot_agent/config.py | 2 | bot_psychologist/bot_agent/conversation_memory.py:585:        if not bool(getattr(config, "TURN_LLM_SUMMARY_ENABLED", False)):<br>bot_psychologist/bot_agent/multiagent/turn_summary_service.py:83:    if not bool(getattr(config, "TURN_LLM_SUMMARY_ENABLED", False)): | 0 | none |
| TURN_LLM_SUMMARY_MAX_INPUT_CHARS | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/multiagent/turn_summary_service.py:178:    max_input_chars = int(getattr(config, "TURN_LLM_SUMMARY_MAX_INPUT_CHARS", 6000) or 6000) | 0 | none |
| TURN_LLM_SUMMARY_MAX_PENDING_PER_RUN | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/conversation_memory.py:588:        max_limit = int(getattr(config, "TURN_LLM_SUMMARY_MAX_PENDING_PER_RUN", 10) or 10) | 0 | none |
| TURN_LLM_SUMMARY_MAX_RETRIES | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/multiagent/turn_summary_service.py:180:    retries = int(getattr(config, "TURN_LLM_SUMMARY_MAX_RETRIES", 1) or 1) | 0 | none |
| TURN_LLM_SUMMARY_MAX_SUMMARY_CHARS | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/multiagent/turn_summary_service.py:106:    max_summary_chars = int(getattr(config, "TURN_LLM_SUMMARY_MAX_SUMMARY_CHARS", 700) or 700) | 0 | none |
| TURN_LLM_SUMMARY_MODEL | bot_psychologist/bot_agent/config.py | 4 | bot_psychologist/bot_agent/conversation_memory.py:439:                    model=str(getattr(config, "TURN_LLM_SUMMARY_MODEL", "") or config.LLM_MODEL),<br>bot_psychologist/bot_agent/conversation_memory.py:610:                model=str(getattr(config, "TURN_LLM_SUMMARY_MODEL", "") or config.LLM_MODEL),<br>bot_psychologist/bot_agent/multiagent/turn_summary_service.py:74:        model=model or str(getattr(config, "TURN_LLM_SUMMARY_MODEL", "") or config.LLM_MODEL),<br>bot_psychologist/bot_agent/multiagent/turn_summary_service.py:177:    model_name = str(model or getattr(config, "TURN_LLM_SUMMARY_MODEL", "") or config.LLM_MODEL) | 0 | none |
| TURN_LLM_SUMMARY_PROVIDER | bot_psychologist/bot_agent/config.py | 5 | bot_psychologist/bot_agent/conversation_memory.py:438:                    provider=str(getattr(config, "TURN_LLM_SUMMARY_PROVIDER", "disabled") or "disabled"),<br>bot_psychologist/bot_agent/conversation_memory.py:602:        provider_name = provider or str(getattr(config, "TURN_LLM_SUMMARY_PROVIDER", "disabled") or "disabled")<br>bot_psychologist/bot_agent/multiagent/turn_summary_service.py:75:        provider=provider or str(getattr(config, "TURN_LLM_SUMMARY_PROVIDER", "disabled") or "disabled"),<br>bot_psychologist/bot_agent/multiagent/turn_summary_service.py:176:    provider_name = str(provider or getattr(config, "TURN_LLM_SUMMARY_PROVIDER", "disabled") or "disabled").lower() | 0 | none |
| TURN_LLM_SUMMARY_TIMEOUT_SECONDS | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/multiagent/turn_summary_service.py:179:    timeout_seconds = float(getattr(config, "TURN_LLM_SUMMARY_TIMEOUT_SECONDS", 20) or 20) | 0 | none |
| TURN_LLM_SUMMARY_USE_IN_CONTEXT | bot_psychologist/bot_agent/config.py | 1 | bot_psychologist/bot_agent/multiagent/context_assembly.py:437:        use_llm_in_context = bool(getattr(config, "TURN_LLM_SUMMARY_USE_IN_CONTEXT", True)) | 0 | none |
