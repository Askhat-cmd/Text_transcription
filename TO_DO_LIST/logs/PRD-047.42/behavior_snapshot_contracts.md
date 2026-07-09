# PRD-047.42 Behavior Snapshot Contracts

- note: these are representative read-only contract snapshots, not exhaustive answer-quality coverage.

```json
{
  "writer_contract": {
    "keys_present": [
      "fresh_chat_context_policy_version",
      "writer_context_package_version",
      "writer_grounding_visibility_v1",
      "response_planner_next_move",
      "answer_obligation",
      "final_answer_writer_contact_mode",
      "retrieval_action"
    ],
    "response_planner_next_move": "answer_known_concept",
    "answer_obligation": "answer_knowledge_question",
    "semantic_hits_count": 0,
    "semantic_hits_preview": [],
    "fresh_chat_active_context_source": "current_chat_runtime_scope",
    "writer_contact_mode": "structured_answer",
    "retrieval_action": "include_rag",
    "writer_grounding_authority_note": "Safety and the explicit latest user request are mandatory. Conversation context supports continuity. KB, semantic cards, retrieval notes, and diagnostic hints are optional grounding: use them only if they help the current answer, never let them change the user's request, and do not sound like internal recitation. Treat internal knowledge as hidden competence: do not talk about the base, chunks, semantic cards, uploaded materials, or system internals in the user-facing answer. Speak from understanding, name one main mechanism, show what it protects, and offer at most one next question or step only when it truly helps."
  },
  "writer_agent_runtime_settings": {
    "safe_guided": {
      "model": "gpt-4o-mini",
      "timeout": 11.5,
      "max_tokens": 700,
      "temperature": 0.42
    },
    "mvp_free_dialogue": {
      "model": "gpt-4o-mini",
      "timeout": 11.5,
      "max_tokens": 2500,
      "temperature": 0.42
    }
  },
  "writer_agent_compliance": {
    "literal_markdown_echo": "**Заголовок**\n\n- пункт один\n- пункт два",
    "literal_markdown_shape": "sanitized_direct_no_forced_practice",
    "no_practice_contact": "Понял. Тебе тяжело",
    "no_practice_shape": "sanitized_direct_no_forced_practice"
  },
  "admin_routes": {
    "runtime_effective": {
      "schema_version": "10.5.1",
      "active_runtime": "multiagent",
      "pipeline_mode": "multiagent_only",
      "effective_config_flag_count": 103,
      "dialogue_policy_version": "unified_dialogue_policy_v2"
    },
    "orchestrator_config": {
      "pipeline_mode": "multiagent_only",
      "runtime_entrypoint": "multiagent_adapter",
      "legacy_cascade_status": "physically_removed"
    },
    "deprecated_prompt_stack_usage": {
      "status_code": 410,
      "detail": "Prompt stack usage endpoint deprecated. Prompt stack usage is no longer provided by admin API."
    }
  }
}
```
