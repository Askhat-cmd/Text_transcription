# Architecture Decisions



## ADR-001 - Multiagent-only runtime

Status: accepted

Context: cascade/legacy path создавал размытые контракты и непредсказуемую диагностику.

Decision: runtime работает через multiagent-only orchestration с явным разделением ролей.

Consequences: выше контролируемость trace и проще quality gating.



## ADR-002 - Writer is not the whole diagnostic system

Status: accepted

Context: попытка возложить диагностику целиком на Writer ухудшает воспроизводимость.

Decision: диагностика распределяется между State Analyzer, Thread Manager, Diagnostic Card и compliance.

Consequences: Writer получает структурированный контекст, а не принимает системные решения в одиночку.



## ADR-003 - Context Assembly over "everything-in-prompt"

Status: accepted

Context: прямое включение всей истории/источников в prompt увеличивает шум и риск drift.

Decision: Context Assembly формирует ограниченный управляемый context package.

Consequences: выше predictability, ниже риск неконтролируемых ссылок и цитирования.



## ADR-004 - Knowledge Base is an internal lens library, not a quote source

Status: accepted

Context: внутренние книги и материалы не должны становиться user-facing цитатником.

Decision: KB используется как internal lens/practice metadata library.

Consequences: Writer не цитирует `КУЗНИЦУ ДУХА` напрямую пользователю.



## ADR-005 - Deterministic governance is authority; LLM enrichment is advisory

Status: accepted

Context: LLM может предложить полезные summaries/lenses, но допускает нестабильность формулировок.

Decision: `chunk_type/allowed_use/safety_flags` остаются deterministic authority.

Consequences: enrichment повышает качество retrieval-context, не разрушая safety contracts.



## ADR-006 - Raw history preserved; summaries are additive

Status: accepted

Context: компрессия истории без сохранения raw turns снижает дебаг и доверие к trace.

Decision: raw dialogue history сохраняется полностью, summary-слои добавочные.

Consequences: можно улучшать summaries без потери первичных данных.



## ADR-007 - Turn LLM summary must be async with deterministic fallback

Status: accepted

Context: синхронная summary-генерация может блокировать response path и деградировать UX.

Decision: async per-turn summary реализуется как additive слой (`pending|ready|failed`) и используется в context assembly только при `ready+valid+hash-match`; иначе deterministic fallback.

Consequences: semantic continuity улучшается без блокировки user-response path и без риска потери контекста при сбоях LLM/provider.



## ADR-008 - Diagnostic Center deferred until readiness gates pass

Status: accepted

Context: преждевременный запуск Diagnostic Center при неготовом KB/context даст ложную уверенность.

Decision: запуск только после APPLY1, retrieval eval и context-quality прогресса.

Consequences: более надежный и интерпретируемый диагностический слой.



## ADR-009 - Applied enrichment stored as advisory metadata only

Status: accepted

Context: после real LLM calibration появился production-candidate overlay, но governance authority должна оставаться deterministic.

Decision: APPLY1 записывает enrichment только в `metadata.llm_enrichment` и retrieval metadata pass-through, не меняя `text/chunk_type/allowed_use/safety_flags`.

Consequences: можно использовать enrichment для контекстного улучшения retrieval без подмены safety/governance контрактов.



## ADR-010 - Turn summary validator must include safety-content guards

Status: accepted

Context: базовая проверка `ready/hash/version` недостаточна для безопасного использования summary в context assembly.

Decision: validator для turn summaries обязан отклонять diagnosis assertions, direct advice/action voice, transcript-style dumps и overlong quote/summary payloads.

Consequences: unsafe summaries автоматически уходят в deterministic fallback, а контекстный слой остаётся устойчивым перед запуском retrieval-eval цикла.



## ADR-011 - Retrieval eval gate is mandatory before Diagnostic Center/Admin Review scale-up

Status: accepted

Context: после APPLY1 качество retrieval должно подтверждаться воспроизводимо, иначе downstream diagnostic/review workflows будут опираться на случайный контекст.

Decision: перед расширением в `PRD-046.0.7` обязателен deterministic retrieval eval gate (dataset + runner + scorecard + weak-case queue) и закрытие safety-gap по `internal_only` exposure.

Consequences: запуск Admin Review/Diagnostic Center откладывается до закрытия `PRD-046.0.6-HF1`, даже при хорошем semantic/gov coverage.



## ADR-012 - Internal-only retrieval hits are suppressed for non-safety user contexts

Status: accepted

Context: PRD-046.0.6 показал утечку `internal_only` hits в non-safety top-k при сохранении хорошего semantic качества.

Decision: API-side retrieval policy (`retrieval_governance_safety_v1`) исключает `internal_only` hits из финального top-k для non-safety запросов; для safety-context allowance сохраняется.

