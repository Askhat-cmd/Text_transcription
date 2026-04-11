# PRD-010 — Final Fix: Web Chat answer de-truncation

Version: 1.0.0
Date: 2026-04-12
Status: In Progress
Owner: Codex

## Context
User reports that in Web UI chat answers are still truncated, while LLM canvas/trace shows longer continuation.

Direct evidence from runtime data:
- Latest turn in `bot_sessions.db` (`session_id=9633c268-ae3f-44a9-ad6e-ffd6a33b7e53`) stores `bot_response` length ~263 chars.
- Trace indicates completion tokens much higher (`~355`), meaning raw model output is significantly longer than final chat output.

## Root cause hypothesis
Primary truncation happens in backend formatting layer, not only in SSE/web parser:
- `bot_agent/response/response_formatter.py`
- For non-informational mode, formatter auto-applies sentence cap based on user message length.
- For short validation queries this collapses to 2 sentences, which can cut practical tail and create "abrupt" ending.

## Goal
Ensure default Web coaching answers are not auto-shortened by formatter and are delivered fully to chat message.

## Non-goals
- No commit/push in this cycle (local verification only)
- No Telegram adapter changes

## Required changes
1. Formatter policy
- Disable automatic sentence cap by default.
- Keep compact mode only when user explicitly asks for brevity (`кратко/коротко/...`).

2. Tests
- Update formatter tests to reflect new default behavior.
- Add regression test: short validation query should keep multi-sentence answer unless explicit brevity intent.

3. Verification
- Run formatter test file.
- Run targeted SSE service tests to ensure no regression in stream assembly contract.
- Run local runtime check for representative query and confirm persisted `bot_response` length is not collapsed to short fragment.

## Acceptance criteria
- `ResponseFormatter` no longer truncates regular validation responses to 2 sentences by default.
- Test suite for formatter passes with new behavior.
- Web chat result for the same query is materially longer and complete (no abrupt tail like "...сделай ").
