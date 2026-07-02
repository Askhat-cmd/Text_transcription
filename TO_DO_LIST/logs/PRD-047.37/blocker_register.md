# PRD-047.37 Blocker Register

Date: 2026-07-02
Status: `no_new_blocker_found`

## Active Blockers
None found during PRD-047.37 documentation/freeze work.

## Non-Blocking Warnings Recorded
- Optional sanity check not run as a full runtime gate because PRD-047.37 is a freeze/pilot brief and the owner explicitly moved beyond immediate rerun-gate mode.
- Exact strategic source-gate root paths are missing, with local context alternatives recorded in `source_gate.md`.
- Old trace expiry after backend restart remains accepted warning.
- Greeting/contact wording and UI trace labels remain polish backlog.
- Historical `_build_llm_prompts` full-suite import blocker remains historical test debt.

## Escalation Rule
If pilot evidence shows fresh trace loss, boundary regression, direct concept follow-up payload loss, internal-language leak, safety failure, or delivery/history mismatch, open a narrow blocker PRD. Do not fix it silently inside cleanup work.
