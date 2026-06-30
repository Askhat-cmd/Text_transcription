# Chat 9/10 Evidence Audit

- Chat 9 predecessor evidence isolated two root classes: `S8` explicit `no_practice` violation and benign-turn acceptance/history parity loss.
- Chat 10 owner log confirmed the same family on the web surface: visible bubble and expanded LLM canvas could drift across turns, and reload could hide early turns when visible answers had not been persisted.
- Code audit mapped these symptoms to three concrete points:
  - Writer still had multiple hardcoded `Сделай один шаг прямо сейчас...` fallback branches.
  - `final_answer_acceptance_gate_v1` treated warning-only benign answers as unsavable because `can_accept` required `status == "passed"`.
  - Frontend trace lookup still had positional fallback coupling via message id / reconstructed array order when explicit stable turn identity was missing.
