# Project State - Bot Psychologist / Neo MindBot

## Current Stage
Проект находится на стадии `post-PRD-046.1.13-production-limited-execution-cycle-passed`: Diagnostic Center v1 остаётся trace-only shadow слоем, Planner Bridge остаётся candidate-only, compare-слой `planner_bridge_compliance_shadow` остаётся trace-only, `planner_bridge_writer_contract_pilot` остаётся `pilot_shadow_only`, `writer_prompt_replay` остаётся `offline_replay_only`, а prompt-constraint pilot runtime остаётся default-off limited allowlisted test path. Выполнен один production-limited execution cycle с rollback-first контролем и без broad rollout.
В `PRD-046.1.2` добавлены отдельный модуль divergence-классификации, shadow-only Planner Bridge contracts/builder и eval runner с расширенным набором (`24/24`), подтверждены `hard_blocker_count=0`, `safety_bridge_pass_rate=1.0`, `kb_boundary_violation_count=0`, `raw_kb_text_exposure_count=0`, `user_path_effect_count=0`, `planner_bridge_apply_to_writer_count=0`, `planner_bridge_contract_ready=true`, `final_status=passed`, при сохранении no-mutation proof (`all_blocks/registry/config` без изменений).
В `PRD-046.1.2-HF1` исправлен encoding-дефект `test_command_output.txt` (NUL-corruption), добавлен reusable validator `validate_prd_artifact_encoding.py`, подтверждено `final_status=passed` для артефактов `PRD-046.1.2` (`utf8_decode_error_count=0`, `nul_byte_file_count=0`, `nul_char_file_count=0`, `json_parse_error_count=0`).
В `PRD-046.1.3` добавлены compare-mode contract/builder/eval runner для сопоставления `writer_move_instructions` и `planner_bridge_candidate` в `shadow_compare_only` режиме. Подтверждены `cases_passed=30/30`, `hard_blocker_count=0`, `unexpected_blocked_count=0`, `safety_compatibility_pass_rate=1.0`, `user_path_effect_count=0`, `writer_prompt_changed_by_bridge_count=0`, `writer_contract_changed_by_bridge_count=0`, `final_answer_changed_by_bridge_count=0`, `planner_bridge_apply_to_writer_count=0`, `artifact_encoding_hygiene_passed=true`, `final_status=passed`.
В `PRD-046.1.4` добавлен controlled Writer-Contract pilot (`planner_bridge_writer_contract_pilot`) как non-mutating compare-only overlay: `cases_passed=36/36`, `hard_blocker_count=0`, `safety_pilot_pass_rate=1.0`, `kb_boundary_violation_count=0`, `raw_kb_text_exposure_count=0`, `writer_contract_changed_by_pilot_count=0`, `writer_prompt_changed_by_pilot_count=0`, `final_answer_changed_by_pilot_count=0`, `pilot_apply_to_writer_contract_count=0`, `pilot_apply_to_writer_prompt_count=0`, `pilot_apply_to_final_answer_count=0`, `runtime_smoke_ok=true`, `artifact_encoding_hygiene_passed=true`, `final_status=passed`.
В `PRD-046.1.5` добавлен offline replay/eval слой `writer_prompt_replay` для сравнения baseline prompt-context и pilot candidate namespace без production activation. Подтверждены `cases_passed=40/40`, `hard_blocker_count=0`, `safety_replay_pass_rate=1.0`, `kb_boundary_violation_count=0`, `constraint_conflict_count=0`, `prompt_bloat_blocker_count=0`, `writer_contract_changed_by_replay_count=0`, `writer_prompt_changed_by_replay_count=0`, `final_answer_changed_by_replay_count=0`, `provider_called_count=0`, `runtime_smoke_ok=true`, `artifact_encoding_hygiene_passed=true`, `final_status=passed`.
В `PRD-046.1.6` добавлен controlled runtime decision слой `prompt_constraint_pilot_runtime` с default-off guardrails (`PROMPT_CONSTRAINT_PILOT_ENABLED=false`, `PROMPT_CONSTRAINT_PILOT_FORCE_DISABLED=true`), allowlisted/test-user `test_apply` режимом и rollback-priority. Подтверждены `cases_passed=50/50`, `default_off_user_path_effect_count=0`, `shadow_mode_apply_count=0`, `test_apply_applied_count=10`, `allowlist_violation_count=0`, `rollback_switch_passed=true`, `safety_apply_blocked_count=3`, `runtime_smoke_ok=true`, `limited_runtime_flag_ready=true`, `artifact_encoding_hygiene_passed=true`, `final_status=passed`.
В `PRD-046.1.7` добавлен runtime evidence/rollback/quality gate runner `run_prompt_constraint_pilot_quality_gate.py` и полный набор артефактов gate-решения. Подтверждены `final_status=passed`, `decision=supervised_rollout_candidate`, `evidence_quality=sufficient`, `rollback_failure_count=0`, `candidate_weaker_than_baseline_count=0`, `raw_kb_text_exposure_count=0`, `normal_user_apply_count=0`, `provider_called_by_eval_count=0`, `production_mutation_detected=false`, `artifact_encoding_hygiene_passed=true`.
В `PRD-046.1.8` добавлен supervised rollout planning/readiness слой (`run_prompt_constraint_supervised_rollout_plan.py`) и артефакты плана (`supervised_rollout_plan`, `readiness_gate`, `abort_criteria`, `toggle_matrix`, `operator_runbook`). Подтверждены `final_status=passed`, `decision=ready_for_supervised_execution_prd`, `enabled_default_false=true`, `force_disabled_default_true=true`, `normal_users_allowed=false`, `max_initial_cohort_size=3`, `rollback_first_policy_preserved=true`, `toggle_matrix_ready=true`, `production_apply_performed=false`, `provider_called_by_plan=false`, `artifact_encoding_hygiene_passed=true`.
В `PRD-046.1.9` выполнен один controlled supervised execution/observability gate (`run_prompt_constraint_supervised_execution_gate.py`) с cohort `3` (`pilot_alpha/pilot_beta/pilot_gamma`) и отдельным normal-user control case. Подтверждены `final_status=passed`, `decision=continue_supervised`, `test_apply_applied_count=3`, `normal_user_apply_count=0`, `rollback_failure_count=0`, `candidate_weaker_than_baseline_count=0`, `raw_kb_text_exposure_count=0`, `provider_called_by_execution_count=0`, `production_mutation_detected=false`, `artifact_encoding_hygiene_passed=true`.
В `PRD-046.1.10` выполнен второй supervised continuation cycle на расширенном allowlisted cohort (`6`: `pilot_alpha/pilot_beta/pilot_gamma/pilot_delta/pilot_epsilon/pilot_zeta`) через `run_prompt_constraint_supervised_continuation_gate.py`. Подтверждены `final_status=passed`, `decision=continue_supervised`, `scenario_coverage_passed=true` (`6/6`), `test_apply_applied_count=6`, `normal_user_apply_count=0` (2 normal control cases), `rollback_failure_count=0`, `stale_apply_after_force_disabled_count=0`, `candidate_weaker_than_baseline_count=0`, `raw_kb_text_exposure_count=0`, `provider_called_by_continuation_count=0`, `production_mutation_detected=false`, `artifact_encoding_hygiene_passed=true`.
В `PRD-046.1.11` выполнен supervised results consolidation / rollout decision gate (`run_prompt_constraint_supervised_consolidation_gate.py`) по артефактам `PRD-046.1.9` и `PRD-046.1.10` без нового execution цикла. Подтверждены `final_status=passed`, `decision=prepare_production_limited_rollout_plan`, `cycles_total=2`, `cycles_passed=2`, `total_test_apply_applied_count=9`, `total_cases_compared=9`, `reproducibility_passed=true`, `risk_register_has_blockers=false`, `provider_called_total=0`, `production_mutation_detected_any=false`, `artifact_encoding_hygiene_all_passed=true`.
В `PRD-046.1.12` построен production-limited rollout plan (`run_prompt_constraint_production_limited_rollout_plan.py`) без execution: сформированы `cohort_policy`, `preflight_gates`, `operator_checklist`, `monitoring_plan`, `rollback_plan`, `abort_criteria`, `readiness_gate` и `operator_runbook`. Подтверждены `final_status=passed`, `decision=ready_for_production_limited_execution_prd`, `execution_performed=false`, `provider_called_by_plan=false`, `production_mutation_detected=false`, `default_flags_changed=false`, `artifact_encoding_hygiene_passed=true`.
В `PRD-046.1.13` выполнен один controlled production-limited execution/monitoring gate (`run_prompt_constraint_production_limited_execution_gate.py`) с единственным target user (`prod_limited_operator_001`) и двумя normal-user controls. Подтверждены `final_status=passed`, `decision=continue_limited`, `execution_window_count=1`, `target_user_count=1`, `production_limited_apply_count=1`, `normal_user_apply_count=0`, `default_off_user_path_effect_count=0`, `rollback_failure_count=0`, `stale_apply_after_force_disabled_count=0`, `safety_regression_count=0`, `kb_policy_regression_count=0`, `raw_kb_text_exposure_count=0`, `provider_called_by_execution_count=0`, `production_mutation_detected=false`, `artifact_encoding_hygiene_passed=true`.

