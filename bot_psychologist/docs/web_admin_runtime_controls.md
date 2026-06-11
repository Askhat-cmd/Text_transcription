# Web Admin Runtime Controls (Управление runtime в Web Admin)

## Runtime Effective Endpoints (Эффективные runtime endpoints)
Read-only runtime truth:
- `GET /api/admin/runtime/effective`
- `GET /api/v1/admin/runtime/effective`

## Effective Block Philosophy Kernel (Блок Philosophy Kernel)
Включает:
- `kernel_enabled`
- `kernel_version`
- `selected_lenses_visible`
- `quote_policy`
- `practice_policy`
- `prompt_budget`
- `quality_calibration`

`quality_calibration` загружается из PRD-047.2 direct artifact, когда доступен:
- `last_prd`
- `last_direct_passed`
- `last_direct_cases_total`
- `artifact_present`

## Effective Block Writer Freedom (Блок Writer Freedom)
Включает:
- `enabled`
- `version`
- `freedom_level`
- `mode_is_hint_not_cage`
- `question_limit`
- `practice_requires_gate`

## Effective Block Active Line (Блок Active Line)
Включает:
- `enabled`
- `version`
- `revoicing_policy`
- `practice_suppression_active`
- `user_intent`
- `continuity_mode`
- `last_quality_calibration`

## Effective Block Response Planner (Блок Response Planner)
Включает:
- `enabled`
- `version`
- `kind`
- `role`
- `live_acceptance_requires_api_trace`
- `last_quality_calibration`

## Effective Block Planner Drift Guard (Блок Planner Drift Guard)
Включает:
- `enabled`
- `version`
- `mode=observe_only`
- `blocking_user_answers=false`
- `window_size`
- `thresholds.warning_violation_rate`
- `thresholds.critical_rate`
- `last_summary` (скользящие счётчики/rates/by_flag)
- `last_replay_status` (статус direct/live artifact PRD-047.6)

## Effective Block Guided Live Testing (Блок Guided Live Testing)
Включает:
- `enabled`
- `schema_version` (`live_feedback_v1`)
- `mode` (`developer_local`)
- `feedback_storage` (`file_sanitized`)
- `raw_dialogue_saved_by_default=false`
- `scenario_set`
- `scenario_count`
- `last_session_summary_available`

## Admin UI Surface (Поверхность Admin UI)
`web_ui/src/components/admin/AdminPanel.tsx` рендерит read-only runtime cards для:
- версия/enabled/видимость selected lenses philosophy kernel
- лимиты prompt budget
- статус последней калибровки качества
- состояние writer freedom contract
- состояние runtime Active Line / сводка калибровки
- состояние runtime Response Planner / сводка калибровки
- статус runtime Planner Drift Guard / thresholds / rolling counters / replay
- режим/статус захвата runtime Guided Live Testing

Prompt/source editor в этом PRD не добавляется.

## Effective Block Dialogue Policy PRD-047.9 (Блок Dialogue Policy PRD-047.9)
`/api/admin/runtime/effective` теперь также экспонирует explicit effective profile policy:
- `dialogue_policy.profile`
- `dialogue_policy.writer_autonomy`
- `dialogue_policy.planner_authority`
- `dialogue_policy.diagnostic_card_authority`
- `dialogue_policy.writer_move_authority`
- `dialogue_policy.active_line_authority`
- `dialogue_policy.context_budget_chars`
- `dialogue_policy.allow_numbered_lists`
- `dialogue_policy.allow_examples`
- `dialogue_policy.allow_practice_catalog`
- `dialogue_policy.writer_runtime_max_tokens_effective`

Web Admin Runtime tab рендерит эти поля как read-only, чтобы profile value и effective behavior оставались согласованными.

## PRD-047.10 Update (2026-06-01) (Обновление PRD-047.10)
- Runtime effective `dialogue_policy` теперь включает:
  - `human_like_answer_policy` (MVP human-like autonomy contract),
  - `constraint_resolution` (audit metadata advisory overrule).
- Runtime tab должна отображать эти blocks как read-only effective truth.
- Это остаётся developer-local calibration surface; production rollout semantics не подразумеваются.
