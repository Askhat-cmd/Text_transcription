# PRD-047.15-HF1 LLM / Hybrid Decision Brief

- recommendation: `build_hybrid_llm_assist_for_low_confidence_cases`
- cases_total: `40`
- automated_expected_match_rate: `0.825`
- llm_candidate_cases_count: `8`

## Option A - Heuristic-only Composer
- Description: Current deterministic v1 with rule improvements.
- Pros: predictable, cheap, no latency, easy to test, stable trace, low risk of hallucinated retrieval intent, no extra provider dependency
- Cons: brittle on subtle context, needs many rules, weak on ambiguous mixed cases, may miss implicit user intent, manual maintenance grows over time
- Best use: clear routing, summary suppression, greetings/close/support, obvious knowledge questions, obvious short follow-up with strong last offer

## Option B - Hybrid Heuristics + LLM-assisted Composer
- Description: Heuristics handle high-confidence cases; LLM is called only for ambiguous/mixed/low-confidence cases.
- Pros: keeps deterministic safety for simple cases, improves ambiguous context, controls cost/latency, allows better query rewriting, can output structured JSON only, easier to gate than LLM-first
- Cons: more complex architecture, needs JSON validation, needs timeout/fallback, must prevent user-facing text, needs cost/latency monitoring, possible model drift
- Best use: mixed cases, implicit topic shifts, weak inherited topic, query rewrite, KB vs memory decision

## Option C - LLM-first Composer
- Description: LLM decides retrieval need/query/inclusion for most turns.
- Pros: highest flexibility, better semantic interpretation, fewer brittle rules, can understand complex implicit context
- Cons: higher cost, higher latency, less deterministic, harder to test, possible hallucinated query, provider dependency, more safety/validation required, may become hidden authority over Writer
- Best use: only after trace evidence proves deterministic/hybrid insufficient

## Future Hybrid Architecture Sketch
- Deterministic Composer pre-pass.
- High-confidence cases stay heuristic-only.
- Low-confidence/mixed cases may call a future metadata-only LLM composer.
- Strict JSON validation and no-user-facing-text gate are mandatory.
- Writer remains the only final answer author.
