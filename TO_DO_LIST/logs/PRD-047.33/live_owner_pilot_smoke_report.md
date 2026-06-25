# Live Owner Pilot Smoke Report - PRD-047.33

Date: 2026-06-25
Status: passed_with_warning
Backend health: `healthy`, `blocks_loaded=247`, `bot_data_base_api=available`
Frontend: restarted on `http://localhost:3000/`

## Smoke Matrix
| Scenario | Answer length | Selected profile | Writer payload | Runtime truth trace | Methodical note | Result |
| --- | ---: | --- | ---: | --- | --- | --- |
| A Greeting | 84 | `contact_brief` | 0 | yes | no warning | pass |
| B Resistance | 878 | `adaptive_current_pipeline` | 0 | yes | heuristic clean, but trace profile still not compact-tagged | warning |
| C Anger boss | 747 | `concrete_situation_compact` | 0 | yes | no warning | pass |
| D Long-term practice | 661 | `bounded_practice` | 1 | yes | one bounded practice preserved, but answer still list-shaped | warning |
| E No-practice explanation | 644 | `ordinary_explanation_compact` | 0 | yes | no practice leak, but one short list remains | warning |
| F No internal DB | 1031 | `no_internal_db_compact` | 0 | yes | payload suppression preserved, but one list remains | warning |
| G Direct KB/source | 1405 | `direct_kb_grounded_compact` | 2 | yes | grounded path preserved; still slightly over soft target | warning |
| H Simple support | 463 | `ordinary_explanation_compact` | 0 | yes | no warning | pass |

## Main findings
- direct KB/source path is fixed and now traces as `direct_kb_grounded_compact`;
- explicit practice path remains bounded and keeps narrow payload `1`;
- no-internal-db remains Writer payload `0`;
- runtime truth trace remains honest across all A-H cases;
- residual warning remains on ordinary explanation case B:
  - answer is shorter and less lecture-like than before;
  - trace still reports `adaptive_current_pipeline` instead of the intended compact ordinary-explanation profile.

## Artifact
- raw machine-readable output: `TO_DO_LIST/logs/PRD-047.33/live_owner_pilot_raw.json`
