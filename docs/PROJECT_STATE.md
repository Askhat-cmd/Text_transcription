# Project State - Bot Psychologist / Neo MindBot

## Current Stage
Проект находится на стадии `post-PRD-046.0.11-final-runtime-readiness-summary`: финальная readiness-сводка перед переходом к Diagnostic Center сформирована и сохранена в machine-readable + human-readable артефактах.
В `PRD-046.0.11` подтверждены runtime/admin/BotDB/KB/Chroma/retrieval/governance/legacy-SD/UTF-8/docs gates, live endpoints на `http://127.0.0.1:8003` проверены, `focus_source=123__кузница_духа`, `blocks/chroma=247/247/247`, no-mutation proof (`all_blocks/registry/config`) пройден, переход к `PRD-046.1` разрешён.

## Current Runtime Architecture
Активный user-path:
User message -> State Analyzer -> Thread Manager -> Memory Retrieval -> Context Assembly -> Diagnostic Card -> Writer Move Compliance -> Writer -> Validator/Trace -> Memory Update.

Runtime работает без cascade legacy режима и опирается на управляемый pipeline с диагностическим trace, где Writer не является единственным диагностическим узлом.

## Current Knowledge Base State
Knowledge Base governance слой внедрен: chunk_type/allowed_use/safety_flags остаются deterministic authority. Текущее production-состояние: `247` governed blocks для `123__кузница_духа`; Chroma collection также `247` блоков, source set = только `123__кузница_духа`. Источник `КУЗНИЦА ДУХА` трактуется как internal lens library, не как user-facing цитатник.
В `PRD-046.0.10` legacy SD cleanup завершён: SD labeler отключён по умолчанию и может запускаться только при явном `enabled + explicit_legacy_mode`; API `sd_level` остаётся compatibility-only и игнорируется как retrieval filter; dashboard readiness больше не зависит от legacy SD metadata.
В `PRD-046.0.10-HF1` закрыт финальный хвост: canonical `config.yaml` закреплён как default-disabled (`sd_labeling.enabled=false`, `legacy_sd_labeling.enabled=false`), env overrides переведены в runtime-only режим без автоперезаписи конфига, runtime smoke artifacts переведены на UTF-8-safe генерацию и проверку маркеров mojibake.

## Current Context / Memory State
Context Assembly реализован и стабилизирован. Async turn LLM summary additive слой прошел HF1 acceptance-calibration: eval-case coverage расширена, validator safety guards усилены, processor evidence pending->ready подтверждён. Для длинных turns используется `llm_abstractive_v1` при `ready+valid+hash-match`, иначе deterministic fallback `deterministic_extractive_v1`. Raw dialogue history сохраняется полностью, summary-поля остаются добавочным слоем и не подменяют первичные turn records.