Consequences: закрыт safety-gate (`internal_only_unsafe_exposure_count=0`) без ослабления dataset и без мутации KB/governance authority.



## ADR-013 - Human review decisions are stored as separate overlays before any KB apply step

Status: accepted

Context: после APPLY1 enrichment advisory metadata требует human-review, но прямое применение review решений в production KB без отдельного controlled apply шага повышает риск governance drift и неаудируемых мутаций.

Decision: workflow `PRD-046.0.7` ограничивается безопасным сбором review queue и валидацией decisions overlay; решения хранятся отдельно и не применяются к `all_blocks_merged.json`/Chroma в рамках этого цикла.

Consequences: review процесс становится воспроизводимым и проверяемым (sanitized artifacts + no-mutation proof), а фактический apply переносится в отдельный PRD с preflight/dry-run safety gates.



## ADR-014 - Legacy SD classification is decommissioned from active BotDB admin/query path

Status: accepted

Context: SD-поля исторически присутствуют в данных, но их активное использование в BotDB Admin/UI/API как production-сигнала создаёт ложную модель состояния KB и мешает hygiene/reprocess readiness этапу.

Decision: для BotDB admin/query surfaces SD больше не используется как active filter/signal; в `/api/query` `sd_level` переводится в deprecated no-op с явным debug trace, а SD-визуалы удаляются из dashboard/registry UI.

Consequences: снижен риск ошибочного operational решения на SD-сигналах; совместимость клиентов сохранена через backward-compatible поле без влияния на retrieval.



## ADR-015 - Source registry cleanup must go through snapshot+archive workflow before clean reprocess

Status: accepted

Context: ручные удаления и смешанные test/stale источники в registry приводят к непрозрачному состоянию и блокируют безопасный clean reprocess.

Decision: cleanup выполняется через контролируемый `audit -> plan -> dry-run/apply` процесс с обязательной защитой focus source и запретом hard-delete источников с `blocks_count > 0`; перед mutation обязателен snapshot.

Consequences: улучшена воспроизводимость и обратимость hygiene-операций; readiness gate может детерминированно объяснять blockers/warnings перед запуском reprocess.



## ADR-016 - Clean source reprocess must be candidate-first before any production apply/reindex

Status: accepted

Context: после закрытия hygiene blocker нужно пересобрать knowledge source из raw markdown, но прямой apply в production (`all_blocks_merged`/Chroma/registry) без измеримого candidate quality увеличивает риск regression и не даёт изолировать причину деградации.

Decision: этап `PRD-046.0.8` выполняется только в `candidate` режиме: reprocess строится из single active source, формируются preflight/stats/diff/governance gate/practice-like/no-mutation артефакты, при этом production data и runtime path не мутируются.

Consequences: решение о reindex/apply переносится в отдельный PRD на основе gate-результата; при проблемах классификации запускается HF-калибровка вместо опасной production мутации.



## ADR-017 - Direct practice protocols require deterministic classification before candidate apply

Status: accepted

Context: после `PRD-046.0.8` candidate показал practice-like ambiguity (`practice_like_misclassified_count > 0`), что делало переход к controlled apply/reindex рискованным.

Decision: для candidate-governance вводится deterministic practice taxonomy (`direct_practice_protocol`, `practice_context_or_theory`, `case_or_dialogue_about_practice`, `quote_or_source_fragment_with_practice_terms`) и gate v2 с отдельными метриками `direct_practice_misclassified_count` и `unsafe_practice_suggestion_count`. Direct practice обязан иметь `chunk_type=practice`, `practice_suggestion` в `allowed_use`, а также safety bundle (`not_for_direct_quote`, `practice_requires_low_resource_check`).

Consequences: candidate apply/reindex запрещен, пока direct-practice misclassification не равен `0`; contextual/mixed-intent warnings обрабатываются отдельным HF-warning циклом без мутации production данных.



## ADR-018 - Mixed-intent candidate chunks must be resolved before production apply

Status: accepted

Context: после `PRD-046.0.8-HF1` оставались mixed-intent high/medium warnings, что сохраняло риск неочевидного governance-поведения при переходе к apply/reindex.

Decision: вводится candidate mixed-intent audit+resolution taxonomy (`split_required`, `primary_role_resolved`, `review_only`, `false_positive`) и gate v3 с полями `mixed_intent_unresolved_count`, `mixed_intent_split_required_count`, `candidate_ready_for_apply`. Production apply/reindex разрешается только при `status=passed` и `candidate_ready_for_apply=true`.

Consequences: unresolved/split-required mixed-intent кейсы блокируют apply; false-positive и review-only сценарии остаются прозрачными через candidate metadata без мутации production контуров.



