# PRD-047.29 Constraint Respect Repair Report

Status: passed
Date: 2026-06-23

## Repair Scope

- `latest_turn_constraints_v1` now extracts only explicit latest-turn user constraints:
  - `no_practice`
  - `no_breathing_only`
  - `simplify`
  - `long_term_perspective`
  - `no_internal_db`
- The constraint object is attached to `final_answer_directive_v1`.
- The same signal is forwarded into Writer-visible directive JSON and advisory summary.
- `must_answer` now prefers the current user turn when explicit latest-turn constraints are active, so stale prior-turn obligation cannot quietly dominate.

## Runtime Touchpoints

- `bot_psychologist/bot_agent/multiagent/latest_turn_constraints.py`
- `bot_psychologist/bot_agent/multiagent/final_answer_directive.py`
- `bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py`
- `bot_psychologist/bot_agent/multiagent/legacy_advisory_sanitizer.py`

## Live Evidence

- Fixture: `TO_DO_LIST/fixtures/PRD-047.29/current_pipeline_simplification_cases_ru.jsonl`
- Runner: `bot_psychologist/tools/run_prd_047_29_current_pipeline_simplification.py`
- Final live result after backend restart on fresh code:
  - `case_count=8`
  - `passed_count=8`
  - `blocked_count=0`
  - `status=passed`

## Key Cases

- `P29-001`: explicit `no_practice` detected, `practice_blocked_by_user_request=true`
- `P29-002`: explicit `no_breathing_only` detected
- `P29-003`: explicit `simplify` detected
- `P29-004`: explicit `long_term_perspective` detected
- `P29-005`: explicit `no_internal_db` detected and Writer-visible KB/semantic-card payload suppressed
- `P29-007`: safety case with phrase `не давай дыхательную практику` now correctly maps to `no_practice`
- `P29-008`: phrase `не своди к дыханию` now correctly maps to `no_breathing_only`

## Conclusion

The current pipeline now hears explicit latest-turn constraints more reliably without introducing a new router, new agent, or parallel runtime path.
