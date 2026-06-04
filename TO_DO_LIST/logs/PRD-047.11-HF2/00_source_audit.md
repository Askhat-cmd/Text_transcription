# PRD-047.11-HF2 Source Audit

- generated_at_utc: `2026-06-04T05:30:57.604946+00:00`
- scope: conversation context, retrieval gating, routing, session isolation, persistence, rendering, admin payload

## conversation_context
- `bot_psychologist/bot_agent/multiagent/context_assembly.py` :: present, no direct `conversation_context` match
- `bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py:0` :: conversation_context,

## semantic_hits
- `bot_psychologist/bot_agent/multiagent/writer_context_package.py:0` :: 
- `bot_psychologist/bot_agent/multiagent/live_turn_evidence.py:0` :: 

## contextual_retrieval_gating
- `bot_psychologist/bot_agent/multiagent/dialogue_pragmatics.py:0` :: len(included_hits),
- `bot_psychologist/bot_agent/multiagent/orchestrator.py` :: present, no direct `rag_included_count` match

## knowledge_answer_routing
- `bot_psychologist/bot_agent/multiagent/knowledge_answer_routing_guard.py:0` :: {
- `bot_psychologist/bot_agent/multiagent/final_answer_directive.py:0` :: dict[str, Any],

## session_new_chat_creation
- `bot_psychologist/api/dependencies.py:0` :: Request) -> str:
- `bot_psychologist/api/conversations/repository.py:0` :: str,
- `bot_psychologist/api/conversations/service.py:0` :: str,
- `bot_psychologist/api/routes/chat.py:0` :: str,
- `bot_psychologist/web_ui/src/pages/ChatPage.tsx:0` :: item.session_id,
- `bot_psychologist/web_ui/src/services/api.service.ts:0` :: sessionId,

## persistence_memory_update
- `bot_psychologist/api/routes/users.py:0` :: "user_memory_profile_cleared",
- `bot_psychologist/bot_agent/conversation_memory.py:0` :: 

## web_chat_rendering
- `bot_psychologist/web_ui/src/components/chat/Message.tsx` :: present, no direct `ReactMarkdown` match
- `bot_psychologist/web_ui/src/components/chat/ChatWindow.tsx` :: present, no direct `ReactMarkdown` match

## admin_runtime_effective_payload
- `bot_psychologist/api/admin_routes.py:0` :: FRESH_CHAT_CONTEXT_POLICY_VERSION,
- `bot_psychologist/web_ui/src/components/admin/AdminPanel.tsx:0` :: {runtimeEffectiveData.dialogue_policy?.fresh_chat_context_policy_version ?? 'n/a'}</div>