## Current Runtime Architecture
Активный user-path:
User message -> State Analyzer -> Thread Manager -> Memory Retrieval -> Context Assembly -> Diagnostic Card -> Diagnostic Center Shadow (trace-only) -> Writer Move Compliance -> Writer -> Validator/Trace -> Memory Update.

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
- Diagnostic Center v1 shadow + Planner Bridge contract in shadow/eval-only mode (no writer/user-path effect).

## Not Implemented Yet
- Post-run production-limited results consolidation / rollback & quality gate (`PRD-046.1.14`).

## Known Risks
- Без регулярной обработки pending turn summaries возможен возврат к deterministic fallback чаще, чем ожидается.
- В окружениях с нестабильной кодировкой входа возможны искажения текстовых сигналов; safety-guards должны сохраняться conservative.
- Premature Diagnostic Center launch создаст ложную уверенность в диагностике при неготовом context-quality слое.
- Overlay apply без отдельного controlled PRD нарушит release discipline.
- Старый review queue (`PRD-046.0.7`) устарел после смены block boundaries и не может применяться напрямую.
- Операции reindex остаются чувствительными к локальной стабильности Chroma SQLite; обязательны backup/manifest + recovery шаги.
- Исторические Chroma proof-артефакты используются только как diagnostic evidence и не могут override live mismatch в strict gate.

## Next Planned PRDs
1. PRD-046.1.14 - Production-Limited Prompt-Constraint Pilot Results / Rollback & Quality Gate v1.

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
- Source cycle: PRD-046.1.13



