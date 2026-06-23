# PRD-047.29 Practice Pushback Repair Report

Status: passed
Date: 2026-06-23

## What Changed

- Explicit no-practice phrasing is now promoted into `latest_turn_constraints_v1.no_practice`.
- `final_answer_directive_v1` hardens this into `practice_policy=forbidden_explicit_latest_turn`.
- Writer-visible sanitized directive now carries the same constraint.
- Writer-visible practice instruction becomes `no_exercise_but_answer_normally`.

## Important Boundary

This is a hard stop for new practice in the answer, not a new routing engine.

## Covered Phrases

- `не давай практику`
- `не давай дыхательную практику`
- `не хочу практику`
- `без практик`
- `не предлагай упражнение`

## Evidence

- Unit coverage:
  - `tests/test_prd_047_29_latest_turn_constraints.py`
  - `tests/test_prd_047_29_writer_payload_and_contract.py`
- Live smoke:
  - `P29-001` passed
  - `P29-007` passed

## Outcome

The final runtime summary now truthfully reports `practice_blocked_by_user_request=true` on explicit pushback turns.