## ADR-019 - Candidate apply to production requires preflight, backups, controlled reindex, and post-apply retrieval gates

Status: accepted

Context: переход candidate (`PRD-046.0.8-HF2`) в production несет высокий риск несогласованности между `all_blocks_merged`, registry и Chroma, а также риск некорректного повторного использования устаревших review artifacts.

Decision: apply разрешается только через staged workflow: `preflight -> dry-run apply plan -> mandatory backups -> controlled production mutation -> Chroma reindex/recovery -> post-apply consistency/quality/retrieval gates`.

Consequences: production KB становится аудируемым и воспроизводимым после reprocess; старые review queues помечаются stale, а дальнейший review/apply цикл должен опираться на новые block ids.



## ADR-020 - Post-reprocess enrichment and review must be regenerated against current block ids

Status: accepted

Context: после boundary-changing reprocess (`PRD-046.0.8.1`) старые enrichment/review артефакты стали семантически и технически stale, даже при частичном тематическом совпадении текста.

Decision: для post-reprocess этапа обязателен fresh baseline (`PRD-046.0.9`) с preflight, inventory, overlay validation и review queue rebaseline, привязанными к текущим block ids/hash. Старые решения не применяются без явного remap+hash proof.

Consequences: review/apply цикл остается трассируемым и безопасным; исключается silent перенос старых решений на новые границы чанков; LLM enrichment сохраняет advisory роль и не может мутировать deterministic governance authority.



## ADR-021 - BotDB Admin Dashboard must use explicit read-only summary contract

Status: accepted

Context: после `PRD-046.0.9-RUN1` registry отражал актуальные данные, но dashboard показывал пустые карточки из-за хрупкой сборки состояния из разрозненных вызовов и отсутствия явной деградации при проблемах источников данных.

Decision: dashboard переводится на единый read-only контракт `/api/dashboard/` (`botdb_dashboard_summary_v1`), который агрегирует registry/chroma/governance/enrichment/review state и возвращает явные `warnings` при частичной недоступности артефактов.

Consequences: admin UI отображает достоверное операционное состояние, не мутирует production данные и не маскирует ошибки немыми `—` карточками.



## ADR-022 - Admin UI acceptance requires runtime/browser-visible smoke, not only TestClient

Status: accepted

Context: после HF1 API unit tests были зелёными, но ручная проверка браузерного runtime всё ещё показывала устаревший/пустой dashboard UI.

Decision: для Admin UI hotfix-циклов обязательны runtime-oriented smoke checks: статический contract (HTML script version, JS fetch path), endpoint slash/no-slash compatibility и явный UI fallback на API/payload ошибки.

Consequences: acceptance не завершается только TestClient-уровнем; PRD считается закрытым после подтверждения browser-visible контракта.



## ADR-023 - Writer KB snippets must be boundary-aware and never cut Cyrillic words mid-token

Status: accepted

Context: в runtime prompt `ЗНАНИЯ ИЗ БАЗЫ` фиксировались обрезанные фрагменты (`Добро пожаловат`, `Ешь на бе`), ухудшающие качество контекста для Writer.

Decision: sanitization/truncation для writer-facing KB snippets должна резать по sentence/word boundary и добавлять ellipsis `…`, а не использовать raw fixed-char clipping.

Consequences: снижается шум и двусмысленность в writer prompt при сохранении budget limits и без мутации production block text.



## ADR-024 - Admin source registry must be row-isolated and never fail silently

Status: accepted

Context: при runtime-проверке после HF2 registry page могла открываться с пустой таблицей, хотя источники в системе были; один проблемный row/policy path потенциально ронял весь payload, а frontend не показывал явный error state.

Decision: endpoint `/api/registry/` обязан обрабатывать ошибки на уровне строки (row-level isolation), возвращать частичный список с `delete_policy.state=unavailable` и причинами, а frontend обязан иметь явные loading/error/empty states вместо silent empty table.

Consequences: отказ одной строки больше не блокирует весь admin registry, а browser-visible диагностика делает runtime проблемы воспроизводимыми и проверяемыми до перехода к human-review циклам.



## ADR-025 - Admin/API runtime gate cannot pass when required endpoints are unreachable

Status: accepted

Context: после controlled apply data-level проверки могли быть зелёными даже при `connection refused` на admin endpoints, что создавало ложный signal готовности перед следующим архитектурным этапом.

Decision: post-apply quality gate обязан разделять data consistency и admin runtime consistency; при недоступности `/api/status`, `/api/registry`, `/api/dashboard`, `/api/dashboard/` статус должен быть `blocked_admin_api_unavailable` (или `skipped_offline_explicit` при явном offline-режиме), но не `passed`.

