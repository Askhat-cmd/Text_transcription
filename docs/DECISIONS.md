# Architecture Decisions

## ADR-072 - Explicit summary requests own route and obligation without canned answers

Status: accepted

Date: 2026-06-08

Context: PRD-047.14 and HF1.2 left a focused risk where explicit recap/summary requests could be mistaken for confirmation of the previous assistant offer or handled by static Writer summary text.

Decision:
- explicit current-conversation summary requests resolve to `dialogue_act=summary_request` before last-offer confirmation;
- the answer obligation is `summarize_current_conversation`;
- `final_answer_directive_v1` exposes summary metadata to Writer while preserving Writer authorship;
- Writer must not create a canned summary replacement;
- `final_answer_acceptance_gate_v1` blocks reconfirmation/last-offer misanswers and recommends retry/quarantine without producing replacement text;
- no new LLM agent, runtime path, KB/governance authority, frontend path, or rollout activation is introduced.

Consequences: summary turns can be tracked and retried honestly without contaminating last-offer state or healthy context memory.

## ADR-071 - PRD-047.13-HF1 closes active cleanup noise without runtime mutation

Status: accepted

Date: 2026-06-08

Context: PRD-047.13 produced a cleanup inventory and proved runtime non-mutation, but active documentation still contained stale next-PRD references, living-doc metadata gaps, and potentially misleading profile/admin labels. Historical empty artifacts and encoding warnings also needed explicit closure classification.

Decision:
- PRD-047.13-HF1 may change docs, cleanup reports, manifests, placeholder explanations, and Web Admin help labels only;
- `safe_guided`, `mvp_free_dialogue`, and `free_dialogue_default` are documented as presets/aliases of `unified_dialogue_policy_v2`, not separate systems;
- historical artifacts remain preserved or manifest-classified; active empty/noisy artifacts must be closed;
- Writer, Orchestrator, Dialogue Act Resolver, Final Answer Acceptance Gate, RAG/Chroma, prompt behavior, Diagnostic Center authority, production flags, and runtime paths remain unchanged.

Consequences: PRD-047.13-HF1 is the final cleanup closure before `PRD-047.14 - Live Dialogue Quality Polish / Human Reference Calibration v1`.

## ADR-070 - PRD-047.13 cleanup boundary preserves runtime baseline

Status: accepted

Date: 2026-06-05

Context: after PRD-047.12-HF1, the unified dialogue runtime has an accepted engineering baseline, but the repository still contains historical PRDs, logs, reports, admin labels, and docs that can be confused with active runtime instructions.

Decision:
- PRD-047.13 is limited to inventory, classification, docs truth sync, admin surface inventory, and manifest-backed cleanup reporting;
- Writer, Orchestrator, Final Answer Acceptance Gate, Stale Stub Detector, Dialogue Act Resolver, RAG/Chroma, prompt behavior, and Diagnostic Center authority remain out of scope;
- archive/delete actions require explicit manifests;
- `production_ready=false`, `broad_rollout_allowed=false`, and `normal_user_activation_allowed=false` remain invariant.

Consequences: cleanup evidence lives under `TO_DO_LIST/logs/PRD-047.13/`; live dialogue quality work moves to PRD-047.14.

## ADR-068 - Writer-first prompt assembly for MVP profile

Status: accepted

Date: 2026-06-01

Context: PRD-047.10/HF cycles left residual conflicts where legacy prompt blocks (`writer_move`, `diagnostic_card`, `active_line`, `response_planner`) still appeared as imperative commands and repeatedly produced stale regulate-style stub answers in live dialogue.

Decision:
- add deterministic `final_answer_directive_v1` as single conflict-resolved command block for Writer in `mvp_free_dialogue`;
- keep Diagnostic Center / Planner / Active Line / Diagnostic Card as advisory context providers for MVP profile;
- keep minimal safety/privacy/no-diagnosis boundaries as hard limits;
- expose writer-first assembly and role fields in admin runtime effective payload + live evidence export;
- add strict stale-stub detector for regression checks across answer payloads and artifacts.

