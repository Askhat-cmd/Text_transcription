# Chat 11 Evidence Audit

## Observed Owner Symptoms
- After page reload, some delivered assistant turns still showed trace/canvas, while some visible assistant turns showed no trace block at all.
- The failure mode was no longer "wrong trace under wrong bubble"; HF1 already removed that drift class.
- The residual class was "visible answer exists, but no exact trace can be recovered or displayed for that turn".

## Key Evidence Used
- Mixed trace presence across reloaded turns in `ЧАТ_С_БОТОМ_11.txt`.
- Prior HF1 repair already bound trace lookup to explicit `turn_number`.
- Current frontend hook suppressed mismatched trace rendering, which prevented wrong canvas but left a silent missing-state.

## HF3 Classification
- Confirmed root class: owner/debug observability gap, not Writer quality regression.
- Primary defects repaired in HF3:
  - exact turn lookup could silently fall back to latest trace;
  - store lookup could search beyond the requested candidate session scope;
  - frontend suppressed the mismatch/missing state without a visible owner/debug reason.
- Separate bounded note: `memory_written.assistant=""` can still happen when answer saving is quarantined by acceptance logic; that is classified in `memory_written_timing_report.md`, not treated as the main HF3 trace-availability defect.