## Current LLM Enrichment State
Offline LLM enrichment pipeline внедрен и откалиброван, затем применен controlled overlay cycle:
- RUN1 показал blocker по unknown lens.
- HF2 закрыл unknown lens и quote/invariant риски.
- HF3 закрыл low_resource avoid_when hard-fail.
Текущее состояние: advisory enrichment metadata записана в `metadata.llm_enrichment` для 60 блоков батча APPLY1 без мутации governance authority полей.
Новый post-reprocess baseline (`247` block ids) построен в `PRD-046.0.9`; в `PRD-046.0.9-RUN1` выполнен реальный enrichment run: `items_completed=247`, `validation_errors_count=0`, `review_queue_items_count=87`, `provider_status=called`.
В `PRD-046.0.9-RUN1-HF1` dashboard получает enrichment/review состояние из артефактов RUN1 через единый endpoint `/api/dashboard/` и показывает явные warning/error причины вместо немых пустых карточек.
В `PRD-046.0.9-RUN1-HF2` endpoint/Frontend дополнительно откалиброваны под runtime acceptance: поддерживаются `/api/dashboard` и `/api/dashboard/`, production-block card опирается на focus-source (`247`), registry total показывается отдельно, а при API/payload проблемах отображается явная ошибка.
В `PRD-046.0.9-RUN1-HF3` registry endpoint стал row-isolated (одна плохая строка больше не роняет весь список), frontend реестра получил явные loading/error/empty состояния, а consistency gate подтвердил browser-visible состояние без reindex/apply.
В `PRD-046.0.9.1` добавлены CLI `prepare_human_review_decisions.py` и `validate_human_review_decisions.py`, артефакты review-workbench/template/validation/no-mutation сгенерированы, deterministic safety checks по decisions overlay включены (forbidden/raw/private keys, secret-like values, authority-mutation attempts, duplicate/unknown/mismatch guards). Production apply/reindex не выполнялись.
В `PRD-046.0.9.1-HF1` добавлены `audit_blocks_snapshot_alignment.py` и `restore_blocks_snapshot_alignment.py`, найден authoritative snapshot (`candidate_to_apply.snapshot.json`) и восстановлен blocks snapshot до `247` с backup proof. Добавлен strict gate `prepare_human_review_decisions.py --require-aligned`.
В `PRD-046.0.9.2` добавлены `prepare_architect_review_batches.py` и `validate_architect_decisions_overlay.py`; сформированы sanitized architect review batches (`8` batch-файлов на `87` items), `architect_decisions_template/overlay`, validation report с `ready_for_architect_review=true` и `apply_ready=false`, а также no-mutation proof без production/apply/reindex.
В `PRD-046.0.9.3` добавлены `architect_auto_decision_policy.py` и `generate_architect_auto_decisions.py`; сгенерирован auto-decisions overlay (`87` решений), validation прошло с `coverage_percent=100.0`, `remaining_items_count=0`, `apply_ready=true`, официальный overlay обновлён, no-mutation proof подтверждён (`all_blocks/registry/chroma` без изменений).
В `PRD-046.0.7.1` добавлены `controlled_review_decision_apply.py` и CLI `preflight_review_decision_apply.py` / `plan_review_decision_apply.py` / `apply_review_decisions_controlled.py`; выполнен controlled apply (`updated_blocks=200`) с backup/proof/smoke артефактами, инварианты authority сохранены (`text/chunk_type/allowed_use/safety_flags/source_id/block_id/governance` неизменны), acceptance snapshot `passed=true`.
В `PRD-046.0.7.2` добавлены `post_apply_quality_gate.py` и `run_post_apply_quality_gate.py` с артефактами quality gate; подтверждены `data_consistency_passed=true`, `apply_route_consistency_passed=true`, `retrieval_quality_passed=true`, `writer_kb_policy_passed=true` и no-mutation proof (`all_blocks_merged_mutated=false`, `registry_mutated=false`) без reindex/provider вызовов.
В `PRD-046.0.7.2-HF1` добавлены `admin_live_smoke.py` и `run_admin_live_smoke.py` с launch manifest/readiness polling/schema checks/no-mutation proof; зафиксирован честный blocker `done_with_admin_launch_blocker` после неуспешного startup/readiness (`/api/status`, `/api/registry`, `/api/dashboard`, `/api/dashboard/` недоступны), при этом production hashes не изменились.
В `PRD-046.0.7.2-HF2` добавлен HF2 runner `run_admin_live_smoke_hf2.py`, закрыт runtime blocker на внешнем сервере (`http://127.0.0.1:8003`), сформированы live/scheme/quality/no-mutation артефакты и отчёты; quality gate переведён в `passed` без production apply/reindex/provider вызовов.
В `PRD-046.0.7.2-HF3` внедрён strict chroma reconciliation gate (`run_admin_live_smoke_hf3.py` + `dashboard_chroma_reconciliation.py`), добавлены `/api/registry/` compatibility checks и запрет historical-proof override; live mismatch `dashboard.chroma.count=229` честно зафиксирован как blocker `done_with_chroma_count_blocker` без production мутаций.
В `PRD-046.0.7.2-HF4` добавлены инструменты `diagnose_chroma_runtime_count.py`, `reindex_focus_source_chroma_controlled.py`, `run_chroma_recovery_hf4.py`; подтверждён actual mismatch (`direct=229`), выполнен controlled focus-only reindex с backup, затем исправлен dashboard count source (`ChromaManager.get_stats -> collection.count()`), после чего live gate прошёл (`dashboard/direct/registry = 247`), без мутации `all_blocks_merged.json` и `registry.json`.