Consequences: readiness к Diagnostic Center не может стать `true` без подтверждённой доступности admin/API runtime, а отчёты корректно отражают blocker вместо ложного green.



## ADR-026 - Live admin runtime smoke uses dual launch mode with readiness polling

Status: accepted

Context: для post-apply readiness gate требуется проверять реальный runtime admin endpoints; при этом сервер может быть уже запущен пользователем или должен подниматься временно агентом.

Decision: HF1 live smoke использует dual strategy: `external_existing` (не запускать второй сервер на том же порту) и `hf1_subprocess` (detected canonical launch command + startup polling + controlled shutdown). Если readiness не достигнут или запуск невозможен, статус обязан оставаться blocker (`blocked_admin_launch_failed`), без ложного green.

Consequences: gate становится воспроизводимым и трассируемым (manifest + sanitized logs + explicit blocker reason) без мутации production данных.



## ADR-027 - Admin gate may accept dashboard Chroma mismatch only with explicit local proof

Status: superseded_by_adr_028

Context: в HF2 live runtime dashboard мог возвращать `chroma.count`, отличающийся от ожидаемого production count, хотя отдельная локальная Chroma diagnostics-проверка подтверждала корректный `247` для focus source.

Decision: quality gate не блокируется только при наличии явного локального proof-артефакта с ожидаемым count; mismatch без proof остаётся schema blocker. Принятие mismatch всегда фиксируется предупреждением в artifacts/reports.

Consequences: сохраняется строгий gate по умолчанию, но исключается ложный blocker при совместимом runtime contract drift и подтвержденной локальной диагностике.



## ADR-028 - Historical Chroma proof cannot override live dashboard mismatch in strict gate

Status: accepted

Context: HF3 показал, что `dashboard.chroma.count=229` при `blocks=247` может быть замаскирован historical proof (`247`) и дать ложный green readiness signal.

Decision: для post-apply readiness gate действует strict live contract: historical/local proof используется только как диагностическое evidence и никогда не может перевести `dashboard_chroma_count_mismatch` в `passed`. При live mismatch статус обязан быть `blocked_chroma_count_mismatch` с итогом `done_with_chroma_count_blocker`.

Consequences: readiness к Diagnostic Center остаётся честно заблокированной до reconciliation/recovery шага; устраняется риск ложноположительного gate-pass из-за stale артефактов.



## ADR-029 - Dashboard Chroma total must use collection.count() as authoritative source

Status: accepted

Context: в HF4 после controlled reindex direct Chroma diagnostic уже показывал `247`, но dashboard временно отображал `0` из-за вычисления total через `collection.get()` выборку, что давало runtime drift.

Decision: для admin/dashboard runtime total Chroma count берётся из `collection.count()`; выборка `get(..., include=['metadatas'])` используется только для распределений/составов и не как источник total.

Consequences: dashboard Chroma total синхронизирован с direct diagnostic и strict gate, уменьшается риск ложного blocker/passed статуса из-за особенностей выборки API.



## ADR-030 - Diagnostic Center is a map-making layer, not a user-facing agent

Status: accepted

Context: проект перешёл к Diagnostic Center после readiness-gates, но есть риск превратить новый слой в отдельного user-facing LLM-агента, который начнёт писать пользователю, подменять Writer и принимать authority-решения по KB/governance.

Decision: Diagnostic Center v1 закреплён как internal map-making layer. Он собирает `DiagnosticCenterOutput` из существующих сигналов (State Analyzer / Thread Manager / Context Assembly / governed retrieval metadata) и формирует `working_hypothesis + next_micro_shift`. Diagnostic Center не генерирует финальный пользовательский текст, не цитирует KB напрямую, не меняет governance authority и не включается в active runtime без отдельного PRD.

Consequences: диагностическая логика становится тестируемой независимо от Writer, runtime сохраняет multiagent-дисциплину, а следующий шаг (`PRD-046.1.1`) может подключать слой только в shadow-mode с отдельными eval/gate проверками.



## ADR-031 - Diagnostic Center shadow mode cannot affect user-facing output

Status: accepted

Context: в `PRD-046.1.1` Diagnostic Center впервые подключается к runtime. Без жёстких ограничений shadow path мог бы незаметно повлиять на WriterContract, writer prompt или final answer.

Decision: Diagnostic Center в runtime допускается только в trace-only shadow режиме. Shadow output строится на реальных runtime сигналах, но не передаётся в WriterContract, не меняет writer prompt, не меняет validation path и не влияет на final answer. При ошибке shadow runtime продолжает основной ответ без блокировки.

Consequences: система получает измеримые divergence-метрики для следующего PRD, сохраняя инварианты user-path безопасности (`writer_contract_changed=false`, `writer_prompt_changed_by_shadow=false`, `final_answer_changed_by_shadow=false`).



