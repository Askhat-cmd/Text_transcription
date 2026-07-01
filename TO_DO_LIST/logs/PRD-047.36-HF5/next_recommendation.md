# PRD-047.36-HF5 Next Recommendation

Date: 2026-07-01
Current status: `accepted_with_warning`

## Recommended next step
Re-run a shortened owner readiness gate on top of HF4 + HF5 with these fixed scenarios:
- fresh trace restoration / reload truth from HF4
- direct concept follow-up from HF5
- `no_internal_db` preservation
- `no_practice` preservation
- one safety scenario

## What not to do next
- do not add a dictionary or alias map for concept words
- do not mutate DB/Chroma/source coverage inside the runtime fix stream
- do not broaden semantic-card authority

## Separate later only if needed
If owner review still finds weak concept coverage for terms that are not truly present in the current source base, open a separate source/DB preparation PRD instead of extending HF5 runtime heuristics.