## Current Admin Source Hygiene State
Delete policy в реестре стала явной и согласованной между backend/frontend:
- `Защищено` только для focus source `123__кузница_духа`;
- `Удалить` для безопасных zero-block источников;
- `Очистить тестовый` для test-like `<=1` блока только при safety-gates;
- snapshot registry создаётся перед фактическим delete-мутированием.
Production focus source и Chroma production count остаются неизменны.

## Current Writer KB Snippet State
Root cause mid-word KB snippet clipping подтверждён в `knowledge_policy._sanitize_preview` (жёсткий char-cut). В HF2 внедрена boundary-aware truncation логика (sentence/word boundary + ellipsis `…`) без изменения governance authority и без изменения production block text.

## Stable Modules
- Multiagent runtime orchestration.
- State Analyzer routing/calibration (deterministic contract).
- Thread Manager diagnostics baseline.
- Context Assembly v1 deterministic path.
- Diagnostic Card + Writer Move Compliance contracts.
- Governance-first KB policy and redaction-safe trace.
- BotDB/Chroma retrieval restore path.
- Admin Review Workflow v1 (contracts + sanitizer + queue/decision validation CLI).
- BotDB source hygiene/readiness tools v1 (`source_hygiene_audit/apply`, `legacy_sd_usage_audit`, `reprocess_readiness_gate`).

## Experimental / In Progress Modules
- Нет активных blocker-hotfix модулей в post-apply admin/runtime gate.

## Not Implemented Yet
- Diagnostic Center v1 (deferred until KB/retrieval/context readiness confirmed).

## Known Risks
- Без регулярной обработки pending turn summaries возможен возврат к deterministic fallback чаще, чем ожидается.
- В окружениях с нестабильной кодировкой входа возможны искажения текстовых сигналов; safety-guards должны сохраняться conservative.
- Premature Diagnostic Center launch создаст ложную уверенность в диагностике при неготовом context-quality слое.
- Overlay apply без отдельного controlled PRD нарушит release discipline.
- Старый review queue (`PRD-046.0.7`) устарел после смены block boundaries и не может применяться напрямую.
- Операции reindex остаются чувствительными к локальной стабильности Chroma SQLite; обязательны backup/manifest + recovery шаги.
- Исторические Chroma proof-артефакты используются только как diagnostic evidence и не могут override live mismatch в strict gate.

## Next Planned PRDs
1. PRD-046.1 - Diagnostic Center v1 Readiness / Architecture PRD.

## Do Not Do Yet
- Не включать Diagnostic Center до завершения async summary + retrieval eval шага.
- Не менять governance authority (`chunk_type/allowed_use/safety_flags`) через LLM overlay.
- Не превращать KB в direct-quote source для Writer.
- Не подменять deterministic governance решения LLM-логикой.

## Documentation Update Rule
1. PRD, меняющий stage/architecture, обязан обновить PROJECT_STATE.
2. PRD, меняющий последовательность работ, обязан обновить ROADMAP.
3. PRD с новым архитектурным решением обязан обновить DECISIONS.
4. Каждый новый PRD после push обязан обновить PRD_INDEX.
5. TO_DO_LIST остается детальным архивом, docs — краткая operational map.

## Last Updated
- Date: 2026-05-17
- Source cycle: PRD-046.0.11