Consequences:
- no new LLM agent and no new runtime path were added;
- governance authority fields and Chroma index were not mutated;
- live acceptance remains explicitly blocked until runtime profile activation and real web markdown smoke pass are green.

## ADR-069 - HF3 repairs concrete formula-stub answers at answer level, not by adding new runtime authority

Status: accepted

Date: 2026-06-04

Context: after HF2, real owner feedback still showed a residual class where concrete user situations could receive a generic formula opening like `Сейчас полезнее не упражнение...`, and bare gratitude turns could still surface misleading deterministic `hypo/explore` signals in trace.

Decision:
- add a lightweight concrete-answer-fit heuristic (`concrete_answer_fit_v1`) and contextual no-practice rewrite only for concrete formula-stub failures;
- keep Writer freedom intact in MVP profile and do not add a new guard, mode, runtime path, or LLM agent;
- repair deterministic gratitude/close handling so simple `Спасибо.` maps to `intent=contact` and `nervous_state=window`;
- revalidate browser/admin proof on real `localhost:3000` and capture explicit reset/memory/admin inventory artifacts;
- treat docs/encoding hygiene as part of the runtime truthfulness boundary for this cycle.

Consequences:
- the fix remains observability-friendly and local to answer-level/runtime evidence without broadening authority;
- concrete situation answers are less likely to pass through stale generic mechanism stubs;
- localhost UX and docs truthfulness are now part of the same stabilization evidence pack before `PRD-047.12`.
## ADR-065 - Planner Drift Guard is observe-only runtime quality monitor

Status: accepted

Context: после PRD-047.5-HF1 оставался эксплуатационный риск runtime drift (model/provider/prompt/runtime variability) даже при зелёных калибровочных прогонах.

Decision: введён детерминированный `planner_drift_guard_v1` как observability-first слой:
- сверяет `response_planner` и `final_answer` на каждом ходе;
- пишет `status/severity/flags` в trace/debug;
- ведёт rolling summary counters (in-memory, max window=100);
- публикует read-only runtime block в admin effective;
- используется для dry/direct/live replay regression артефактов.

Consequences:
- drift guard не блокирует и не переписывает пользовательский ответ;
- drift guard не является новым LLM-агентом;
- governance authority (`chunk_type`, `allowed_use`, `safety_flags`) не меняется;
- runtime quality drift становится наблюдаемым без broad rollout / production activation.
## ADR-066 - Guided Live Feedback Protocol is evidence loop, not runtime mutation

Status: accepted

Context: после runtime observability (PRD-047.6) отсутствовал структурированный процесс живого пользовательского тестирования и связки human feedback с trace/debug.

Decision: введён guided live testing protocol v1 с санитизированным feedback capture/storage и summary workflow:
- feedback хранится как file-based sanitized artifacts;
- feedback связывается с compact trace summary (`active_line`, `response_planner`, `planner_drift_guard`, `writer`);
- runtime/admin/web отображают read-only guided live testing status;
- feedback не изменяет runtime поведение автоматически.

Consequences:
- feedback становится first-class evidence для следующих PRD;
- Writer hard constraints не усиливаются в feedback layer;
- `final_answer` не переписывается и не блокируется;
- новый LLM-агент не добавляется, governance authority не мутируется.

## ADR-066 Amendment - Dialogue profiles are presets over one unified adaptive policy surface

Status: accepted

Date: 2026-05-29

## PRD-047.12-HF1 Final Answer Acceptance Gate

Decision: add `final_answer_acceptance_gate_v1` after Writer and Validator, before unanswered-question closure, last-offer seeding, and healthy context memory write.

Rationale: PRD-047.12 unified the architecture, but live evidence showed false positives where stale/generic answers could be accepted as answered. The fix is a truth gate and quarantine layer in the same runtime path, not a new mode, LLM agent, or static answer factory.

Consequences: failed final answers can trigger one Writer retry with gate feedback. If still failed, the answer is quarantined from healthy state while trace/debug exposes status and failed checks. Diagnostic Center, Planner, and Active Line remain advisory-only.

Context: `mvp_free_dialogue` introduced higher Writer freedom, but residual conflicts remained when old planner/diagnostic constraints and context truncation still dominated prompt behavior.

