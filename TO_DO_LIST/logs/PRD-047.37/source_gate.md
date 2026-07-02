# PRD-047.37 Source Gate

Date: 2026-07-02
Status: `completed_with_missing_optional_context`

## PRD Input
- Pulled `origin/main` fast-forward to `1f99ac54fb94d6c046b65c552b63146fa06593fc`.
- Read `TO_DO_LIST/PRD-047.37_Cleanup_Freeze_Pilot_Start_Brief_RU.md`.

## Required HF / Gate Sources
- `TO_DO_LIST/PRD-047.36-HF4_Trace_Restoration_Hard_Blocker_Owner_Web_Verification_RU.md` - read.
- `TO_DO_LIST/logs/PRD-047.36-HF4/implementation_report.md` - read.
- `TO_DO_LIST/logs/PRD-047.36-HF4/live_smoke_report.md` - read.
- `TO_DO_LIST/PRD-047.36-HF5_Direct_Concept_Followup_KB_Visibility_RU.md` - read.
- `TO_DO_LIST/logs/PRD-047.36-HF5/implementation_report.md` - read.
- `TO_DO_LIST/logs/PRD-047.36-HF5/live_smoke_report.md` - read.
- `TO_DO_LIST/PRD-047.36-HF6_No_Internal_DB_No_Practice_Boundary_Trace_Integrity_RU.md` - read.
- `TO_DO_LIST/logs/PRD-047.36-HF6/implementation_report.md` - read.
- `TO_DO_LIST/logs/PRD-047.36-HF6/live_smoke_report.md` - read.
- `TO_DO_LIST/logs/PRD-047.36-HF6/next_recommendation.md` - read.
- `TO_DO_LIST/PRD-047.36-POST-HF_Owner_Readiness_Gate_RU.md` - read.
- `TO_DO_LIST/logs/PRD-047.36-POST-HF/readiness_gate_report.md` - read.
- `TO_DO_LIST/logs/PRD-047.36-POST-HF/boundary_preservation_report.md` - read.

## Required Strategic Docs
- `docs/PROJECT_STATE.md` - read.
- `docs/ROADMAP.md` - read.
- `docs/PRD_INDEX.md` - read.
- `docs/DECISIONS.md` - read.

## Exact Paths Missing From PRD Source Gate
- `STRATEGIC_PLAN_NEO_MindBot_Post_PRD_047_35_Product_Simplicity_Retrieval_Reliability_RU_v2.md`
- `STRATEGIC_PLAN_NEO_MindBot_Thin_Spine_Recovery_RU_v1.md`
- `TRANSFER_BRIEF_Bot_Psychologist_Neo_MindBot_AFTER_THIN_SPINE_STRATEGY_RU.md`
- `WAKE_UP_DB_STRUCTURE_ADAPTED_FOR_NEO_MindBot_PRD_Reference_RU_v1.1.md`
- `TO_DO_LIST/context/Рекомендации для архитектора_2.txt`

## Local Context Alternatives Read
- `TO_DO_LIST/context/WAKE_UP_DB_STRUCTURE_ADAPTED_FOR_NEO_MindBot_PRD_Reference_RU_v1.1.md`
- `TO_DO_LIST/context/STRATEGIC_PLAN_NEO_MindBot_Anti_Overengineering_Live_Core_v2_RU (1).md`
- `TO_DO_LIST/context/TRANSFER_BRIEF_Bot_Psychologist_Neo_MindBot_AFTER_STRATEGIC_PLAN_PRD-047.15-HF2_DETAILED_RU.md`
- `TO_DO_LIST/context/ЧАТ_С_БОТОМ_13.txt` was confirmed present and treated as private local context only.
- `TO_DO_LIST/context/Рекомендации для архитектора.txt` is present, but the exact `_2` file requested by PRD is missing.

## Baseline Extracted
- Canonical user-facing runtime remains `multiagent_adapter / multiagent_v1`.
- Writer remains final answer author.
- `writer_kb_payload_v1` is the accepted knowledge-to-Writer path.
- Trace is owner/debug observability, not public answer content.
- Semantic cards are advisory-only and Writer-can-ignore.
- HF4 restored fresh Web Chat trace/reload truth, with old pre-restart debug trace expiry accepted when labelled honestly.
- HF5 restored direct concept follow-up selected-knowledge admission.
- HF6 restored stable `boundary_trace_v1` proof for `no_internal_db` and `no_practice`.
- POST-HF gate before HF6 was blocked by missing boundary trace flags, now addressed by HF6.

## Known Warnings Carried Into PRD-047.37
- Old debug traces after backend restart may expire if explicitly labelled.
- Greeting/contact wording can be too therapeutic or mechanized.
- Source exact-match coverage can be weak for concepts not represented by strong DB chunks.
- Shadow planner may be invalid/noisy while production path is correct.
- Full pytest still has historical unrelated `_build_llm_prompts` import blocker.
- UI trace labels / Session Trace Panel polish may still be needed.

## Hard Scope Boundary
PRD-047.37 is a freeze/documentation/pilot-start brief. It must not add a runtime path, new agent, dictionary, alias map, Writer style retune, DB/Chroma/source mutation, persistent trace store, or another hotfix.
