# PRD-047.41 Effective Config Registry Snapshot

- flag_count: `103`
- admin_hot_editable_count: `35`
- editable_env_intersection_count: `35`
- editable_non_env_keys: `['ENABLE_CACHING', 'LLM_MAX_TOKENS', 'LLM_MODEL', 'LLM_TEMPERATURE', 'TOP_K_BLOCKS']`

## Status Counts
| Status | Count |
| --- | --- |
| active_tunable | 51 |
| frozen_constant | 41 |
| retirement_candidate_deferred | 1 |
| secret | 10 |

## Registry Entries
| Flag | Status | Source | Admin hot-editable | Current value | Notes |
| --- | --- | --- | --- | --- | --- |
| ADMIN_ACCESS_KEY | secret | env | False | {"is_set": false} | Secret flag: export only is_set, never raw value. |
| ADMIN_INVITE_KEY | secret | env | False | {"is_set": false} | Secret flag: export only is_set, never raw value. |
| ADMIN_USERNAME | secret | env | False | {"is_set": false} | Secret flag: export only is_set, never raw value. |
| ALL_BLOCKS_MERGED_PATH | active_tunable | env | False | C:/My_practice/Text_transcription/Bot_data_base/data/processed/all_blocks_merged.json | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| APP_ENV | active_tunable | env | False |  | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| ARCHIVE_RETENTION_DAYS | active_tunable | env | True | 365 | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| AUTHOR_BLEND_MODE | frozen_constant | constant | False | all | Frozen constant per PRD-047.41 bucket A. |
| AUTO_CLEANUP_ENABLED | active_tunable | env | True | True | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| BOT_DB_CIRCUIT_BREAKER_ENABLED | active_tunable | env | False | True | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| BOT_DB_CIRCUIT_BREAKER_TTL_SECONDS | active_tunable | env | False | 60.0 | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| BOT_DB_FAST_FAIL_ON_503 | active_tunable | env | False | True | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| BOT_DB_PATH | frozen_constant | constant | False | C:\My_practice\Text_transcription\bot_psychologist\data\bot_sessions.db | Frozen constant per PRD-047.41 bucket A. |
| BOT_DB_TIMEOUT | active_tunable | env | False | 10.0 | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| BOT_DB_URL | active_tunable | env | False | http://localhost:8003 | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| CHROMA_API_URL | active_tunable | env | False | http://localhost:8003 | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| CHROMA_COLLECTION | active_tunable | env | False | bot_knowledge | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| CLASSIFIER_MODEL | active_tunable | env | True | gpt-5-nano | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| CONFIDENCE_CAP_HIGH | active_tunable | env | True | 7 | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| CONFIDENCE_CAP_LOW | active_tunable | env | True | 3 | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| CONFIDENCE_CAP_MEDIUM | active_tunable | env | True | 5 | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| CONFIDENCE_CAP_ZERO | active_tunable | env | True | 0 | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| CONVERSATION_HISTORY_DEPTH | active_tunable | env | True | 3 | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| DATA_ROOT | frozen_constant | constant | False | C:\My_practice\Text_transcription\bot_psychologist\..\voice_bot_pipeline\data | Frozen constant per PRD-047.41 bucket A. |
| DATA_SOURCE | active_tunable | env | False | unknown | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| DB_EXPORT_FILE | active_tunable | env | False |  | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| DB_JSON_DIR | active_tunable | env | False |  | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| DEBUG | frozen_constant | constant | False | False | Frozen constant per PRD-047.41 bucket A. |
| DECISION_GATE_RULE_THRESHOLD | active_tunable | env | False | 0.75 | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| DEGRADED_MODE | active_tunable | env | False | False | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| DEV_API_KEY | secret | env | False | {"is_set": false} | Secret flag: export only is_set, never raw value. |
| DIAGNOSTIC_CENTER_CREATOR_USER_ID | frozen_constant | constant | False | creator | Frozen constant per PRD-047.41 bucket A. |
| DIAGNOSTIC_CENTER_DEVELOPER_USER_IDS | frozen_constant | constant | False | ['creator'] | Frozen constant per PRD-047.41 bucket A. |
| DIALOGUE_PROFILE | active_tunable | env | True | mvp_free_dialogue | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| EMBEDDING_DEVICE | frozen_constant | constant | False | auto | Frozen constant per PRD-047.41 bucket A. |
| EMBEDDING_MODEL | frozen_constant | constant | False | intfloat/multilingual-e5-base | Frozen constant per PRD-047.41 bucket A. |
| ENABLE_CONVERSATION_SUMMARY | active_tunable | env | True | True | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| ENABLE_KNOWLEDGE_GRAPH | active_tunable | env | True | False | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| ENABLE_SEMANTIC_MEMORY | active_tunable | env | True | True | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| ENABLE_SESSION_STORAGE | active_tunable | env | True | True | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| ENABLE_STREAMING | active_tunable | env | True | True | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| FAST_DETECTOR_CONFIDENCE_THRESHOLD | active_tunable | env | True | 0.8 | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| FAST_DETECTOR_ENABLED | active_tunable | env | True | True | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| FREE_CONVERSATION_MODE | active_tunable | env | True | False | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| INTERNAL_TELEGRAM_KEY | secret | env | False | {"is_set": false} | Secret flag: export only is_set, never raw value. |
| KNOWLEDGE_SOURCE | active_tunable | env | False | api | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| LEGACY_PIPELINE_ENABLED | retirement_candidate_deferred | env | False | false | Deferred legacy compatibility marker awaiting explicit owner decision. |
| MAX_CONTEXT_SIZE | active_tunable | env | True | 2000 | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| MAX_CONVERSATION_TURNS | active_tunable | env | True | 1000 | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| MAX_TOKENS | active_tunable | env | True | None | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| MAX_TOKENS_SOFT_CAP | active_tunable | env | True | 8192 | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| MIN_RELEVANCE_SCORE | active_tunable | env | True | 0.1 | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| MULTIAGENT_ENABLED | frozen_constant | constant | False | off | Deprecated compatibility marker kept as literal constant after PRD-036. |
| NEO_MINDBOT_ENABLED | frozen_constant | constant | False | off | Deprecated compatibility marker kept as literal constant after PRD-036. |
| OPENAI_API_KEY | secret | env | False | {"is_set": true} | Secret flag: export only is_set, never raw value. |
| PRIMARY_MODEL | frozen_constant | constant | False | gpt-4o-mini | Frozen constant per PRD-047.41 bucket A. |
| PROMPT_MODE_OVERRIDES_SD | frozen_constant | constant | False | True | Frozen constant per PRD-047.41 bucket A. |
| REASONING_EFFORT | active_tunable | env | True | low | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| RECENT_WINDOW | frozen_constant | constant | False | 4 | Frozen constant per PRD-047.41 bucket A. |
| RERANKER_BLOCK_THRESHOLD | frozen_constant | constant | False | 8 | Frozen constant per PRD-047.41 bucket A. |
| RERANKER_CONFIDENCE_THRESHOLD | frozen_constant | constant | False | 0.35 | Frozen constant per PRD-047.41 bucket A. |
| RERANKER_ENABLED | frozen_constant | constant | False | False | Frozen constant per PRD-047.41 bucket A. |
| RERANKER_MODE_WHITELIST | frozen_constant | constant | False | THINKING,INTERVENTION | Frozen constant per PRD-047.41 bucket A. |
| RETRIEVAL_TOP_K | active_tunable | env | False | 5 | Active env-backed runtime surface; visible in registry, not admin hot-editable. |
| SEMANTIC_MAX_CHARS | active_tunable | env | True | 1000 | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| SEMANTIC_MIN_SIMILARITY | active_tunable | env | True | 0.7 | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| SEMANTIC_SEARCH_TOP_K | active_tunable | env | True | 3 | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| SESSION_RETENTION_DAYS | active_tunable | env | True | 90 | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| STATE_CLASSIFIER_CONFIDENCE_THRESHOLD | active_tunable | env | True | 0.65 | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| STATE_CLASSIFIER_ENABLED | active_tunable | env | True | True | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| SUMMARIZER_FALLBACK_ON_EMPTY | frozen_constant | constant | False | True | Frozen constant per PRD-047.41 bucket A. |
| SUMMARIZER_FALLBACK_RETRIES | frozen_constant | constant | False | 2 | Frozen constant per PRD-047.41 bucket A. |
| SUMMARIZER_MIN_TURNS | frozen_constant | constant | False | 3 | Frozen constant per PRD-047.41 bucket A. |
| SUMMARIZER_MODEL | frozen_constant | constant | False | gpt-4o-mini | Frozen constant per PRD-047.41 bucket A. |
| SUMMARIZER_REASONING_EFFORT | frozen_constant | constant | False | low | Frozen constant per PRD-047.41 bucket A. |
| SUMMARY_MAX_CHARS | active_tunable | env | True | 500 | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| SUMMARY_UPDATE_INTERVAL | active_tunable | env | True | 5 | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
| SUMMARY_WINDOW_SIZE | frozen_constant | constant | False | 5 | Frozen constant per PRD-047.41 bucket A. |
| TELEGRAM_ALLOWED_UPDATES | frozen_constant | constant | False | ['message'] | Frozen constant in PRD-047.41; reactivate as real config when Telegram deployment PRD lands. |
| TELEGRAM_BOT_TOKEN | secret | env | False | {"is_set": false} | Secret flag: export only is_set, never raw value. |
| TELEGRAM_ENABLED | frozen_constant | constant | False | False | Frozen constant in PRD-047.41; reactivate as real config when Telegram deployment PRD lands. |
| TELEGRAM_MODE | frozen_constant | constant | False | mock | Frozen constant in PRD-047.41; reactivate as real config when Telegram deployment PRD lands. |
| TELEGRAM_POLLING_MAX_RETRY_DELAY | frozen_constant | constant | False | 60.0 | Frozen constant in PRD-047.41; reactivate as real config when Telegram deployment PRD lands. |
| TELEGRAM_POLLING_RETRY_DELAY | frozen_constant | constant | False | 5.0 | Frozen constant in PRD-047.41; reactivate as real config when Telegram deployment PRD lands. |
| TELEGRAM_POLLING_TIMEOUT | frozen_constant | constant | False | 30 | Frozen constant in PRD-047.41; reactivate as real config when Telegram deployment PRD lands. |
| TELEGRAM_WEBHOOK_SECRET | secret | env | False | {"is_set": false} | Secret flag: export only is_set, never raw value. |
| TELEGRAM_WEBHOOK_URL | frozen_constant | constant | False | None | Frozen constant in PRD-047.41; reactivate as real config when Telegram deployment PRD lands. |
| TEST_API_KEY | secret | env | False | {"is_set": false} | Secret flag: export only is_set, never raw value. |
| THREAD_STORAGE_DIR | frozen_constant | constant | False | C:\My_practice\Text_transcription\bot_psychologist\data\threads | Frozen constant per PRD-047.41 bucket A. |
| TURN_LLM_SUMMARY_DEBUG_PREVIEW_CHARS | frozen_constant | constant | False | 160 | Frozen constant per PRD-047.41 bucket A. |
| TURN_LLM_SUMMARY_ENABLED | frozen_constant | constant | False | False | Frozen constant per PRD-047.41 bucket A. |
| TURN_LLM_SUMMARY_MAX_INPUT_CHARS | frozen_constant | constant | False | 6000 | Frozen constant per PRD-047.41 bucket A. |
| TURN_LLM_SUMMARY_MAX_PENDING_PER_RUN | frozen_constant | constant | False | 10 | Frozen constant per PRD-047.41 bucket A. |
| TURN_LLM_SUMMARY_MAX_RETRIES | frozen_constant | constant | False | 1 | Frozen constant per PRD-047.41 bucket A. |
| TURN_LLM_SUMMARY_MAX_SUMMARY_CHARS | frozen_constant | constant | False | 700 | Frozen constant per PRD-047.41 bucket A. |
| TURN_LLM_SUMMARY_MODEL | frozen_constant | constant | False | gpt-4o-mini | Frozen constant per PRD-047.41 bucket A. |
| TURN_LLM_SUMMARY_PROVIDER | frozen_constant | constant | False | disabled | Frozen constant per PRD-047.41 bucket A. |
| TURN_LLM_SUMMARY_TIMEOUT_SECONDS | frozen_constant | constant | False | 20.0 | Frozen constant per PRD-047.41 bucket A. |
| TURN_LLM_SUMMARY_USE_IN_CONTEXT | frozen_constant | constant | False | True | Frozen constant per PRD-047.41 bucket A. |
| VOYAGE_API_KEY | secret | env | False | {"is_set": true} | Secret flag: export only is_set, never raw value. |
| VOYAGE_ENABLED | active_tunable | env | True | True | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| VOYAGE_MODEL | active_tunable | env | True | rerank-2 | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| VOYAGE_TOP_K | active_tunable | env | True | 3 | Active env-backed runtime surface already represented in EDITABLE_CONFIG. |
| WARMUP_ON_START | active_tunable | env | True | True | Reclassified from frozen_default_only per PRD-047.41, owner decision (a) 2026-07-09; no EDITABLE_CONFIG/UI change. |
