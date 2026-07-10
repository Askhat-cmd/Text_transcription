# PRD-047.42-APPLY-4 Next Recommendation

- Recommendation: continue `writer_agent.py` with the smallest remaining non-giant class slice before touching `_call_llm` or `_enforce_answer_compliance`.
- Best next candidate: a narrow PRD around `write()` plus `_resolve_runtime_settings()` only if their call graph can be snapshot-guarded cleanly.
- Alternative: pause the `writer_agent.py` track and execute deferred `PRD-047.42b` for the `19` production `diagnostic_center_*` files if the goal is to keep cutting the safest independently structured god-file family first.
- Non-recommendation: do not jump directly to `_call_llm`, `writer_contract.to_prompt_context`, or broad suite-health cleanup inside this PRD chain.
