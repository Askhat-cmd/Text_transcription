# PRD-047.37 Freeze Summary

Date: 2026-07-02
Status: `accepted_with_warning_candidate`

## Owner Decision
The owner explicitly moved the project out of the immediate hotfix loop and into Cleanup / Freeze / Pilot Start Brief. The accepted product direction is:

- stop adding chaotic narrow fixes by default;
- freeze the current recovered baseline;
- document warnings honestly;
- let the owner run a controlled pilot and collect evidence;
- handle remaining issues through later narrow PRDs only if pilot evidence proves a blocker.

## Current Accepted Runtime Baseline
- Canonical user-facing runtime: `multiagent_adapter / multiagent_v1`.
- Writer remains the final answer author.
- Knowledge-to-Writer path: `writer_kb_payload_v1`.
- Trace is owner/debug observability, not public answer content.
- Semantic cards are advisory-only and Writer-can-ignore.
- Runtime truth and boundary proof use existing trace/debug surfaces, including `runtime_truth_trace_v1`, `runtime_trace_summary_v1`, `source_chunk_match_trace_v1`, and `boundary_trace_v1`.

## Accepted Capabilities
- Latest-turn authority is the main answer target.
- Hidden knowledge competence is active in public user mode.
- Public answers must not mention DB/chunks/cards/trace by default.
- Direct knowledge questions can pull Writer KB Payload.
- Direct concept follow-ups can admit already selected relevant knowledge through minimal hidden Writer payload.
- `no_internal_db` suppresses Writer-visible knowledge and is trace-proven through `boundary_trace_v1`.
- `no_practice` is trace-proven through `boundary_trace_v1` and must suppress practice/homework/step routine pressure.
- Fresh trace/reload works for new Web Chat sessions.
- Old debug traces after backend restart may expire only if explicitly labelled.
- Safety remains above depth, DB, answer style, and user curiosity.

## Accepted Warnings
- Old pre-restart in-memory debug traces can expire after backend restart.
- Greeting/contact wording may sound too therapeutic or mechanized.
- Source exact-match coverage can be weak for concepts not represented by strong DB chunks.
- Shadow planner state may be invalid/noisy while the production answer path is correct.
- Full pytest collection still has historical unrelated `_build_llm_prompts` import debt.
- Some UI trace labels / Session Trace Panel copy still need polish.
- Several exact strategic source-gate root paths from PRD-047.37 are absent locally; local context alternatives were read and recorded in `source_gate.md`.

## Known Blockers
No new PRD-047.37 product blocker was discovered.

The previous POST-HF gate blockers were trace-proof blockers for `no_internal_db` and `no_practice`; PRD-047.36-HF6 reports them repaired through `boundary_trace_v1`. PRD-047.37 intentionally does not rerun the full readiness gate because the owner selected freeze/pilot-start brief over another immediate gate rerun.

## Intentionally Not Fixed Now
- Greeting/contact tone polish.
- Persistent historical debug trace storage across backend restarts.
- Source/DB preparation for weak concept coverage.
- Shadow planner cleanup/noise collapse beyond documentation.
- Historical `_build_llm_prompts` full-suite blocker.
- UI trace label polish.
- Runtime answer-shape tuning.

## Acceptance Position
PRD-047.37 should close as `ACCEPTED_WITH_WARNING` if reports, docs sync, tests, no-mutation proof, and git publication complete. This status is intentional: the project is frozen with known warnings rather than declared perfect.
