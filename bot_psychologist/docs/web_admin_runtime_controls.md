# Web Admin Runtime Controls

## Runtime Effective Endpoints
Read-only runtime truth:
- `GET /api/admin/runtime/effective`
- `GET /api/v1/admin/runtime/effective`

## Philosophy Kernel Effective Block
Includes:
- `kernel_enabled`
- `kernel_version`
- `selected_lenses_visible`
- `quote_policy`
- `practice_policy`
- `prompt_budget`
- `quality_calibration`

`quality_calibration` is loaded from PRD-047.2 direct artifact when available:
- `last_prd`
- `last_direct_passed`
- `last_direct_cases_total`
- `artifact_present`

## Writer Freedom Effective Block
Includes:
- `enabled`
- `version`
- `freedom_level`
- `mode_is_hint_not_cage`
- `question_limit`
- `practice_requires_gate`

## Active Line Effective Block
Includes:
- `enabled`
- `version`
- `revoicing_policy`
- `practice_suppression_active`
- `user_intent`
- `continuity_mode`
- `last_quality_calibration`

## Response Planner Effective Block
Includes:
- `enabled`
- `version`
- `kind`
- `role`
- `live_acceptance_requires_api_trace`
- `last_quality_calibration`

## Admin UI Surface
`web_ui/src/components/admin/AdminPanel.tsx` renders read-only runtime cards for:
- philosophy kernel version/enabled/selected-lenses visibility
- prompt budget limits
- last quality calibration status
- writer freedom contract state
- active line runtime state/calibration summary
- response planner runtime state/calibration summary

No prompt/source editor is added in this PRD.
