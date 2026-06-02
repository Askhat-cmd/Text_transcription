# Prompt Assembly Audit

- target: verify FINAL ANSWER DIRECTIVE authority vs legacy advisory pressure.
- checked_files:
  - bot_psychologist/bot_agent/multiagent/agents/writer_agent_prompts.py
  - bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py
  - bot_psychologist/bot_agent/multiagent/orchestrator.py

Findings:
- FINAL ANSWER DIRECTIVE block exists and is explicit in writer user template.
- Legacy sections remain visible as source signals; wording with imperative markers can still pressure tone/tempo.
- Runtime needs continued truthfulness audit on how LLM interprets advisory labels in live turns.