## ADR-032 - Planner Bridge remains shadow-only until explicit compliance integration PRD

Status: accepted

Context: после trace-only Diagnostic Center shadow появился рабочий путь нормализации сигналов в candidate planning constraints, но прямое подключение к Writer Move Compliance без divergence-калибровки и отдельного integration PRD увеличивает риск user-path regressions.

Decision: Planner Bridge v1 реализуется только как shadow/eval contract слой. Он может формировать candidate constraints и trace, но `apply_to_writer=false`, `apply_to_writer_contract=false`, `activation_mode=shadow_only` до отдельного PRD-046.1.3.

Consequences: архитектура получает готовый мост для следующего шага интеграции, сохраняя no-user-path-effect и предотвращая преждевременное влияние Diagnostic Center/Planner Bridge на final answer.



## ADR-033 - Planner Bridge can compare with Writer Move Compliance only in shadow_compare mode

Status: accepted

Context: после PRD-046.1.2/046.1.2-HF1 проекту нужно сравнить candidate constraints Planner Bridge с текущими Writer Move Compliance rules, но без риска скрытого влияния на WriterContract/prompt/final answer.

Decision: вводится только shadow compare integration: Planner Bridge candidate + compliance comparison пишутся в runtime trace как `planner_bridge_compliance_shadow`, при этом `apply_to_writer=false`, `apply_to_writer_contract=false`, writer prompt и final answer path остаются неизменными.

Consequences: система получает измеримый compatibility слой (compatible/tightens/expected_divergence/needs_review/blocked) и готовность к следующему controlled pilot PRD, не нарушая user-path safety gates.



## ADR-034 - Writer-Contract Pilot remains non-mutating until offline replay PRD

Status: accepted

Context: после PRD-046.1.3 появилась готовность строить candidate constraints для WriterContract, но прямое применение overlay к production Writer path в этом цикле создаёт риск незаметных regressions в prompt/final answer.

Decision: в PRD-046.1.4 вводится только controlled pilot overlay (`pilot_shadow_only`) с фиксированными guardrails: `apply_to_writer_contract=false`, `apply_to_writer_prompt=false`, `apply_to_final_answer=false`. Pilot обязан доказывать immutability через deterministic hash (`before/after`) и сохранять runtime trace/eval artifacts без provider calls.

Consequences: Diagnostic Center/Planner Bridge получают измеримый контрактный мост к Writer без production activation; следующий шаг допускается только как offline replay/eval PRD (PRD-046.1.5), а не прямое влияние на пользовательский ответ.



## ADR-035 - Writer Prompt Replay remains offline-only before any prompt activation

Status: accepted

Context: после PRD-046.1.4 появилась возможность оценивать candidate constraints на уровне prompt-context, но любое прямое подключение replay-кандидата в production Writer path преждевременно и рискованно без отдельного controlled rollout.

Decision: в PRD-046.1.5 replay слой ограничен `offline_replay_only`: baseline и candidate prompt-context сравниваются детерминированно (safety/KB/conflict/prompt-bloat/non-mutation), но replay не имеет права менять production WriterContract, writer prompt или final answer и не вызывает provider.

Consequences: проект получает измеримый quality-eval фундамент для следующего ограниченного runtime-эксперимента (PRD-046.1.6) с жёсткими rollback/safety gates вместо немедленной активации для всех пользователей.



## ADR-036 - Prompt Constraint Pilot can affect Writer prompt only under default-off allowlisted runtime flag

Status: accepted

Context: после offline replay (PRD-046.1.5) нужен ограниченный runtime-эксперимент для проверки prompt constraints, но broad activation в production создаёт риск user-path regressions.

Decision: в PRD-046.1.6 pilot constraints могут влиять на Writer prompt только при explicit runtime-флагах (`PROMPT_CONSTRAINT_PILOT_ENABLED=true`, `PROMPT_CONSTRAINT_PILOT_MODE=test_apply`), только для allowlisted/test users и только после passed gates (rollback/safety/KB/conflict/prompt-bloat/non-mutation). По умолчанию путь остаётся disabled/shadow; `PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED=true` имеет абсолютный rollback-приоритет.

Consequences: production default path остаётся неизменным, runtime-эксперимент трассируется артефактами и может быть мгновенно отключён rollback-флагом; broad rollout запрещён до отдельного PRD-046.1.7+.



## ADR-037 - Diagnostic Center v1 accepted as governed shadow layer; runtime authority expansion requires separate PRD

Status: accepted

Context: после PRD-046.1.15 Diagnostic Center v1 и связанный Planner/Prompt-Constraint стек стабилизированы, но остаются риски преждевременного расширения authority в production user-path.

