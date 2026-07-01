# PRD-047.36-HF4 Turn Number Mapping Report

Date: 2026-07-01

## HF4 result
- Streaming route now computes one `resolved_turn_number` and reuses it for:
  - debug trace save;
  - SSE done payload;
  - history/session persistence.
- Fresh-chat live verification proved:
  - pre-restart turns `1..5` all returned exact `turn_index=N`;
  - post-restart new chat turns `1..2` both returned exact `turn_index=N`.

## Conclusion
- No off-by-one or regenerated numbering remained in the repaired flow.
