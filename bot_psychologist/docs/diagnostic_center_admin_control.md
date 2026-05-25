# Diagnostic Center Admin Control

## Purpose
Operational control map for Diagnostic Center runtime governance in the single-developer phase after `PRD-046.1.37-HF1` and `PRD-046.1.38`.

This document defines:
- runtime modes;
- admin API contract;
- Web Admin behavior;
- boundary flags and rollout limits;
- kill-switch priority and reset behavior.

## Scope
- Local/developer governance controls are available.
- Production rollout authority is not granted by these controls.
- `production_ready`, `broad_rollout_allowed`, `normal_user_activation_allowed` remain `false`.
- Invariant flags:
  - `production_ready=false`
  - `broad_rollout_allowed=false`
  - `normal_user_activation_allowed=false`

## Runtime Modes
- `disabled`
- `shadow`
- `developer`
- `creator_only`
- `allowlist`
- `developer_local_all_users`

`developer_local_all_users` is explicitly local-governed mode and not production broad rollout.

## Admin API
- `GET /api/admin/diagnostic-center/effective`
- `POST /api/admin/diagnostic-center/control`
- `POST /api/admin/diagnostic-center/reset`
- mirrored aliases under `/api/v1/admin/diagnostic-center/*`

### Effective payload highlights
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

## Kill switch priority
`force_disabled=true` always wins over mode and sets `effective_active=false`.

## Reset behavior
Reset returns safe default:
- `mode=creator_only`
- `force_disabled=false`
- empty allowlist

## Web Admin
Admin UI exposes a dedicated **Diagnostic Center** tab with:
- current status card;
- mode selector;
- force-disabled toggle;
- allowlist editor;
- boundary flags (read-only);
- actions: refresh/save/reset.

When `developer_local_all_users` is selected, UI must show explicit warning that this is local testing mode and not production rollout.

## Safety / privacy / governance
- no `.env` mutation;
- no raw provider payload exposure;
- no KB governance mutation (`chunk_type`, `allowed_use`, `safety_flags`);
- no Chroma reindex in this PRD scope.
