# Admin Control Diagnostic Center (Admin Control Diagnostic Center)

## Purpose (Назначение)
Operational control map для runtime governance Diagnostic Center на single-developer phase после `PRD-046.1.37-HF1` и `PRD-046.1.38`.

Документ определяет:
- runtime modes;
- admin API contract;
- Web Admin behavior;
- boundary flags и rollout limits;
- kill-switch priority и reset behavior.

## Scope (Область)
- Local/developer governance controls доступны.
- Production rollout authority не предоставляется этими controls.
- `production_ready`, `broad_rollout_allowed`, `normal_user_activation_allowed` остаются `false`.
- Invariant flags:
  - `production_ready=false`
  - `broad_rollout_allowed=false`
  - `normal_user_activation_allowed=false`

## Runtime Modes (Режимы runtime)
- `disabled`
- `shadow`
- `developer`
- `creator_only`
- `allowlist`
- `developer_local_all_users`

`developer_local_all_users` — явно local-governed mode, а не production broad rollout.

## Admin API (Admin API)
- `GET /api/admin/diagnostic-center/effective`
- `POST /api/admin/diagnostic-center/control`
- `POST /api/admin/diagnostic-center/reset`
- mirrored aliases под `/api/v1/admin/diagnostic-center/*`

### Effective payload highlights (Основные поля effective payload)
- `schema_version=diagnostic_center_control_v1`
- `status=completed_for_current_creator_only_phase`
- `current_mode`
- `effective_active`
- `force_disabled`
- `available_modes`
- `boundary_flags`
- `scope.note`
- `last_evidence.last_prd`
- `last_evidence.recommended_runner_timeout_sec`

## Kill switch priority (Приоритет kill switch)
`force_disabled=true` всегда побеждает mode и устанавливает `effective_active=false`.

## Reset behavior (Поведение reset)
Reset возвращает safe default:
- `mode=creator_only`
- `force_disabled=false`
- empty allowlist

## Web Admin (Web Admin)
Admin UI экспонирует отдельную вкладку **Diagnostic Center** с:
- current status card;
- mode selector;
- force-disabled toggle;
- allowlist editor;
- boundary flags (read-only);
- actions: refresh/save/reset.

При выборе `developer_local_all_users` UI должен показывать явное предупреждение, что это local testing mode, а не production rollout.

## Safety / privacy / governance (Безопасность / privacy / governance)
- без mutation `.env`;
- без exposure raw provider payload;
- без KB governance mutation (`chunk_type`, `allowed_use`, `safety_flags`);
- без Chroma reindex в scope этого PRD.
