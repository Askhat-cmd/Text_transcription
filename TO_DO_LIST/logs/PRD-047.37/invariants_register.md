# PRD-047.37 Invariants Register

Date: 2026-07-02
Status: `freeze_baseline`

## I1 - Latest-turn authority
- status: `accepted`
- proof source: PRD-047.34 implementation report; `docs/PROJECT_STATE.md`; ADR-088.
- what would violate it: answering stale previous tasks when the latest non-empty user turn is a new request and no explicit continuation exists.
- later PRD candidate if regressed: narrow latest-turn authority repair PRD.

## I2 - Writer final authorship
- status: `accepted`
- proof source: ADR-073, ADR-074, ADR-074 Amendment; current runtime baseline.
- what would violate it: runtime/static fallback producing semantic final answers instead of Writer, or planner/DB/card text becoming final answer authority.
- later PRD candidate if regressed: no-stub / Writer authorship quarantine PRD.

## I3 - Hidden knowledge competence
- status: `accepted`
- proof source: PRD-047.35 implementation/live smoke; ADR-089.
- what would violate it: public answer describes internal KB/chunks/cards/trace as the source of competence during ordinary user mode.
- later PRD candidate if regressed: hidden-competence leakage repair PRD.

## I4 - No public DB/chunk/card/trace leak
- status: `accepted`
- proof source: PRD-047.35, PRD-047.36-HF5 live smoke, PRD-047.36-HF6 reports.
- what would violate it: final answer tells the user that it found chunks/cards/trace/DB unless the user explicitly asks an owner/debug/source question.
- later PRD candidate if regressed: public-internal-language leak PRD.

## I5 - Direct concept follow-up knowledge admission
- status: `accepted_with_warning`
- proof source: PRD-047.36-HF5 implementation and live smoke; ADR-094.
- what would violate it: selected relevant concept knowledge remains trace-only with Writer Payload `0` and `grounding_reason=no_clear_retrieval_need` when no hard boundary applies.
- later PRD candidate if regressed: Chunk/Grounding Gate selected-knowledge admission PRD.

## I6 - no_internal_db boundary trace proof
- status: `accepted`
- proof source: PRD-047.36-HF6 implementation/live smoke; ADR-081.
- what would violate it: explicit no-internal-DB latest turn has Writer Payload > 0, semantic cards writer-visible, or missing `boundary_trace_v1.boundary_flags`.
- later PRD candidate if regressed: boundary trace propagation repair PRD.

## I7 - no_practice boundary trace proof
- status: `accepted`
- proof source: PRD-047.36-HF6 implementation/live smoke; ADR-081.
- what would violate it: explicit no-practice latest turn gets homework/exercise/step routine or missing `boundary_trace_v1.boundary_flags`.
- later PRD candidate if regressed: no-practice boundary trace/behavior repair PRD.

## I8 - Fresh trace/reload truth
- status: `accepted_with_warning`
- proof source: PRD-047.36-HF4 implementation/live smoke; ADR-093.
- what would violate it: fresh delivered Web Chat assistant turn shows Trace unavailable or exact trace lookup misses after reload.
- later PRD candidate if regressed: fresh trace/reload restoration PRD.

## I9 - Old trace expiry labelled honestly
- status: `accepted_with_warning`
- proof source: PRD-047.36-HF4 and HF6 reports.
- what would violate it: old pre-restart missing trace is presented as fresh failure, silently hidden, or mislabeled without `debug_trace_expired_after_backend_restart` / legacy reason.
- later PRD candidate if regressed: trace availability labelling PRD; persistent trace store only if explicitly approved.

## I10 - Safety floor over depth/DB/style
- status: `accepted_with_warning`
- proof source: POST-HF G8 pass_with_warning; existing safety policy.
- what would violate it: acute panic/safety turn gets deep philosophy, diagnosis, spiritual authority, or misses medical escalation boundaries.
- later PRD candidate if regressed: safety floor calibration PRD.

## I11 - Semantic cards advisory-only
- status: `accepted`
- proof source: PRD-047.27, PRD-047.36-HF5, ADR-085.
- what would violate it: semantic cards become hard authority, route selector, final answer source, or override Writer/safety/user boundaries.
- later PRD candidate if regressed: semantic-card authority rollback PRD.

## I12 - No dictionary / no alias route / no rule-engine sprawl
- status: `accepted`
- proof source: PRD-047.28 through PRD-047.36-HF6 non-goals; PRD-047.37 hard non-goals.
- what would violate it: adding term-specific if/else routes, alias maps, runtime dictionaries, or a parallel rule-engine to fix concept cases.
- later PRD candidate if regressed: anti-overengineering cleanup PRD.