Decision: PRD-046.1.16 закрепляет Diagnostic Center v1 как внутренний governed shadow/runtime-governance слой с постоянными regression blockers. Broad rollout, изменение Writer prompt/contract/final answer path и расширение runtime authority запрещены без отдельного future PRD с новым controlled rollout, rollback plan и normal-user no-effect доказательствами.

Consequences: проект получает формально закрытый runtime governance boundary (`trace_only_shadow`, `default_off_limited_allowlisted_test_path`) и стабильную опору для следующего шага качества ответов (PRD-046.1.17) без ослабления safety/KB/privacy/no-mutation инвариантов.



## ADR-038 - Response quality eval must pass before any Diagnostic Center runtime authority expansion

Status: accepted

Context: после PRD-046.1.16 проект подтвердил governance/safety/no-mutation boundaries, но это не отвечает на вопрос качества пользовательского ответа в живой траектории.

Decision: перед любым расширением влияния Diagnostic Center/Planner/Prompt-Constraint на Writer/final-answer path обязателен воспроизводимый offline response-quality eval pack (curated live-like scenarios + rubric + weak/hard-fail detection + KB/internal lens boundary checks).

Consequences: обсуждение runtime authority expansion переносится только после успешного quality evidence слоя; приоритетом становятся continuity/depth-fit/micro-shift/non-bookishness и сохранение KB boundaries без broad rollout.



## ADR-039 - Controlled runtime pilot requires readiness plan and rollback-first governance



- Date: 2026-05-18

- Status: accepted

- Context: ????? PRD-046.1.16/046.1.17/046.1.18 ??????? ?????? ? ????????????? pilot only ??? ??????? governance, ?? ?????? runtime execution ??? ???????????????? readiness-planning ???????? ???? ????????? normal-user path, KB boundary violations ? ??????????????? rollback.

- Decision: ????? controlled runtime pilot ??? Diagnostic Center / Prompt-Constraint path ?????? ?????????? ? ?????????? plan-only readiness PRD, ??????? ?????????: cohort policy, toggle matrix, runtime preflight requirements, limited live smoke plan, rollback-first runbook, hard-stop criteria, monitoring artifact contract, normal-user guard, KB governance guard ? trace sanitization guard. Execution ??????????? ?????? ? ????????? ????????? PRD ????? ??????????? readiness gate.

- Consequences: Broad rollout ???????? ???????????; normal-user apply ???????? ??????????? ?? ?????????; rollback ???????? ?????????? ??????????? ????? FORCE_DISABLED; ?????????? readiness artifacts ????????? blocker ??? execution PRD.



## ADR-040 - Every controlled runtime execution must be followed by a no-new-execution results gate



- Date: 2026-05-18

- Status: accepted

- Context: after a single controlled execution window, direct cohort expansion without consolidated evidence review can hide rollback drift, normal-user side effects, trace hygiene regressions, or safety/KB boundary violations.

- Decision: each controlled runtime execution PRD must be followed by a dedicated no-new-execution results gate PRD that deterministically audits source evidence (execution scope, rollback, normal-user no-effect, quality delta, safety/KB, trace sanitization, no-mutation, encoding hygiene) and produces a decision gate: `continue_limited_candidate | fix_required | stop_pilot`.

- Consequences: rollout progression becomes evidence-first and reversible, broad rollout remains prohibited by default, and any further runtime execution requires an explicit next PRD with preserved rollback-first governance.



## ADR-041 - BotDB recovery closure requires live query proof before Diagnostic Center continuation



Status: accepted

Context: HF1 restored Chroma counts but left `/api/query` and bot retrieval path ambiguous due live runtime drift.

Decision: Diagnostic Center continuation is blocked until live proof confirms `dashboard=ok/247`, `registry_stats=200/247`, `/api/query=200` with hits, and bot retrieval path uses API without semantic fallback/circuit-open state.

Consequences: runtime truth is anchored in live artifacts; continuation PRDs cannot rely on historical/local-only Chroma evidence.



## ADR-042 - Registry cleanup uses focus-only gate with Chroma absence proof

Status: accepted
Context: post-recovery runtime may keep stale non-focus registry rows, while direct Chroma source checks can fail with runtime binding errors.
Decision: non-focus deletion is allowed only when independent proof confirms absence from all_blocks and Chroma; focus source is always protected; delete API must not leak raw Chroma tracebacks.
Consequences: operator-facing registry can be safely reduced to focus-only state without risking production source loss or governance mutation.

## ADR-043 - Provider-backed continuation requires readiness-only gate before new execution

