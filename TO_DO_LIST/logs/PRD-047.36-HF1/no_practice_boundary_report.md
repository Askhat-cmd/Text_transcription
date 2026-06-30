# No-Practice Boundary Report

## Repair
- `writer_agent.py` now routes one-step fallback through a bounded resolver instead of blindly returning the canned `5 минут` instruction.
- When latest-turn constraints/contact mode make canned practice disallowed, Writer now keeps a sanitized direct answer or falls back to a short no-practice explanation.
- Greeting retry and gentle-close retry were also narrowed so they do not reopen practice/continuation drift.

## Outcome
- Explicit no-practice turns no longer collapse into forced micro-step output on the compliance layer.
- Existing retry/quarantine behavior for real bad answers remains intact.
