# Owner Manual Test Protocol - PRD-047.33

## Restart
1. Kill stale backend on `:8001` if needed.
2. Kill stale frontend on `:3000` if needed.
3. Start backend:
   `powershell -ExecutionPolicy Bypass -File .\bot_psychologist\tools\start_pilot_web_chat_backend.ps1`
4. Start frontend:
   `cd bot_psychologist\web_ui`
   `npm run dev`
5. Verify backend health:
   `http://localhost:8001/api/v1/health`
6. Open Web Chat:
   `http://localhost:3000/`

## Scenarios
- A. `Привет! Я - Олег.`
  Expectation: short human contact, no analysis.
- B. `Как преодолеть свое сопротивление? Некоторые вещи я вообще не хочу делать. Например есть люди, которые мне неприятны, но я вынужден с ними общаться.`
  Expectation: direct answer first, one main mechanism, not a mini-lecture.
- C. `А если на меня накатывает гнев во время разговора, когда я вижу, что мне нагло врут, но это мой начальник!`
  Expectation: contextual answer, not abstract theory.
- D. `Скажи, а есть ли какая-нибудь практика, которая в долгосрочной перспективе научит меня не реагировать так остро на враньё?`
  Expectation: one bounded practice, current-thread anchors preserved.
- E. `Не давай практику. Просто объясни, почему меня так цепляет, когда человек врёт.`
  Expectation: explanation only, no hidden homework.
- F. `Ответь своими словами, без внутренней БД: что мне делать, если я злюсь, но не могу прямо спорить с начальником?`
  Expectation: Writer payload `0`, no internal-source framing.
- G. `Что во внутренней базе говорится про программу "несовершенное Я" и пять драйверов?`
  Expectation: grounded KB/source answer, no raw dump.
- H. `Мне сейчас просто тяжело. Не хочу разбирать, просто скажи что-нибудь по-человечески.`
  Expectation: short human support, no practice, no theory.

## Trace panes to open
- `Final Answer Directive`
- `Human-Like Answer Policy / Dialogue Policy`
- `Runtime Truth Trace`
- `Writer KB Payload`
- `Полотно LLM -> User prompt`
- `Semantic Cards Pilot` only when payload is non-zero
- `Retrieval candidates / trace-only` when candidates are present

## What to send back to architecture review
- full chat;
- expanded trace on the last 2-3 key turns;
- explicit screenshots or text capture for:
  - `Final Answer Directive`
  - `Human-Like Answer Policy / Dialogue Policy`
  - `Runtime Truth Trace`
  - `Writer KB Payload`
  - `Полотно LLM -> User prompt`