Decision:
- keep single multiagent runtime path (no duplicated orchestrator/writer/planner);
- treat `safe_guided` and `mvp_free_dialogue` as presets of one `dialogue_policy` authority resolver;
- enforce authority order: minimal safety > explicit user request > knowledge/concept need > writer freedom > planner/diagnostic advisory;
- preserve Writer context by recency with profile-specific budgets, instead of fixed `[:2000]` prefix slicing;
- keep planner drift guard observe-only (no blocking/rewrite of final answer).

Consequences:
- mode switching becomes parameterized behavior, not architecture branching;
- explanation/overview/practice requests can expand in MVP profile without removing minimal safety baseline;
- runtime/admin/trace can expose one coherent effective policy contract.

## ADR-067 - MVP human-like writer autonomy uses policy-level constraint resolution, not new guard/runtime branch

Status: accepted

Date: 2026-06-01

Context: after PRD-047.9 architectural unification, live owner feedback still showed formal/over-constrained answers in `mvp_free_dialogue` for direct concrete requests, dissatisfaction repair, and summary requests.

Decision:
- add `human_like_answer_policy` and `constraint_resolution` to unified effective `dialogue_policy`;
- keep authority order within single runtime path (`minimal safety > explicit user request > live dialogue pragmatics > knowledge/concept need > writer autonomy > planner advisory`);
- treat legacy restrictive constraints as advisory-overridable metadata in MVP profile;
- expose human-like/constraint-resolution metadata in admin effective and trace payloads.

Consequences:
- no new LLM agent and no new runtime path were introduced;
- no blocking evaluator or final-answer auto-rewrite layer was added;
- writer keeps freedom in MVP while minimal safety baseline remains intact;
- observability of constraint overrule reasons is explicit and auditable.

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
## ADR-054 - Creator live continuation requires explicit evidence-strength gate

Status: accepted
Context: PRD-046.1.34 passed safety/runtime boundaries, but web chat smoke evidence can be probe-level or simulated without strong sanitized live-turn proof.
Decision: PRD-046.1.35 introduces a dedicated evidence-strength audit that classifies artifacts into `actual_live_turn_evidence`, `runtime_probe_evidence`, `simulated_gate_evidence`, and `missing_evidence`; continuation beyond creator-only stage is blocked when actual live-turn evidence is absent.
Consequences: safety-green is necessary but insufficient; rollout remains constrained until evidence quality is explicit and reproducible.

## ADR-055 - Creator live evidence requires end-to-end RAG delivery trace

Status: accepted
Context: PRD-046.1.35 ended with evidence_incomplete; we needed a strict chain proof from BotDB query to writer prompt and debug trace.
Decision: introduce HF1 scorecard + creator_live_turn_proof + rag_to_writer_delivery_proof with delivery classification and explicit governance-blocked state.
Consequences: creator-only runtime remains bounded; broad rollout and normal-user activation stay disabled until later PRDs.

## ADR-056 - Live RAG evidence must align adaptive trace, multiagent trace, and writer prompt

Status: accepted
Context: HF2 showed in-process retrieval success while strict live artifacts still reported zero delivery.
Decision: HF3 evaluates two live queries, aligns adaptive+multiagent traces, and stores explicit writer KB truncation audit as a non-blocking quality backlog.
Consequences: rollout remains bounded to creator-only path; broad rollout and normal-user activation stay disabled.

## PRD-046.1.35-HF4
Current Stage:
PRD-046.1.35-HF4 calibrated creator-live response behavior: example/explanation requests no longer trigger regulate_first by default, practice rejection suppresses body-action suggestions, and Web Trace displays non-empty safe Writer chunk previews.
Next:
PRD-046.1.36 Creator Live Pilot Acceptance / Minimal Admin Runtime Controls v1.

## HF4 Delivery Metadata
- prd_id: PRD-046.1.35-HF4
- commit_hash: 3a3c6a32a0c29551440432c0a266ab7cbab25b20
- push_status: pushed_to_origin_main

## ADR-055 - Diagnostic Center creator-live pilot acceptance boundary is completion-ready without broad rollout

