# PRD-047.37 Next Recommendation

Date: 2026-07-02
Recommendation: `Option A - Owner Pilot Start`

## Default Next Step
Run owner pilot using:

```text
TO_DO_LIST/logs/PRD-047.37/pilot_start_brief.md
```

The owner should collect evidence across the 12 listed scenarios and classify each issue as blocker or warning using the brief.

## Why Option A First
- The last hotfix chain restored the critical spine: fresh trace/reload, direct concept follow-up payload, and boundary trace proof.
- PRD-047.37 deliberately freezes the system with warnings instead of continuing speculative hotfixes.
- Pilot evidence is now the strongest input for deciding which warning deserves a narrow PRD.

## Alternative Next Options
- Option B - Cleanup Pass 1: docs/logs/trace labels/legacy report hygiene only.
- Option C - DB/Chunk Preparation Strategy: separate source/DB preparation phase based on Wake Up DB Structure.
- Option D - Historical Test Debt: fix `_build_llm_prompts` import blocker if it starts blocking confidence or CI.

## What Not To Do Next
- Do not add dictionary/alias/term-specific rules.
- Do not add a new agent or runtime path.
- Do not mutate Bot_data_base, Chroma, source documents, registry, or processed blocks inside pilot/cleanup work.
- Do not convert warnings into hotfixes without fresh owner evidence.
