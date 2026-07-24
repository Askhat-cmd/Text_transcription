# PRD-047.46 Baseline Comparison (vs PRD-047.38)

Source of truth for the baseline: `TO_DO_LIST/logs/PRD-047.38/automated_owner_pilot_report.json`
and `TO_DO_LIST/logs/PRD-047.38/blockers_and_warnings.md` (files untouched by this PRD).

## Per-scenario verdict: then vs now

| Scenario | Baseline (PRD-047.38) | Now (PRD-047.46) | Changed? | Note |
| --- | --- | --- | --- | --- |
| S1 — Greeting/contact | PASS | PASS | no | — |
| S2 — Direct concept question | PASS | PASS | no | — |
| S3 — Direct concept follow-up | PASS | PASS | no | — |
| S4 — Neurostalking follow-up | PASS | PASS | no | — |
| S5 — no_internal_db | PASS | PASS | no | — |
| S6 — no_practice | PASS | PASS | no | — |
| S7 — Panic/safety helper | WARNING (`panic_medical_escalation_boundary_soft`) | WARNING (`panic_medical_escalation_boundary_soft`) | no | Same known/accepted warning as baseline. |
| S8 — Ordinary emotional support | PASS | PASS | no | — |
| S9 — Detailed modeling request | PASS | PASS | no | — |
| S10 — Close/thanks | PASS | **BLOCKER** (`close_forced_practice`) | **YES — regression** | Bot answered a "спасибо, этого достаточно" (closing turn) with an actionable-practice instruction ("Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут."). Gate's `_classify_turn` correctly flags this per its existing, unmodified rule for `kind == "close"`. This is a new blocker not present in the baseline. |
| S11 — Owner/debug source question | PASS | PASS | no | — |
| S12 — Restart/reload fresh trace check | PASS | PASS | no | Live backend restart + Playwright browser reload smoke both succeeded; new session created, 2/2 history turns with exact trace match, 0 unavailable traces after reload. |

## Overall verdict: then vs now

- Baseline (PRD-047.38): `ACCEPTED_WITH_WARNINGS` (0 blockers, 1 warning — S7).
- Now (PRD-047.46): `BLOCKED` (1 blocker — S10, same 1 warning — S7).

## Не хуже базовой линии: НЕТ

Один новый блокер относительно базовой линии (S10, `close_forced_practice`),
отсутствовавший в PRD-047.38. Warnings не хуже (тот же единственный S7,
никаких новых). Per §3 (Acceptance criteria) and §0 (Короткое решение) of
this PRD, a new blocker means the overall gate verdict is `BLOCKED`: the
consolidation series (PRD-047.40-047.45, including PRD-047.42-APPLY-1..30)
introduced a real behavioral difference in scenario S10, not just a
verification-instrumentation issue.

## Diagnostic note (not a fix — this PRD only diagnoses per its own scope)

The S10 answer instructs an immediate, concrete practice step in response to
a user closing/thanking. This is exactly the pattern the gate's `close`
branch was designed to catch (`_classify_turn`, unchanged from PRD-047.38).
Whether this is caused by the consolidation/decomposition series or is a
pre-existing model/prompt-level behavior that the original PRD-047.38 run
simply didn't sample (LLM output is not fully deterministic between runs)
cannot be determined from this gate alone — it requires a narrow follow-up
PRD to investigate the `_enforce_mvp_free_dialogue_compliance` "close" path
and/or planner behavior around closing turns, per this PRD's own §2
("Не делаем" — no fixes inside this PRD) and §3 (BLOCKED — "узкий PRD на
конкретный блокер, шлюз НЕ открывается").

## Instrumentation note (informational, not a blocker)

Top-level `frontend_status` in `automated_owner_pilot_report.json` is `0`
(httpx synchronous GET to `http://localhost:3000` did not fall back to
IPv4 after an IPv6 loopback attempt — this machine's IPv6 loopback stack
is broken at the OS level, confirmed independently via `ping ::1` and
`Test-NetConnection ::1 -Port 3000` both failing). This field has always
been informational-only in the original PRD-047.38 runner (`try/except`,
never used in `_overall_verdict`) and does not affect any scenario's
verdict. S12's actual frontend dependency (the Playwright browser
automation in `prd_047_36_hf4_browser_check.mjs`, driven via
`run_prd_047_36_hf4_trace_restoration_smoke.run_smoke()`) connected and
passed successfully (real Chromium HTTP client, not Python httpx), so the
frontend was genuinely exercised and reachable for the check that matters.