Status: accepted
Context: HF4 passed behavior calibration and creator pipeline evidence, while broad rollout and production-ready declaration remain disallowed.
Decision: PRD-046.1.36 accepts Diagnostic Center as a governed creator-live pilot layer with runtime controls, rollback hard-stop, and strict normal-user no-effect boundary.
Consequences: next step is final completion decision gate (`PRD-046.1.37`), not broad rollout.

## ADR-057 - Diagnostic Center v1 completion gate closes current creator-pilot phase without rollout expansion

Status: accepted
Context: PRD-046.1.36 accepted creator-live pilot layer but left runtime readiness warning and mixed evidence provenance strengths.
Decision: PRD-046.1.37 enforces final source/provenance/runtime/live/admin/rollback/normal-user/safety/no-mutation decision package and closes Diagnostic Center v1 for the current phase.
Consequences: creator-only/allowlist pilot remains governed; broad rollout stays prohibited; production_ready remains false; next work moves to Multiagent Quality & Tuning Track.

## ADR-058 - Diagnostic Center admin controls are available for single-developer local governance without production rollout declaration

Status: accepted
Context: after PRD-046.1.37-HF1 completion, operational docs and admin control surface needed explicit synchronization to avoid ambiguity between local developer controls and production rollout policy.
Decision: PRD-046.1.38 introduces a dedicated Diagnostic Center admin contract (`effective/control/reset`) and Web Admin tab with full mode visibility, including `developer_local_all_users`, while preserving strict boundary flags (`production_ready=false`, `broad_rollout_allowed=false`, `normal_user_activation_allowed=false`, `external_users_allowed=false`).
Consequences: single-developer local operations can exercise full runtime control map with auditable state, but production authority expansion remains blocked until a separate future governance PRD.

## ADR-059 - Known internal concepts must be answered from governed KB grounding before asking the user to define the term

Status: accepted
Context: live multiagent failures showed that Writer could ask clarifying questions about already-known internal concepts (for example, `нейросталкинг`) even when retrieval/context already contained grounding.
Decision: introduce deterministic Knowledge Answer Routing Guard before Writer contract. If user asks/challenges a known internal concept and KB grounding is available (including lexical near-exact fallback), runtime sets `knowledge_answer_first`, disables definition-first behavior, and blocks practice-first diversion for that turn.
Consequences: concept questions are answered from internal governed meaning first, trace explicitly records `knowledge_answer` and `practice_gate`, and future tuning can iterate on measurable failure-case baseline instead of subjective chat impressions.

## ADR-059 Amendment - Acceptance requires final-answer compliance, not only guard flags

Status: accepted
Context: PRD-047.0 showed a false-positive gap where internal guard flags were correct but final user-facing answers still violated known-concept and no-practice expectations.
Decision: quality acceptance for known-concept routing is valid only when evaluator checks final answer text (forbidden fragments, clarification-question bans, required semantics, practice gate behavior, and required grounding), not trace flags alone.
Consequences: failure baseline now rejects mismatched final answers even when internal trace appears green; next tuning PRDs can rely on stricter and reproducible acceptance evidence.

## ADR-060 - NEO Philosophy Kernel is an internal lens layer, not a user-facing quotation source

Status: accepted

Date: 2026-05-28

Context: PRD-047.1 required stable philosophical grounding for Writer without turning source materials into raw quote output or authority references in user-facing responses.

Decision: introduce versioned `NEO Philosophy Kernel` and `Writer Freedom Contract v1` as compact internal prompt/context layers. Kernel content is structured and short, selected deterministically per turn, and exposed in trace/admin only as sanitized metadata (no raw long source passages).

Consequences: Writer receives clearer identity/lens boundaries with guided freedom (`mode_is_hint_not_cage`, `practice_requires_gate`) while safety/hard-boundary governance remains strict. Future PRDs can tune depth/quality using measurable kernel fields without mutating KB authority or copying source text verbatim.

## ADR-060 Amendment - Philosophy Kernel acceptance requires answer-quality and prompt-compactness gates

Status: accepted

Date: 2026-05-28

