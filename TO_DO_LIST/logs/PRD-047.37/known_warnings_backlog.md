# PRD-047.37 Known Warnings And Backlog

Date: 2026-07-02
Status: `accepted_warning_register`

| Issue | Classification | Current Status | Why Not Blocking Pilot | Later Action |
| --- | --- | --- | --- | --- |
| Old debug trace expiry after backend restart | `trace_persistence_candidate`, `warning_not_blocking_pilot` | Accepted warning from HF4/HF6 | Fresh chats must work; old in-memory traces may expire if labelled honestly | Optional persistent debug trace store PRD only if owner wants historical trace recovery |
| Greeting/contact too therapeutic | `UX_polish_candidate`, `warning_not_blocking_pilot` | Known live warning | Does not break trace, boundaries, knowledge delivery, or safety | Pilot evidence first, then compact greeting/contact calibration PRD if repeated |
| Weak source coverage for terms like samorealization | `source_db_preparation_candidate`, `warning_not_blocking_pilot` | Known source coverage risk | Runtime can still answer generally and trace source weakness honestly | Separate DB/chunk preparation strategy PRD |
| Shadow planner invalid/noisy while production path correct | `cleanup_candidate`, `warning_not_blocking_pilot` | Known debug-noise risk | Production path can be correct and trace can label shadow-only noise | Cleanup Pass 1 focused on trace/debug label hygiene |
| Historical `_build_llm_prompts` import blocker | `historical_test_debt` | Full test collection debt | Not caused by PRD-047.37 and historically unrelated | Dedicated historical test debt PRD if CI/confidence becomes blocked |
| Future DB/chunk preparation weakness | `source_db_preparation_candidate` | Deferred architecture phase | PRD-047.37 forbids DB/Chroma/source mutation | DB/Chunk Preparation Strategy after pilot evidence |
| Persistent debug trace store | `trace_persistence_candidate` | Not implemented | Old trace expiry is labelled and fresh trace is the pilot-critical path | Optional future HF only with explicit owner approval |
| UI trace labels / Session Trace Panel polish | `UX_polish_candidate`, `cleanup_candidate` | Known polish debt | Does not alter runtime behavior if exact trace proof remains available | Cleanup Pass 1 docs/UI trace label pass |
| Exact strategic source-gate root docs missing | `cleanup_candidate` | Exact root paths absent; context alternatives exist | Does not block current code baseline; source_gate records truth | Cleanup pass to normalize strategic docs locations/names |
| Full POST-HF rerun skipped | `warning_not_blocking_pilot` | Owner override accepted by PRD-047.37 | Product owner explicitly chose freeze/pilot brief over another immediate gate rerun | Pilot should use `pilot_start_brief.md` and report blocker evidence if found |

## Future HF Trigger Rule
A future hotfix is justified only when pilot evidence shows a hard blocker:

- fresh trace unavailable for new delivered turns;
- `no_internal_db` or `no_practice` boundary behavior/trace regresses;
- direct concept follow-up returns selected knowledge trace-only with payload `0`;
- public answer leaks DB/chunk/card/trace language;
- safety turn becomes unsafe;
- visible answer materially diverges from Writer final answer or saved history.