Status: accepted
Context: after PRD-046.1.21-HF3 recovery closure, Diagnostic Center can continue, but immediate provider-backed execution would couple live dependencies and runtime risk without refreshed rollout policy evidence.
Decision: PRD-046.1.22 is locked to readiness-only scope: validate source gates, validate live BotDB health (`dashboard=247/ok`, `registry=1`, `query=200`, no semantic fallback), and publish strict contracts (single synthetic allowlisted operator, normal-user controls, rollback-first, hard-stop criteria, KB boundary, trace sanitization) without provider execution.
Consequences: provider-backed execution remains prohibited in PRD-046.1.22 and can start only in a separate PRD-046.1.23 with explicit execution evidence, rollback proof, and hard-stop enforcement.

## ADR-044 - Provider-backed limited smoke execution is constrained to one allowlisted operator with rollback-first and no normal-user effect

Status: accepted
Context: readiness PRD-046.1.22 confirmed live dependencies and policy boundaries, but first real provider-backed execution required strict containment to prevent accidental rollout and user-path regressions.
Decision: PRD-046.1.23 execution is constrained to one synthetic allowlisted operator (`pilot_runtime_operator_001`), five fixed scenarios, provider budget `<=5`, mandatory normal-user controls (`>=2`) with zero apply effect, rollback-first toggles, hard-stop safety/KB/trace gates, and sanitized-only artifacts (no raw provider payload or secrets).
Consequences: provider-backed runtime path can be validated with real calls while preserving production governance boundaries; broad rollout and production-ready decisions remain explicitly blocked until a dedicated results/quality/rollback gate (PRD-046.1.24).

## ADR-045 - Every provider-backed execution must be followed by a no-new-execution results gate before cohort expansion

Status: accepted
Context: PRD-046.1.23 executed the first provider-backed limited smoke, but expanding cohort/execution immediately would risk hiding regressions in rollback, normal-user no-effect, safety/KB boundaries, trace/provider sanitization, and BotDB stability.
Decision: PRD-046.1.24 is mandatory as a deterministic post-run results gate that consumes prior artifacts only (no new provider calls, no new runtime execution, no production mutation) and emits one of `continue_limited_candidate | fix_required | stop_provider_backed_pilot`.
Consequences: rollout progression stays evidence-first and reversible; broad rollout remains prohibited and production-ready remains false until a separate future PRD passes after this gate.

## ADR-046 - Controlled cohort expansion requires cumulative provider-backed consolidation gate pass

Status: accepted
Context: после двух provider-backed limited smoke циклов (`PRD-046.1.23`, `PRD-046.1.25`) и одного post-run results gate (`PRD-046.1.24`) требовалось архитектурно зафиксировать консолидационный decision gate до расширения когорты.
Decision: перед любым controlled cohort expansion обязателен cumulative consolidation PRD (`PRD-046.1.26`) без новых provider calls/execution/mutation, который детерминированно подтверждает source chain completeness, provider evidence continuity, normal-user no-effect, rollback-first, safety/KB boundary, trace/provider sanitization, BotDB stability, no-mutation и artifact hygiene. Только при `final_status=passed` и `decision=ready_for_controlled_cohort_expansion_prd` допускается следующий PRD расширения когорты.
Consequences: расширение провайдерного пилота остаётся evidence-first и обратимым; broad rollout/production-ready/normal-user activation остаются запрещёнными до будущих отдельных gate PRD.

## ADR-047 - Controlled cohort expansion execution remains bounded and non-authoritative

Status: accepted
Context: после `PRD-046.1.26` было разрешено перейти от single-operator limited smoke к расширенной allowlisted synthetic cohort execution, но существовал риск скрытого перехода к normal-user activation или неявного расширения runtime authority.
Decision: `PRD-046.1.27` закрепляет execution boundary: только allowlisted synthetic cohort из трёх операторов, provider budget `<=12`, обязательные normal-user controls без apply/provider effects, rollback-first/hard-stop/safety-KB/trace/no-mutation gates и запрет broad rollout/production-ready/normal-user activation.
Consequences: даже при зелёном execution результате (`ready_for_final_acceptance_and_stabilization_prd`) Diagnostic Center остаётся governed limited layer; расширение authority возможно только через следующий отдельный acceptance/stabilization gate PRD.

## ADR-048 - Provider-backed Diagnostic Center phase accepted as governed limited-runtime candidate