Context: PRD-047.1 established structural kernel/freedom foundation, but quality acceptance still needed reproducible answer-level validation and prompt-size safeguards to avoid verbose or technical drift.

Decision: PRD-047.2 adds mandatory acceptance gates:
- reproducible kernel quality dataset (>=12 cases),
- answer-level evaluator over final text (not trace flags only),
- prompt compactness budgets for kernel/freedom sections,
- direct-run pass requirement (`12/12`) before acceptance.

Consequences: Philosophy Kernel governance now requires both structural correctness and measurable response quality/compactness; future expansions should build on this gate before dialogue continuity layers.

## ADR-061 - Active Line is a continuity layer; Diagnostic Center observes but does not rigidly command Writer

Status: accepted

Date: 2026-05-28

Context: live dialogue failures after PRD-047.2 showed repeated mechanical revoicing and unsolicited action-step drift even when kernel and practice gates were present.

Decision: introduce `Active Line / Dialogue Continuity v1` as lightweight deterministic layer (`active_line.py`) that computes per-turn intent/continuity/repair/revoicing/practice signals and passes them into Writer contract/prompt/compliance. Diagnostic Center and admin runtime surfaces expose this layer read-only; they do not become a rigid command system for Writer.

Consequences: dialogue continuity behavior becomes reproducible and testable (`dry/direct/live` runners), practice suppression is explicit on mechanism-first turns, correction turns use repair mode, and architecture keeps Writer freedom with bounded deterministic guardrails.

## ADR-062 - Response Planner v1 is deterministic next-meaningful-move layer, not a new answer-writing agent

Status: accepted

Date: 2026-05-28

Context: after PRD-047.3, continuity signals reduced drift, but Writer still needed compact per-turn guidance about answer shape/depth/question/practice behavior to keep one coherent move per turn without turning Writer into a rigid script.

Decision: add `Response Planner v1` as deterministic layer between Active Line and WriterContract. Planner does not call LLMs and does not produce user-facing text; it computes compact move/policy fields (`next_move`, `answer_shape`, `response_depth`, `question_policy`, `practice_policy`, `revoicing_policy`, `must_include`, `must_avoid`) from existing runtime signals. Safety, Knowledge Answer routing, and Practice Gate remain hard boundaries; Writer Freedom Contract remains active as guided style/freedom frame.

Consequences: turn-level move selection becomes reproducible and traceable (`debug/api/admin/runtime`), live acceptance can enforce strict no-fallback planner-trace policy, and future quality work can calibrate answer fit on measurable planner outputs without changing governance authority fields or adding a new LLM agent.

## ADR-063 - Planner quality acceptance requires answer-fit calibration on weak live groups, not planner-trace presence alone

Status: accepted

Date: 2026-05-28

Context: PRD-047.4 proved structural planner integration and trace visibility, but live cases still showed weak semantic fit (low-resource, safety-adjacent distress, defensive framing, close turns, no-question requests, explicit step requests, repair turns) despite formally valid planner fields.

Decision: PRD-047.5 introduces mandatory planner quality calibration with deterministic text-level override signals in `response_planner.py`, answer-level fit evaluator over final writer text, and strict runner acceptance across `dry/direct/live` with no runner-side live fallback.

Consequences: acceptance now requires both structural planner trace and behavioral fit between planner decision and final answer; planner remains deterministic and non-LLM, while Writer Freedom Contract remains active under stronger policy-obedience checks.

## ADR-064 - PRD-047.5-HF1 enforces strict planner-vs-final-answer obedience and closes safety-adjacent false positives

Status: accepted

Date: 2026-05-29

Context: post-acceptance audit of PRD-047.5 found a critical false-positive class: `response_planner` selected `stabilize_safety / safety_grounding`, but final answer drifted into mechanism/explanation text while evaluator still returned `passed=true`.

Decision: PRD-047.5-HF1 hardens answer-fit acceptance on final text with strict shape/policy checks and mismatch counters (`safety_grounding`, `short_support`, `question_policy=none`, `practice_policy=forbidden`, `planner_answer_shape_alignment`), keeps live runner planner source API-trace-only, and applies minimal writer compliance repair where strict evaluator exposed real runtime drift.

