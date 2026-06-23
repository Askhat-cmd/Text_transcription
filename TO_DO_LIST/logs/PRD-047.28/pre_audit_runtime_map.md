# PRD-047.28 Pre-Audit Runtime Map

Generated before implementation to map the current production-like path and isolate the experiment.

## Source Gate Notes

- Present and reviewed:
  - `docs/PROJECT_STATE.md`
  - `docs/ROADMAP.md`
  - `docs/PRD_INDEX.md`
  - `docs/DECISIONS.md`
  - `TO_DO_LIST/context/WAKE_UP_DB_STRUCTURE_ADAPTED_FOR_NEO_MindBot_PRD_Reference_RU_v1.1.md`
  - prior PRD reports/logs for `PRD-047.25`, `PRD-047.26`, `PRD-047.27`
- Not found in repository during intake:
  - `STRATEGIC_PLAN_NEO_MindBot_Thin_Spine_Recovery_RU_v1.md`
  - `TRANSFER_BRIEF_Bot_Psychologist_Neo_MindBot_AFTER_THIN_SPINE_STRATEGY_RU.md`
  - `STRATEGIC_PLAN_NEO_MindBot_Anti_Overengineering_Live_Core_v2_RU.md`
  - `TRANSFER_BRIEF_Bot_Psychologist_Neo_MindBot_AFTER_PRD-047.25_DETAILED_RU.md`

## Canonical Current Full Pipeline Entrypoint

- API app entrypoint: `bot_psychologist/api/main.py`
- Canonical adaptive route: `bot_psychologist/api/routes/chat.py`
- Active runtime adapter: `bot_psychologist/bot_agent/multiagent/runtime_adapter.py`
- Runtime entrypoint asserted in admin/docs/trace: `multiagent_adapter`
- Core orchestration path: `bot_psychologist/bot_agent/multiagent/orchestrator.py`

## Writer Prompt / Writer Call Layer

- Writer agent implementation: `bot_psychologist/bot_agent/multiagent/agents/writer_agent.py`
- Writer prompt templates/assembly: `bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py`
- Writer contract shape: `bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py`
- Writer is invoked from the orchestrator after context/policy assembly and before validator/final acceptance.

## Canonical KB Path

- Canonical Writer KB payload module: `bot_psychologist/bot_agent/multiagent/writer_kb_payload.py`
- Existing prompt integration tests:
  - `bot_psychologist/tests/multiagent/test_writer_kb_payload.py`
  - `bot_psychologist/tests/multiagent/test_writer_kb_payload_prompt_integration.py`
  - `bot_psychologist/tests/api/test_writer_kb_payload_live_http_path.py`

## Canonical Retrieval Query Path

- Current-turn retrieval builder: `bot_psychologist/bot_agent/multiagent/retrieval_query_builder.py`
- Hybrid/query-before-RAG plumbing lives in:
  - `bot_psychologist/bot_agent/multiagent/contextual_retrieval_query_composer.py`
  - `bot_psychologist/bot_agent/multiagent/hybrid_retrieval_planner.py`
  - `bot_psychologist/bot_agent/multiagent/orchestrator.py`
- Current runtime docs identify `current_turn_focus_v1` as canonical retrieval assembly.

## Overlay / Semantic Cards / Diagnostic Center Integration Points

- Overlay shadow trace: `bot_psychologist/bot_agent/multiagent/overlay_shadow_trace.py`
- Semantic card loader/adapter:
  - `bot_psychologist/bot_agent/knowledge/semantic_card_loader.py`
  - `bot_psychologist/bot_agent/knowledge/semantic_card_payload_adapter.py`
- Semantic card pack:
  - `bot_psychologist/knowledge_packs/semantic_cards_pilot_v1/cards.json`
- Diagnostic Center runtime/admin surface:
  - `bot_psychologist/bot_agent/diagnostic_center_control.py`
  - `bot_psychologist/api/admin_routes.py`
  - advisory integrations inside `bot_psychologist/bot_agent/multiagent/orchestrator.py`

## Existing Eval / Smoke / Live Runner Surfaces

- `bot_psychologist/tools/prd_047_27_semantic_cards_pilot.py`
- `bot_psychologist/tools/run_prd_047_27_hf2_owner_web_chat_parity.py`
- `bot_psychologist/scripts/run_quality_baseline.py`
- Related tests already cover runtime trace, payload, overlay, and retrieval contracts.

## Compatibility / Fallback Paths Still Present

- `legacy_fallback_used` / compatibility metadata is still exposed by `runtime_adapter.py`
- Old admin/runtime compatibility surfaces remain referenced in docs and admin types
- Legacy fallback behavior around writer payload/query assembly remains visible as compatibility-only and must not be changed in this PRD

## Retirement Candidates For Later PRD, Not This One

- `overlay_shadow_trace`
- `semantic_cards_pilot_v1`
- Diagnostic Center advisory visibility/control surfaces that add trace noise
- heavy dialogue act / answer obligation layering if thin-spine evidence proves simpler alternatives
- stale compatibility metadata / fallback surfaces around `legacy_fallback_used`
- noisy trace surfaces that duplicate the same runtime truth in multiple places

## PRD-047.28 Implementation Boundary

- The experiment must be added as isolated offline/CLI/eval code.
- The current web/manual runtime path must remain unchanged.
- Variant A should call the existing supported runtime adapter when possible.
- Variants B/C must not hook into live UI or become a runtime toggle.
