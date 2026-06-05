# Diagnostic Center Boundary

- status: current
- last_verified_prd: PRD-047.12-HF1

## Active Now
- Diagnostic Center remains present and visible for admin/runtime observability.
- It is advisory context only for Writer-first final answer assembly.
- It does not rewrite, block, or hard-authorize user-facing final answers.

## Not Production Ready
- Diagnostic Center is not a production clinical decision system.

## How To Test
- Check Admin Runtime roles: `diagnostic_center_role=advisory_context_only`.
- Run no-mutation proof artifacts.