Consequences: acceptance evidence now rejects planner/answer mismatch in safety-adjacent and no-question paths; HF1 artifacts are green only when final answer obeys planner shape/policy (`dry=26/26`, `direct=26/26`, `live=26/26`).



## ADR-069 - PRD-047.11-AUDIT is evidence-first and may close as warning

Status: accepted

Date: 2026-06-02

Context: after PRD-047.11, previous dry/direct/live artifacts claimed writer-first acceptance, but live owner feedback still reported greeting over-analysis, stale mechanism phrases, and weak truthfulness between synthetic checks and real dialogue quality.

Decision:
- add a dedicated `PRD-047.11-AUDIT` runner/dataset/artifact pack focused on source inventory, acceptance-gate truthfulness, live case matrix, raw traces, and prompt canvases;
- treat missing browser proof (`playwright_not_installed`) and incomplete admin screenshot evidence as warning-grade audit outcomes, not silent passes;
- keep single runtime / single Writer / advisory-only Diagnostic Center intact during the audit;
- select the next repair PRD by strongest confirmed failure cluster, not by the easiest visible symptom.

Consequences:
- the runtime can remain in `warning` status even when the audit implementation itself is complete;
- stale bad-phrase detection becomes stricter and scans all turns/traces, reducing false-green reports;
- follow-up PRD selection is evidence-based (`PRD-047.11-HF1` before broader profile consolidation).

## ADR-070 - Writer-visible advisory sanitization after PRD-047.11-HF1

Status: accepted

Date: 2026-06-02

Context: PRD-047.11-AUDIT showed that `mvp_free_dialogue` still leaked legacy diagnostic/planner/active-line command pressure into the writer-visible prompt (`WRITER MOVE MUST DO`, raw practice suppression flags, planner must_include/must_avoid markers, and stale fallback phrases). The runtime needed a prompt-diet repair without adding a new mode, new agent, or stronger user-facing safety block.

Decision:
- keep `FINAL ANSWER DIRECTIVE` as the main writer-visible governing block;
- preserve raw diagnostic/planner/active-line data in trace/admin/evidence only;
- convert writer-visible legacy signals into a compact neutral advisory summary through `legacy_advisory_sanitizer_v1`;
- rewrite practice suppression semantics to `no_exercise_but_answer_normally`, meaning "no unsolicited exercise/practice suggestion" rather than "no substantive answer";
- keep bad phrase blocklists evaluation-only and remove stale template/fallback sources instead of steering Writer with blocklist instructions.

Consequences:
- Writer receives less imperative prompt pressure in `mvp_free_dialogue`, while observability remains intact;
- prompt canvases can be audited for absence of raw legacy command blocks without losing runtime debug detail;
- future UI/browser proof work can focus on rendering and evidence capture rather than prompt-assembly cleanup.

## ADR-071 - Fresh chat starts as a local context line until continuation or knowledge need is explicit

Status: accepted

Date: 2026-06-04

Context: live evidence after PRD-047.11-HF1 showed that a new greeting-only chat could still inherit stale mechanism/topic steering from prior sessions, producing over-analytical first answers and repair friction.

Decision:
- add deterministic `fresh_chat_context_policy_v1`;
- treat the first 1-2 turns of a new chat as local current-chat scope by default;
- block cross-session topic continuation on greeting/contact turns unless the user explicitly asks to continue a previous topic or asks a real knowledge/concept question;
- expose the policy in trace, live evidence, and admin runtime effective payload.

Consequences:
- fresh greetings no longer pull stale mechanism context into the active writer path;
- explicit continuation still re-enables cross-session grounding with auditable reasons;
- no new agent, no new runtime path, and no governance/KB mutation were introduced.

## ADR-072 - Writer-visible RAG must pass one final context package gate

Status: accepted

Date: 2026-06-04

Context: live prompt canvases showed a contradiction where retrieval could be classified as `memory_only` or `none`, yet raw `KNOWLEDGE RAG HITS` still leaked into the writer-visible prompt.