Status: accepted
Context: после двух single-operator provider-backed cycles, cumulative consolidation и controlled cohort expansion (`PRD-046.1.23..PRD-046.1.27`) требовалась финальная архитектурная приёмка без нового execution/call budget роста.
Decision: `PRD-046.1.28` фиксирует phase acceptance как `accepted_as_governed_limited_runtime_candidate` при обязательных permanent regression gates (normal-user no-effect, rollback-first, safety/KB boundary, trace/provider sanitization, no-mutation, encoding hygiene, BotDB stability, quality/micro-shift) и при жёстких boundary-флагах: `broad_rollout=false`, `production_ready=false`, `normal_user_activation=false`.
Consequences: provider-backed phase завершена на governance уровне, но broad rollout и production launch запрещены; следующий обязательный шаг — `PRD-046.1.29` stabilization/cleanup/eval-harness consolidation перед любым дальнейшим расширением.
## ADR-049 - Diagnostic Center Stabilization / Cleanup Boundary

Status: accepted
Context: provider-backed Diagnostic Center phase was accepted in `PRD-046.1.28`, but runtime/eval/docs artifacts remained mixed between active operations and historical evidence.
Decision: `PRD-046.1.29` establishes a manifest-first, reproducibility-preserving cleanup boundary: separate production runtime, permanent quality gates, and historical evidence; disallow physical deletion of runtime/eval-critical files in this PRD; require explicit follow-up PRD for any destructive cleanup.
Consequences: project navigation is compact and maintainable, permanent gates remain intact, and broad rollout continues to require a separate governance PRD.
Implementation proof: `PRD-046.1.29` merged in commit `70635e1` on `origin/main`.
## ADR-049 - Controlled Rollout Planning Boundary

Status: accepted
Context: Diagnostic Center accepted as governed limited-runtime candidate, but rollout execution remains sensitive to rollback, safety/KB, trace sanitization, and normal-user isolation risks.
Decision: controlled rollout execution requires a separate explicit PRD with allowlist-only cohort, rollback-first policy, hard-stop enforcement, permanent gate reuse, and strict normal-user no-effect proof.
Consequences: planning and execution are separated; broad rollout and production-ready declaration remain blocked in planning-only phase.
## ADR-050 - Controlled Rollout Execution Boundary

Status: accepted
Context: PRD-046.1.30 prepared plan-only rollout boundaries; PRD-046.1.31 executes the first controlled rollout window.
Decision: execution remains allowlist-only and rollback-first with strict hard-stop, provider budget cap, normal-user no-effect, BotDB stability, safety/KB boundary, trace sanitization, and no-mutation/hygiene gates.
Consequences: broad rollout, normal-user activation, and production-ready declaration remain prohibited; post-execution decisions must be taken by a separate consolidation/results PRD.

## ADR-051 - Controlled Rollout Results Gate Boundary

Status: accepted
Context: after `PRD-046.1.31` execution passed, a separate consolidation stage was required to verify rollback/safety/normal-user/no-mutation continuity and fix docs sync drift before any activation-readiness decision.
Decision: `PRD-046.1.32` is mandatory as a no-new-execution/no-provider-call results gate that consumes source evidence only, validates provider budget and safety boundaries, enforces normal-user no-effect and no-mutation proofs, and blocks progression when docs consistency remains stale.
Consequences: rollout governance stays evidence-first and reversible; broad rollout and normal-user activation remain prohibited; next step may only be readiness decision PRD (`PRD-046.1.33`) when this gate is fully green.

## ADR-052 - Limited runtime activation requires readiness/boundary gate before allowlisted live execution

Status: accepted
Context: after `PRD-046.1.32`, the project had green controlled-rollout results evidence, but broad rollout / normal-user activation / production-ready authority expansion remained prohibited and required an additional boundary decision before any live allowlisted execution.
Decision: before any allowlisted limited live activation, a dedicated readiness/boundary decision gate is mandatory (`PRD-046.1.33`) to confirm source evidence integrity, strict live dependencies, normal-user no-effect, rollback-first and hard-stop completeness, safety/KB boundary, trace/provider sanitization, no-mutation proof, artifact hygiene, and docs sync. The readiness PRD itself does not perform runtime execution or provider-backed activation.
Consequences: the next step can only be a separate constrained execution PRD (`PRD-046.1.34`) with allowlist, budget, rollback-first, and post-run results gating; broad rollout and production-ready declaration remain blocked pending future dedicated governance gates.
## ADR-053 - Creator-only live activation precedes external allowlist expansion

Status: accepted
Context: after `PRD-046.1.33`, limited runtime readiness was passed, but project state still has no external real users; broad rollout and normal-user activation remain prohibited.
Decision: first live activation step is constrained to `creator_only` runtime mode with explicit creator identity boundary, admin kill switch priority, strict normal-user no-effect controls, sanitized trace monitor, provider budget cap, and rollback/hard-stop governance. External allowlist expansion is deferred to later PRDs.
Consequences: this step is not broad rollout and not production-ready declaration; `broad_rollout_allowed=false`, `production_ready=false`, and `normal_user_activation_allowed=false` remain invariant.
