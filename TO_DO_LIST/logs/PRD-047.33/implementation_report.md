# Implementation Report - PRD-047.33

Date: 2026-06-25
Status: passed_with_warning

## Scope completed
- created `PRD-047.33_TASK_LIST.md` and executed the required source gate;
- audited answer-shape controls across dialogue policy, final directive, writer contract/prompt, writer grounding visibility, runtime trace summary, and owner trace surfaces;
- calibrated answer-shape guidance inside the existing pipeline only;
- preserved explicit practice, no-practice, no-internal-db, direct KB/source, and runtime-truth boundaries;
- created required PRD evidence artifacts and updated project docs.

## Code changes
- `dialogue_policy.py`
  - tightened compact support target length from `600_1400` to `450_1100`
  - added extra human-like soft controls for direct answer first, single main mechanism, and bounded list size
- `final_answer_directive.py`
  - introduced soft `answer_shape_profile` selection with profile notes
  - added ordinary/support/direct/practice/no-internal-db/direct-source compact profiles
  - hardened direct-source detection for live source-request phrasing
  - preserved no-internal-db priority over source-grounded mode
- `writer_contract.py`, `writer_agent_prompts.py`, `writer_agent.py`
  - surfaced selected answer-shape profile into Writer prompt assembly
  - clarified that ordinary support/explanation turns should not default to a teaching article
- `legacy_advisory_sanitizer.py`, `runtime_trace_summary.py`
  - exposed selected profile and notes in Writer-visible and runtime-trace surfaces
- `response_planner.py`
  - tightened anti-lecture wording for mechanism-heavy ordinary answers
- tests
  - added `tests/test_prd_047_33_answer_shape_calibration.py`
  - extended existing prompt/verbosity coverage

## Outcome
- direct KB/source path now traces as `direct_kb_grounded_compact` in live owner smoke;
- no-internal-db still keeps Writer payload `0`;
- explicit practice still routes to one bounded practice with narrow payload;
- runtime truth trace remains honest and owner-visible;
- ordinary answers are shorter and less methodical overall, but one live resistance case still reports `adaptive_current_pipeline` in trace even after the answer itself improved.

## Honest warning
- PRD-047.33 is not blocked, but it is not a perfect shape-classification closure:
  - case B improved in answer quality and no longer triggers the simple methodical heuristic;
  - the trace profile for that case still does not resolve to the intended ordinary compact profile;
  - because of that residual mismatch, final status is `passed_with_warning`, not `passed`.
