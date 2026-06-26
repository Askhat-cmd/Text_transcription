# PRD-047.34 Implementation Report

Status: `passed_with_warning`  
Main implementation commit: `39ff982`

## Scope delivered

PRD-047.34 repaired latest-turn authority inside the canonical current pipeline. The fix stayed inside existing layers and did not add a new runtime path, a new agent, DB mutation, Chroma mutation, registry/source mutation, or semantic-card expansion.

## Code changes

### Authority and routing

- `dialogue_act_resolver.py`
  - support/contact-mode turns now resolve earlier as `support_request`
  - repair/simplify/contact markers were widened
  - explicit practice detection avoids false retention when the latest turn refuses practice or shifts into contact mode

- `answer_obligation_resolver.py`
  - repair complaints now fall back to `answer_latest_turn` unless there is a truly pending unanswered question
  - support/meta-system feedback no longer default to stale-thread continuation
  - unknown fallback was narrowed toward latest-turn answering instead of blind continuation

- `final_answer_directive.py`
  - latest-turn authority became explicit
  - added:
    - `current_user_request`
    - `must_answer_source`
    - `previous_must_answer_demoted`
    - `previous_must_answer`
    - `explicit_continue_previous_detected`
    - `answer_target`
    - `writer_contact_mode`
  - default rule: latest turn wins
  - explicit continuation remains the only route that may keep previous open loop active
  - added soft `free_writer_contact` profile

### Trace and Writer visibility

- `runtime_trace_summary.py`
  - added `latest_turn_authority_v1`
  - exposed current request, source, demotion, answer target, contact mode, hard constraints, and expected KB payload

- `contracts/writer_contract.py`
  - forwarded the new latest-turn authority fields into Writer prompt context

- `agents/writer_agent_prompts.py`
  - added `LATEST TURN AUTHORITY` section

- `agents/writer_agent.py`
  - fixed missing prompt placeholders that previously triggered Writer fallback
  - blocked canned one-step collapse for `free_writer_contact` / forbidden-practice turns
  - widened trailing follow-up stripping for optional invitation tails

### Boundary hardening

- `latest_turn_constraints.py`
  - broadened explicit `no_practice` detection for natural forms like `не хочу сейчас практику`

- `legacy_advisory_sanitizer.py`
  - suppressed practice-like active-line / micro-shift hints when the latest turn forbids practice
  - replaced them with contact-safe advisory wording

### Tests and tooling

- added `tests/test_prd_047_34_latest_turn_authority.py`
- expanded:
  - `tests/test_prd_047_29_latest_turn_constraints.py`
  - `tests/multiagent/test_writer_agent.py`
- added `tools/run_prd_047_34_owner_smoke.py`

## Acceptance summary

- Chat5 stale-KB failure no longer repeats in live smoke.
- Support-after-practice latest-turn turn now wins with payload `0` and no forced practice rewrite.
- Explicit continuation still works.
- Direct KB/source still works.
- No-internal-db still keeps payload `0`.
- Explicit practice still works.
- Runtime trace now exposes latest-turn authority clearly.

## Warning that remains honest

- `python -m pytest tests -q` is still blocked by the unrelated historical import error:
  - `ImportError: cannot import name '_build_llm_prompts' from 'bot_agent.answer_adaptive'`
- A wider unrelated failure also remains in the pre-existing `tests/multiagent/test_writer_agent.py::test_semantic_hits_limit_to_two` when the whole file is run, but the PRD-047.34 targeted Writer regression added here passes.
