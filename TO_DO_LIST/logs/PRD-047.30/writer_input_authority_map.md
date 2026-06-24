# PRD-047.30 Writer Input Authority Map

Date: 2026-06-24
Status: pre_code_audit_completed

| Input block | Source file | Reaches Writer prompt? | Authority level | Can Writer ignore? | Duplicates | Action in PRD-047.30 |
| --- | --- | --- | --- | --- | --- | --- |
| Safety floor | `bot_psychologist/bot_agent/multiagent/final_answer_directive.py` + writer system prompt | Yes | MUST_OBEY | No | Low | Keep mandatory and above every other layer. |
| `latest_turn_constraints_v1` | `bot_psychologist/bot_agent/multiagent/latest_turn_constraints.py` -> `final_answer_directive.py` -> `writer_contract.py` | Yes | MUST_OBEY | No | Medium with legacy advisory wording | Keep authoritative; do not duplicate the same constraint in long advisory text. |
| Latest user message / `must_answer` | `final_answer_directive.py` -> `writer_contract.py` | Yes | MUST_OBEY | No | Low | Keep as primary answer target. |
| Compact conversation context | `context_assembly.py` -> `writer_contract.py` | Yes | CONTEXT | Mostly no, but only as continuity support | Low | Keep compact and supportive. |
| Writer KB payload | `writer_context_package.py` + `writer_kb_payload.py` | Yes | OPTIONAL_GROUNDING | Yes | Medium with retrieval context and knowledge routing hints | Throttle on non-KB/support/repair/simplify/pushback turns; keep for direct KB/source/concept asks. |
| Semantic cards | `semantic_card_payload_adapter.py` -> `writer_context_package.py` | Yes | OPTIONAL_GROUNDING | Yes | Medium with KB payload and advisory summaries | Make trace-only on non-KB/support/repair/simplify/pushback turns; keep optional on grounded knowledge turns. |
| Diagnostic hints / writer move hints | `diagnostic_center.py` -> `legacy_advisory_sanitizer.py` -> `writer_contract.py` | Yes | OPTIONAL_GROUNDING | Yes | High with final directive and active line | Keep short contextual hints only; avoid command-like repetition. |
| Retrieval context chunks | `writer_context_package.py` -> `writer_contract.py` | Yes | OPTIONAL_GROUNDING | Yes | High with Writer KB payload | Gate with same visibility decision as Writer KB payload. |
| Retrieval query composer metadata | `contextual_retrieval_query_composer.py` -> `writer_contract.py` | Yes | CONTEXT | Yes | Medium | Keep compact metadata; use as signal for visibility decision, not as answer authority. |
| Overlay shadow | `overlay_shadow_trace.py` -> `orchestrator.py` debug only | No in prompt | TRACE_ONLY | Yes | None | Keep trace-only. |
| Knowledge policy trace / semantic hit debug detail | `knowledge_policy.py` -> `orchestrator.py` debug only | No in prompt | TRACE_ONLY | Yes | None | Keep as governance/debug only. |
| Legacy advisory summary | `legacy_advisory_sanitizer.py` -> `writer_contract.py` | Yes | REMOVE_LATER_CANDIDATE | Yes | High with final directive, practice note, active line | Collapse to short non-duplicating summary; keep detail in trace and directive JSON. |

## Conflicts Found

- `latest_turn_constraints_v1` is authoritative, but `legacy_advisory_sanitizer.py` still rephrases overlapping practice/simplify/no-internal-db guidance in long prose.
- `writer_kb_payload` and `retrieval_context["chunks"]` both expose grounding to Writer even when the turn is ordinary emotional/support text.
- semantic cards are advisory-only by design, but on non-KB turns they still enrich Writer-visible payload instead of staying trace-only.

## Audit Conclusion

- `knowledge_policy.py` is already the correct chunk governance gate.
- The remaining problem is not unsafe chunk admission; it is Writer-visible packaging authority after the chunks are already deemed safe.
- PRD-047.30 should therefore change `writer_context_package.py`, prompt assembly in `writer_contract.py` / `writer_agent_prompts.py`, and duplicate advisory compression in `legacy_advisory_sanitizer.py`, without adding a new planner or route.
