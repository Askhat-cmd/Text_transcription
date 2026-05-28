# Web Admin Runtime Controls

## Runtime Effective Endpoint
Read-only runtime truth:
- `GET /api/admin/runtime/effective`
- `GET /api/v1/admin/runtime/effective`

`PRD-047.1` adds two blocks:
- `philosophy_kernel`
- `writer_freedom_contract`

## Effective Philosophy Kernel Block
Fields:
- `enabled`
- `version`
- `identity.bot_identity`
- `identity.role`
- `quote_policy`
- `practice_policy`
- `principles_count`
- `boundaries_count`
- `lenses`

## Effective Writer Freedom Block
Fields:
- `enabled`
- `version`
- `freedom_level`
- `mode_is_hint_not_cage`
- `question_limit`
- `practice_requires_gate`

## Admin UI Surface
`web_ui/src/components/admin/AdminPanel.tsx` renders read-only runtime cards:
- Philosophy Kernel
- Writer Freedom Contract

This keeps Web Admin as the operational control plane while avoiding prompt-source leakage.
