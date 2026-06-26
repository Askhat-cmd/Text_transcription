# PRD-047.34 Chat5 Failure Diagnosis

Status: diagnosed before final closure  
PRD: `PRD-047.34`  
Implementation commit: `39ff982`

## Latest user turn that failed

```text
Мне сейчас просто тяжело. Не хочу разбирать, просто скажи что-нибудь по-человечески.
```

## Observed wrong runtime before repair

- `dialogue_act=unknown`
- `answer_obligation=continue_thread`
- `must_answer=old KB/source question about "несовершенное Я" / five drivers`
- `answer_shape=structured_explanation`
- Writer payload already `0`, but the answer still continued the stale KB task

## Where the stale authority survived

- `dialogue_act_resolver.py` did not reliably recognize support/contact-mode shifts and simplification/repair turns as current-turn answer targets.
- `answer_obligation_resolver.py` still allowed `unknown` / repair-like turns to drift back into old-thread continuation instead of `answer_latest_turn`.
- `final_answer_directive.py` still treated the previous unanswered/open-loop state as practically active unless the new turn was a narrow explicit continuation case.
- Writer prompt surfaces did not explicitly expose current-turn authority, previous-must-answer demotion, or contact-mode intent.

## Why `dialogue_act=unknown` became stale continuation

- The old pipeline shape assumed that if the latest turn was not clearly a new direct knowledge/practice/safety request, the safest continuation was the previous open loop.
- That was acceptable for genuine follow-ups like `расскажи подробнее про второй`, but wrong for human contact-mode turns like support, simplification, refusal of practice, or refusal of analysis.
- As a result, `unknown` effectively inherited stale authority from the previous unanswered/open-loop state.

## Why answer shape stayed too heavy

- Answer-shape selection still leaned on old obligation state and legacy advisory hints.
- Even when KB payload was already suppressed, Writer still saw legacy advisory lines that could push explanation or micro-step behavior.
- The pipeline lacked an explicit `free_writer_contact` authority block that said: answer the latest human turn, not the previous internal task.

## What should demote previous `must_answer`

- The demotion belongs in the existing current pipeline, primarily in `final_answer_directive_v1`, with support from dialogue-act and answer-obligation resolution.
- `previous_must_answer` must remain trace-visible as context, not disappear.
- But by default it must lose command authority unless the latest turn explicitly continues it.

## Repair principle used

- Latest non-empty user turn becomes the default answer target.
- Previous unanswered/open-loop state remains context-only unless explicit continuation is detected.
- Support/contact turns can select `free_writer_contact`.
- Explicit practice, direct KB/source, no-internal-db, no-practice, and safety boundaries remain higher-priority hard constraints.
- No new route, no new agent, and no new DB/KB mutation were introduced.
