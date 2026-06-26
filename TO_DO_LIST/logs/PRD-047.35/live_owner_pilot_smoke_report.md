# PRD-047.35 Live Owner Pilot Smoke Report

Status: `passed_with_warning`  
Raw artifact: `TO_DO_LIST/logs/PRD-047.35/live_owner_smoke_raw.json`

## Runtime restart

- backend restarted on `:8001`
- backend health passed:
  - `status=healthy`
  - `blocks_loaded=247`
  - `bot_data_base_api=available`
- frontend restart answered `HTTP 200` on `http://127.0.0.1:3000`

## Scenario A - ordinary fear / self-worth

Observed:

- turn 2:
  - `must_answer_source=latest_turn`
  - `answer_shape_profile=ordinary_explanation_compact`
  - `contains_internal_language=false`
  - `hidden_knowledge_competence.reason=latest_turn`
- turn 3:
  - `writer_contact_mode=free_writer_contact`
  - public answer still names one mechanism and what it protects

Result:

- ordinary public answer stayed product-clean
- no DB/chunk/semantic-card language leaked
- Wake-depth principle improved mechanism clarity

## Scenario B - panic helper support

Observed:

- turn 1:
  - `contains_internal_language=false`
  - but answer was too crisis-generic for a spouse-help question
- turn 3:
  - `writer_contact_mode=free_writer_contact`
  - short practical support answer returned

Result:

- no internal-language leak
- later turn recovered into useful support guidance
- first turn remains an honest live-quality warning

## Scenario C - owner diagnostic DB question

Observed:

- turn 1:
  - `must_answer_source=direct_source`
  - `answer_shape_profile=direct_kb_grounded_compact`
  - `writer_payload_count=1`
  - `hidden_knowledge_competence.reason=direct_source_debug`
  - `contains_internal_language=false`
- turn 2:
  - user request to answer normally without base talk succeeded
  - payload returned to `0`

Result:

- owner/debug question still works
- reply stayed specialist-like, not a raw storage/chunk report
- product path remained clean when asked to switch back

## Scenario D - deepening / metaphor / close

Observed:

- turn 1:
  - `answer_shape_profile=adaptive_current_pipeline`
  - `answer_length=2630`
  - too long for the target compact public path
- turn 2:
  - metaphor turn was compact and clean
- turn 3:
  - `close_ack` still carried extra mechanism recap instead of stopping cleanly

Result:

- latest-turn authority remained intact
- compactness is improved but not fully frozen
- remaining debt is shape/closure polish, not internal-language leakage

## Overall conclusion

- all observed turns kept `contains_internal_language=false`
- `hidden_knowledge_competence_v1` was visible in runtime trace throughout the smoke
- PRD-047.35 acceptance passed on hidden-competence / no-internals goals
- final status stays `passed_with_warning` because of bounded answer-shape issues in panic turn 1, deep explanation turn 1, and close turn 3
