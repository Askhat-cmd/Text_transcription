# Deployment

## Scope
Deployment notes for the current multiagent runtime architecture.

## Runtime baseline
- Active runtime: `multiagent_adapter`
- Legacy cascade: removed in PRD-041
- Post-purge stabilization: completed in PRD-042

## Recommended production controls
1. `APP_ENV=prod` guardrails and explicit config validation.
2. Strict CORS allowlist.
3. Centralized rate limiting (shared store such as Redis).
4. Structured logs and trace-safe export policy.

## Health and contract checks
- `GET /api/v1/health`
- `GET /api/admin/runtime/effective`
- Multiagent trace endpoint returns consistent runtime metadata.

## Rollout checklist
1. Apply environment configuration and secrets.
2. Run API with process manager.
3. Build and serve web UI artifacts.
4. Run inventory + core backend regression tests before promoting.

## Out of scope for this doc
- Re-enabling legacy cascade runtime.
- Telegram channel production activation by default.
