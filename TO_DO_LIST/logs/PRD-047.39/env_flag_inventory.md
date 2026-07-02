# PRD-047.39 Env / Flag Inventory

- flag_count: `103`

| Flag | Default | Read in files | Controls | PRD hint | Proposed status |
| --- | --- | --- | --- | --- | --- |
| ADMIN_ACCESS_KEY | <required> | bot_psychologist/api/registration/bootstrap.py:84 | API service runtime | unknown | frozen_default_only |
| ADMIN_INVITE_KEY | <required> | bot_psychologist/api/registration/bootstrap.py:80 | API service runtime | unknown | frozen_default_only |
| ADMIN_USERNAME | <required> | bot_psychologist/api/registration/bootstrap.py:79 | API service runtime | unknown | frozen_default_only |
| ALL_BLOCKS_MERGED_PATH | "" | bot_psychologist/bot_agent/config.py:76, bot_psychologist/bot_agent/runtime_config.py:786 | runtime configuration | unknown | active_tunable |
| APP_ENV | "" | bot_psychologist/bot_agent/feature_flags.py:107 | runtime configuration | PRD-047.22-HF2 | active_tunable |
| ARCHIVE_RETENTION_DAYS | "365" | bot_psychologist/bot_agent/config.py:220 | runtime configuration | unknown | frozen_default_only |
| AUTHOR_BLEND_MODE | "all" | bot_psychologist/bot_agent/config.py:88 | runtime configuration | unknown | frozen_default_only |
| AUTO_CLEANUP_ENABLED | "True" | bot_psychologist/bot_agent/config.py:221 | runtime configuration | unknown | frozen_default_only |
| BOT_DB_CIRCUIT_BREAKER_ENABLED | "true" | bot_psychologist/bot_agent/runtime_config.py:778 | runtime configuration | unknown | active_tunable |
| BOT_DB_CIRCUIT_BREAKER_TTL_SECONDS | "60" | bot_psychologist/bot_agent/config.py:65, bot_psychologist/bot_agent/runtime_config.py:781 | runtime configuration | unknown | active_tunable |
| BOT_DB_FAST_FAIL_ON_503 | "true" | bot_psychologist/bot_agent/runtime_config.py:783 | runtime configuration | unknown | active_tunable |
| BOT_DB_PATH | "data/bot_sessions.db" | bot_psychologist/bot_agent/config.py:216 | runtime configuration | unknown | frozen_default_only |
| BOT_DB_TIMEOUT | "10.0" | bot_psychologist/bot_agent/config.py:59, bot_psychologist/bot_agent/db_api_client.py:18, bot_psychologist/bot_agent/runtime_config.py:776 | API service runtime | unknown | active_tunable |
| BOT_DB_URL | "http://localhost:8003" | bot_psychologist/bot_agent/config.py:58, bot_psychologist/bot_agent/db_api_client.py:17, bot_psychologist/bot_agent/runtime_config.py:775 | API service runtime | unknown | active_tunable |
| CHROMA_API_URL | "http://localhost:8004" | bot_psychologist/bot_agent/config.py:56, bot_psychologist/bot_agent/runtime_config.py:784 | retrieval or vector-store behavior | unknown | active_tunable |
| CHROMA_COLLECTION | "bot_knowledge" | bot_psychologist/bot_agent/config.py:57, bot_psychologist/bot_agent/runtime_config.py:785 | retrieval or vector-store behavior | unknown | active_tunable |
| CLASSIFIER_MODEL | "gpt-4o-mini" | bot_psychologist/bot_agent/config.py:96 | runtime configuration | unknown | frozen_default_only |
| CONFIDENCE_CAP_HIGH | "7" | bot_psychologist/bot_agent/config.py:89, bot_psychologist/bot_agent/runtime_config.py:799 | runtime configuration | unknown | active_tunable |
| CONFIDENCE_CAP_LOW | "3" | bot_psychologist/bot_agent/config.py:91, bot_psychologist/bot_agent/runtime_config.py:801 | runtime configuration | unknown | active_tunable |
| CONFIDENCE_CAP_MEDIUM | "5" | bot_psychologist/bot_agent/config.py:90, bot_psychologist/bot_agent/runtime_config.py:800 | runtime configuration | unknown | active_tunable |
| CONFIDENCE_CAP_ZERO | "0" | bot_psychologist/bot_agent/config.py:92, bot_psychologist/bot_agent/runtime_config.py:802 | runtime configuration | unknown | active_tunable |
| CONVERSATION_HISTORY_DEPTH | "3" | bot_psychologist/bot_agent/config.py:166 | runtime configuration | unknown | frozen_default_only |
| DATA_ROOT | "../voice_bot_pipeline/data" | bot_psychologist/bot_agent/config.py:42 | runtime configuration | unknown | frozen_default_only |
| DATA_SOURCE | "unknown" | bot_psychologist/bot_agent/config.py:78, bot_psychologist/bot_agent/runtime_config.py:820 | runtime configuration | unknown | active_tunable |
| DB_EXPORT_FILE | "" | bot_psychologist/bot_agent/config.py:82, bot_psychologist/bot_agent/runtime_config.py:788 | runtime configuration | unknown | active_tunable |
| DB_JSON_DIR | "" | bot_psychologist/bot_agent/config.py:81, bot_psychologist/bot_agent/runtime_config.py:787 | runtime configuration | unknown | active_tunable |
| DEBUG | "False" | bot_psychologist/bot_agent/config.py:224 | debug and trace visibility | unknown | frozen_default_only |
| DECISION_GATE_RULE_THRESHOLD | "0.75" | bot_psychologist/bot_agent/config.py:159, bot_psychologist/bot_agent/runtime_config.py:815 | runtime configuration | unknown | active_tunable |
| DEGRADED_MODE | "False", "false" | bot_psychologist/bot_agent/config.py:77, bot_psychologist/bot_agent/runtime_config.py:821 | runtime configuration | unknown | active_tunable |
| DEV_API_KEY | <required> | bot_psychologist/api/auth.py:41, bot_psychologist/api/registration/bootstrap.py:41 | provider credentials / model provider integration | unknown | frozen_default_only |
| DIAGNOSTIC_CENTER_CREATOR_USER_ID | "", "creator" | bot_psychologist/bot_agent/diagnostic_center_control.py:78, bot_psychologist/bot_agent/multiagent/diagnostic_center_creator_live_activation.py:231 | runtime configuration | unknown | frozen_default_only |
| DIAGNOSTIC_CENTER_DEVELOPER_USER_IDS | "" | bot_psychologist/bot_agent/diagnostic_center_control.py:82 | runtime configuration | unknown | frozen_default_only |
| DIALOGUE_PROFILE | "safe_guided" | bot_psychologist/bot_agent/config.py:102, bot_psychologist/bot_agent/runtime_config.py:797 | runtime configuration | unknown | active_tunable |
| EMBEDDING_DEVICE | "auto" | bot_psychologist/bot_agent/config.py:176 | runtime configuration | unknown | frozen_default_only |
| EMBEDDING_MODEL | "intfloat/multilingual-e5-base" | bot_psychologist/bot_agent/config.py:175 | runtime configuration | unknown | frozen_default_only |
| ENABLE_CONVERSATION_SUMMARY | "True" | bot_psychologist/bot_agent/config.py:189 | runtime configuration | unknown | frozen_default_only |
| ENABLE_KNOWLEDGE_GRAPH | "False" | bot_psychologist/bot_agent/config.py:145 | runtime configuration | unknown | frozen_default_only |
| ENABLE_SEMANTIC_MEMORY | "True" | bot_psychologist/bot_agent/config.py:171 | semantic-card pilot behavior | unknown | frozen_default_only |
| ENABLE_SESSION_STORAGE | "True" | bot_psychologist/bot_agent/config.py:215 | retrieval or vector-store behavior | unknown | frozen_default_only |
| ENABLE_STREAMING | "True" | bot_psychologist/bot_agent/config.py:144 | runtime configuration | unknown | frozen_default_only |
| FAST_DETECTOR_CONFIDENCE_THRESHOLD | "0.80" | bot_psychologist/bot_agent/config.py:150, bot_psychologist/bot_agent/runtime_config.py:806 | runtime configuration | unknown | active_tunable |
| FAST_DETECTOR_ENABLED | "True", "true" | bot_psychologist/bot_agent/config.py:148, bot_psychologist/bot_agent/runtime_config.py:804 | runtime configuration | unknown | active_tunable |
| FREE_CONVERSATION_MODE | "False", "false" | bot_psychologist/bot_agent/config.py:101, bot_psychologist/bot_agent/runtime_config.py:796 | runtime configuration | unknown | active_tunable |
| INTERNAL_TELEGRAM_KEY | <required> | bot_psychologist/api/auth.py:43, bot_psychologist/api/registration/bootstrap.py:43, bot_psychologist/api/registration/routes.py:81 | API service runtime | unknown | frozen_default_only |
| KNOWLEDGE_SOURCE | "json" | bot_psychologist/bot_agent/config.py:53, bot_psychologist/bot_agent/runtime_config.py:774 | runtime configuration | unknown | active_tunable |
| LEGACY_PIPELINE_ENABLED | "off" | bot_psychologist/api/admin_routes.py:90 | admin API/runtime surface | unknown | retirement_candidate |
| MAX_CONTEXT_SIZE | "2000" | bot_psychologist/bot_agent/config.py:167 | runtime configuration | unknown | frozen_default_only |
| MAX_CONVERSATION_TURNS | "1000" | bot_psychologist/bot_agent/config.py:168 | runtime configuration | unknown | frozen_default_only |
| MAX_TOKENS | "" | bot_psychologist/bot_agent/runtime_config.py:793 | runtime configuration | unknown | active_tunable |
| MAX_TOKENS_SOFT_CAP | "8192" | bot_psychologist/bot_agent/config.py:100, bot_psychologist/bot_agent/runtime_config.py:795 | runtime configuration | unknown | active_tunable |
| MIN_RELEVANCE_SCORE | "0.1" | bot_psychologist/bot_agent/config.py:87, bot_psychologist/bot_agent/runtime_config.py:792 | runtime configuration | unknown | active_tunable |
| MULTIAGENT_ENABLED | "off" | bot_psychologist/api/admin_routes.py:89 | admin API/runtime surface | unknown | frozen_default_only |
| NEO_MINDBOT_ENABLED | "off" | bot_psychologist/api/admin_routes.py:91 | admin API/runtime surface | unknown | frozen_default_only |
| OPENAI_API_KEY | <required> | bot_psychologist/bot_agent/config.py:113 | provider credentials / model provider integration | unknown | active_tunable |
| PRIMARY_MODEL | "gpt-4o-mini" | bot_psychologist/bot_agent/config.py:95 | runtime configuration | unknown | frozen_default_only |
| PROMPT_MODE_OVERRIDES_SD | "True" | bot_psychologist/bot_agent/config.py:163 | runtime configuration | unknown | frozen_default_only |
| REASONING_EFFORT | "low" | bot_psychologist/bot_agent/config.py:133 | runtime configuration | unknown | frozen_default_only |
| RECENT_WINDOW | "4" | bot_psychologist/bot_agent/config.py:192 | runtime configuration | unknown | frozen_default_only |
| RERANKER_BLOCK_THRESHOLD | "8" | bot_psychologist/bot_agent/config.py:186 | runtime configuration | unknown | frozen_default_only |
| RERANKER_CONFIDENCE_THRESHOLD | "0.35" | bot_psychologist/bot_agent/config.py:184 | runtime configuration | unknown | frozen_default_only |
| RERANKER_ENABLED | "False" | bot_psychologist/bot_agent/config.py:183 | runtime configuration | unknown | frozen_default_only |
| RERANKER_MODE_WHITELIST | "THINKING,INTERVENTION" | bot_psychologist/bot_agent/config.py:185 | runtime configuration | unknown | frozen_default_only |
| RETRIEVAL_TOP_K | "5" | bot_psychologist/bot_agent/config.py:85, bot_psychologist/bot_agent/runtime_config.py:790 | retrieval or vector-store behavior | unknown | active_tunable |
| SEMANTIC_MAX_CHARS | "1000" | bot_psychologist/bot_agent/config.py:174 | semantic-card pilot behavior | unknown | frozen_default_only |
| SEMANTIC_MIN_SIMILARITY | "0.6" | bot_psychologist/bot_agent/config.py:173 | semantic-card pilot behavior | unknown | frozen_default_only |
| SEMANTIC_SEARCH_TOP_K | "3" | bot_psychologist/bot_agent/config.py:172 | semantic-card pilot behavior | unknown | frozen_default_only |
| SESSION_RETENTION_DAYS | "90" | bot_psychologist/bot_agent/config.py:219 | runtime configuration | unknown | frozen_default_only |
| STATE_CLASSIFIER_CONFIDENCE_THRESHOLD | "0.65" | bot_psychologist/bot_agent/config.py:157, bot_psychologist/bot_agent/runtime_config.py:813 | runtime configuration | unknown | active_tunable |
| STATE_CLASSIFIER_ENABLED | "True", "true" | bot_psychologist/bot_agent/config.py:155, bot_psychologist/bot_agent/runtime_config.py:811 | runtime configuration | unknown | active_tunable |
| SUMMARIZER_FALLBACK_ON_EMPTY | "True" | bot_psychologist/bot_agent/config.py:197 | runtime configuration | unknown | frozen_default_only |
| SUMMARIZER_FALLBACK_RETRIES | "2" | bot_psychologist/bot_agent/config.py:198 | runtime configuration | unknown | frozen_default_only |
| SUMMARIZER_MIN_TURNS | "3" | bot_psychologist/bot_agent/config.py:196 | runtime configuration | unknown | frozen_default_only |
| SUMMARIZER_MODEL | "gpt-4o-mini" | bot_psychologist/bot_agent/config.py:194 | runtime configuration | unknown | frozen_default_only |
| SUMMARIZER_REASONING_EFFORT | "low" | bot_psychologist/bot_agent/config.py:195 | runtime configuration | unknown | frozen_default_only |
| SUMMARY_MAX_CHARS | "300" | bot_psychologist/bot_agent/config.py:193 | runtime configuration | unknown | frozen_default_only |
| SUMMARY_UPDATE_INTERVAL | "3" | bot_psychologist/bot_agent/config.py:190 | runtime configuration | unknown | frozen_default_only |
| SUMMARY_WINDOW_SIZE | "5" | bot_psychologist/bot_agent/config.py:191 | runtime configuration | unknown | frozen_default_only |
| TELEGRAM_ALLOWED_UPDATES | <required> | bot_psychologist/api/telegram_adapter/config.py:76 | API service runtime | unknown | frozen_default_only |
| TELEGRAM_BOT_TOKEN | <required> | bot_psychologist/api/telegram_adapter/config.py:65 | API service runtime | unknown | frozen_default_only |
| TELEGRAM_ENABLED | <required> | bot_psychologist/api/telegram_adapter/config.py:58 | API service runtime | unknown | frozen_default_only |
| TELEGRAM_MODE | <required> | bot_psychologist/api/telegram_adapter/config.py:59 | API service runtime | unknown | frozen_default_only |
| TELEGRAM_POLLING_MAX_RETRY_DELAY | <required> | bot_psychologist/api/telegram_adapter/config.py:74 | API service runtime | unknown | frozen_default_only |
| TELEGRAM_POLLING_RETRY_DELAY | <required> | bot_psychologist/api/telegram_adapter/config.py:70 | API service runtime | unknown | frozen_default_only |
| TELEGRAM_POLLING_TIMEOUT | <required> | bot_psychologist/api/telegram_adapter/config.py:68 | API service runtime | unknown | frozen_default_only |
| TELEGRAM_WEBHOOK_SECRET | <required> | bot_psychologist/api/telegram_adapter/config.py:67 | API service runtime | unknown | frozen_default_only |
| TELEGRAM_WEBHOOK_URL | <required> | bot_psychologist/api/telegram_adapter/config.py:66 | API service runtime | unknown | frozen_default_only |
| TEST_API_KEY | <required> | bot_psychologist/api/auth.py:42, bot_psychologist/api/registration/bootstrap.py:42 | provider credentials / model provider integration | unknown | frozen_default_only |
| THREAD_STORAGE_DIR | <required> | bot_psychologist/api/admin_routes.py:419 | retrieval or vector-store behavior | unknown | frozen_default_only |
| TURN_LLM_SUMMARY_DEBUG_PREVIEW_CHARS | "160" | bot_psychologist/bot_agent/config.py:212 | debug and trace visibility | unknown | frozen_default_only |
| TURN_LLM_SUMMARY_ENABLED | "False" | bot_psychologist/bot_agent/config.py:201 | runtime configuration | unknown | frozen_default_only |
| TURN_LLM_SUMMARY_MAX_INPUT_CHARS | "6000" | bot_psychologist/bot_agent/config.py:207 | runtime configuration | unknown | frozen_default_only |
| TURN_LLM_SUMMARY_MAX_PENDING_PER_RUN | "10" | bot_psychologist/bot_agent/config.py:209 | runtime configuration | unknown | frozen_default_only |
| TURN_LLM_SUMMARY_MAX_RETRIES | "1" | bot_psychologist/bot_agent/config.py:211 | runtime configuration | unknown | frozen_default_only |
| TURN_LLM_SUMMARY_MAX_SUMMARY_CHARS | "700" | bot_psychologist/bot_agent/config.py:208 | runtime configuration | unknown | frozen_default_only |
| TURN_LLM_SUMMARY_MODEL | "gpt-4o-mini" | bot_psychologist/bot_agent/config.py:206 | runtime configuration | unknown | frozen_default_only |
| TURN_LLM_SUMMARY_PROVIDER | "disabled" | bot_psychologist/bot_agent/config.py:205 | runtime configuration | unknown | frozen_default_only |
| TURN_LLM_SUMMARY_TIMEOUT_SECONDS | "20" | bot_psychologist/bot_agent/config.py:210 | runtime configuration | unknown | frozen_default_only |
| TURN_LLM_SUMMARY_USE_IN_CONTEXT | "True" | bot_psychologist/bot_agent/config.py:203 | runtime configuration | unknown | frozen_default_only |
| VOYAGE_API_KEY | <required> | bot_psychologist/bot_agent/config.py:179 | provider credentials / model provider integration | unknown | active_tunable |
| VOYAGE_ENABLED | "False" | bot_psychologist/bot_agent/config.py:182 | provider credentials / model provider integration | unknown | active_tunable |
| VOYAGE_MODEL | "rerank-2" | bot_psychologist/bot_agent/config.py:180 | provider credentials / model provider integration | unknown | active_tunable |
| VOYAGE_TOP_K | "5" | bot_psychologist/bot_agent/config.py:181 | provider credentials / model provider integration | unknown | active_tunable |
| WARMUP_ON_START | "True" | bot_psychologist/bot_agent/config.py:143 | runtime configuration | unknown | frozen_default_only |

## Classification Policy
- `active_tunable`: still a real operational/configuration surface.
- `frozen_default_only`: candidate for PRD-047.41 effective-config consolidation.
- `retirement_candidate`: legacy/SD/user-level naming that needs separate proof before removal.
