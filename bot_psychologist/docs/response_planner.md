# Response Planner (Планировщик ответов)

## Scope (Область)
`Response Planner v1` — детерминированный слой между Active Line и Writer.

Версия:
- `response_planner_v1`

Planner не генерирует user-facing text и не является LLM agent.

## Inputs (Входы)
- `user_message`
- `thread_state`
- `state_snapshot`
- `active_line`
- `knowledge_answer_guard`
- `philosophy_kernel` (только metadata)

## Decision Output (Выход решения)
Основные поля:
- `enabled`
- `next_move`
- `answer_shape`
- `response_depth`
- `target_micro_shift`
- `question_policy`
- `practice_policy`
- `revoicing_policy`
- `continuity_policy`
- `must_include`
- `must_avoid`
- `source_signals`
- `confidence`
- `rationale`

## Core Rules (Основные правила)
- Один answer = один next meaningful move.
- Safety и known-concept routing остаются hard boundaries.
- Practice не является default и требует explicit allow path.
- Если Active Line подавляет revoicing/questions/practice, planner отражает это в policy fields.

## PRD-047.5 Calibration Additions (Дополнения калибровки PRD-047.5)
- Добавлены deterministic text detectors для слабых live groups:
  - low-resource
  - soft-distress (safety-adjacent)
  - defensive world-blame framing
  - explicit no-question request
  - close/thanks turns
  - explicit direct-step/practice request с negated-practice handling
  - repair-misalignment text
- Добавлен mechanism/practice-suppression override path, чтобы избежать false action routing, когда user просит продолжить mechanism analysis без practice.
- Safety, knowledge-answer routing и practice-gate boundaries сохранены как hard constraints.

## Runtime Integration (Интеграция в runtime)
- Orchestrator строит planner decision до `WriterContract`.
- `WriterContract.response_planner` опционален и backward compatible.
- Prompt context получает compact planner fields; Writer остаётся ограничен compliance checks.

## Trace and API (Trace и API-интеграция)
- `debug.response_planner`
- `debug.response_planner_version`
- `debug.response_planner_error`
- `/api/v1/debug/multiagent-trace` отражает planner fields.

## Admin Runtime Visibility (Видимость в Admin Runtime)
`/api/admin/runtime/effective` экспонирует read-only:
- `response_planner.enabled`
- `response_planner.version`
- `response_planner.kind`
- `response_planner.role`
- `response_planner.live_acceptance_requires_api_trace`
- `response_planner.last_quality_calibration`

Admin editing surface в этом PRD не добавляется.

## Calibration Artifacts (Артефакты калибровки)
- `TO_DO_LIST/logs/PRD-047.4/response_planner_dry.json`
- `TO_DO_LIST/logs/PRD-047.4/response_planner_direct.json`
- `TO_DO_LIST/logs/PRD-047.4/response_planner_live.json`
- `TO_DO_LIST/logs/PRD-047.4/response_planner_trace_samples.json`
- `TO_DO_LIST/logs/PRD-047.4/response_planner_policy_violations_report.json`
- `TO_DO_LIST/logs/PRD-047.5/planner_answer_fit_dry.json`
- `TO_DO_LIST/logs/PRD-047.5/planner_answer_fit_direct.json`
- `TO_DO_LIST/logs/PRD-047.5/planner_answer_fit_live.json`
- `TO_DO_LIST/logs/PRD-047.5/planner_answer_fit_trace_samples.json`

## PRD-047.5-HF1 Repair Notes (Заметки repair PRD-047.5-HF1)
- Исправлен false-positive acceptance class, где planner выбирал `stabilize_safety/safety_grounding`, но final answer уходил в mechanism explanation.
- Runner strict checks теперь gate:
  - safety-grounding no-mechanism language
  - short-support compact support shape
  - `question_policy=none` strict no-question/no-question-invite markers
  - `practice_policy=forbidden` strict no-practice-instruction markers
  - planner-shape alignment counters
- HF1 artifacts:
  - `TO_DO_LIST/logs/PRD-047.5-HF1/planner_answer_fit_dry.json`
  - `TO_DO_LIST/logs/PRD-047.5-HF1/planner_answer_fit_direct.json`
  - `TO_DO_LIST/logs/PRD-047.5-HF1/planner_answer_fit_live.json`
  - `TO_DO_LIST/logs/PRD-047.5-HF1/answer_fit_false_positive_regression.json`

## PRD-047.6 Runtime Drift Guard (Runtime Drift Guard, PRD-047.6)
- Добавлен deterministic runtime monitor `planner_drift_guard_v1`:
  - сравнивает `response_planner` vs `final_answer`;
  - эмитирует per-turn `status`, `severity`, `flags` и obedience fields;
  - хранит rolling counters в in-memory monitor window (`max=100`).
- Drift guard — `observe_only`:
  - не блокирует user answers;
  - не переписывает final answer text;
  - не вводит новых LLM agents.
- Новые trace fields:
  - `planner_drift_guard_version`
  - `planner_drift_guard`
  - `planner_drift_guard_error`
  - `planner_drift_summary`
- Runtime replay artifacts:
  - `TO_DO_LIST/logs/PRD-047.6/planner_drift_dry.json`
  - `TO_DO_LIST/logs/PRD-047.6/planner_drift_direct.json`
  - `TO_DO_LIST/logs/PRD-047.6/planner_drift_live.json`
  - `TO_DO_LIST/logs/PRD-047.6/planner_drift_summary.json`
  - `TO_DO_LIST/logs/PRD-047.6/planner_drift_negative_regression.json`

## PRD-047.9 Unified Adaptive Policy Additions (Дополнения Unified Adaptive Policy PRD-047.9)
- Добавлен planner shape для concept-practice overview requests:
  - `next_move=answer_practice_overview`
  - `answer_shape=practice_catalog_explanation`
  - `response_depth=long`
  - `question_policy=optional_none`
  - `practice_policy=overview_allowed`
- Добавлена explicit one-step override branch:
  - если user явно просит one micro-step, planner всё равно возвращает `one_step`.
- Добавлена поддержка stale-active-line signal (`active_line_stale`), чтобы current concept/practice request мог override old line pressure в MVP profile.

## PRD-047.10 Update (2026-06-01) (Обновление PRD-047.10)
- `response_planner` остаётся advisory в MVP profile и не становится blocking rewriter layer.
- Human-like behavior upgrades (repair/summary/direct concrete response shapes) применяются в Writer compliance и unified policy, при этом planner authority остаётся deterministic advisory.