Decision:
- introduce `writer_context_package_v1` as the final assembly boundary for writer-visible context;
- allow trace/admin to retain `rag_candidates_for_trace`, but pass `rag_for_writer` only when the gate explicitly includes it;
- keep greeting repairs, short social/contact turns, and fresh-chat non-knowledge turns free from writer-visible raw RAG chunks;
- expose gate counts/reasons and runtime versions in admin effective payload and live evidence exports.

Consequences:
- retrieval observability remains intact without bypassing the writer-visible gate;
- real browser/live cases can verify both prompt hygiene and answer behavior on the same runtime path;
- the system stays unified: no duplicated orchestrator, no new guard branch, no KB/governance mutation.


## ADR-073 - Unified dialogue policy v2 consolidates preset modes and dialogue-state resolvers in one runtime path

Status: accepted

Date: 2026-06-05

Context: after the PRD-047.9..047.11 chain, `safe_guided` and `mvp_free_dialogue` still behaved like partially separate logic branches, while live follow-up failures (`да`, repair complaint, style preference, repeated direct question, close ack) showed that Writer needed one explicit answer obligation instead of more phrase-specific patches.

Decision:
- keep one multiagent runtime path and normalize behavior through `unified_dialogue_policy_v2`;
- treat `safe_guided`, `free_dialogue_default`, and `mvp_free_dialogue` aliasing as preset resolution, not as separate orchestrators or API paths;
- introduce deterministic dialogue-state layers: `dialogue_act_resolver_v1`, `last_assistant_offer_v1`, `unanswered_question_tracker_v1`, `dialogue_style_state_v1`, and `answer_obligation_resolver_v1`;
- keep `final_answer_directive_v1` as the single Writer-facing control block and `writer_context_package_v1` as the single Writer context package;
- preserve advisory-only roles for Diagnostic Center / Planner / Active Line / Diagnostic Card and keep minimal safety boundaries hard.

Consequences:
- short follow-ups, repairs, confirmations, and style requests are handled through reusable runtime state instead of exact-text patches;
- Admin Runtime, live evidence, and browser/admin acceptance expose one coherent effective policy contract;
- no new LLM agent, no new runtime branch, no KB governance mutation, and no production rollout were introduced.

## ADR-074 - User-facing static replies are not allowed outside narrow safety/minimal-contact boundaries

Status: accepted

Date: 2026-06-08

Context: PRD-047.14-HF1.1 audited remaining hardcoded user-facing reply candidates after the active template-family fallback repair. The audit found active static explanation/repair/direct-answer candidates that can bypass Writer authorship if left as runtime answer factories.

Decision:
- keep Writer as the owner of semantic final answers;
- allow static user-facing text only for narrow safety or minimal-contact boundaries with trace evidence;
- treat repair/explanation/knowledge-answer stubs as candidates for targeted removal or conversion to Writer retry/contract signals;
- keep detector constants, test fixtures, historical artifacts, and docs outside the user-facing reply boundary;
- preserve audit-only no runtime mutation in PRD-047.14-HF1.1 and defer removal to `PRD-047.14-HF1.2`.

Consequences:
- no-stub boundary evidence is now explicit and reproducible;
- future cleanup must remove or convert active static reply factories without adding a new Writer/orchestrator branch;
- safety/minimal fallback exceptions remain narrow, documented, and auditable.

## ADR-074 Amendment - Static repair answers must become Writer retry/contract signals

Status: accepted

Date: 2026-06-08

Context: PRD-047.14-HF1.2 removed the high-confidence Writer-side static semantic repair class found by HF1.1 without replacing it with new canned text.

Decision:
- static user-facing repair or knowledge answers are not valid runtime fixes;
- when Writer output fails, runtime must provide feedback to Writer through existing gate/retry/directive signals or quarantine state effects;
- runtime may not replace Writer with a canned semantic answer;
- `no_stub_repair_signal_v1` is a control/observability signal only and must carry `user_facing_replacement_created=false`.

Consequences:
- final-answer authorship remains with Writer;
- failed repair attempts are retried or quarantined by the existing final-answer acceptance gate;
- remaining summary/advisory/static candidates require separate PRD scope instead of hidden in-place rewriting.
