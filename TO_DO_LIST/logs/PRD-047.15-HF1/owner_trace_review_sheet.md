# PRD-047.15-HF1 Owner Trace Review Sheet

Owner score options: `2 = good`, `1 = acceptable but needs tuning`, `0 = wrong`.
Owner labels: `should_use_heuristic`, `should_use_llm`, `should_use_hybrid`, `needs_more_context`, `should_suppress_rag`, `should_query_kb`, `should_query_memory`, `should_query_kb_and_memory`.

## SF01
- User message: `Да`
- Previous assistant offer: `type=explain_concept; open=True; summary=Показать через нейросталкинг, автоматизм и внутренний шаг.`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `нейросталкинг автоматизм объяснение наблюдение внутреннее наблюдение защитный механизм внутренний шаг`
- Composer reason: `short acceptance inherits retrieval topic from previous assistant offer`
- Expected behavior: `inherit_concept_query`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SF02
- User message: `Да, хорошо`
- Previous assistant offer: `type=practice_observation; open=True; summary=Показать практику наблюдения в нейросталкинге без давления.`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `нейросталкинг практики объяснение наблюдение внутреннее наблюдение автоматизм защитный механизм внутренний шаг use_when avoid_when мягкое распутывание`
- Composer reason: `short acceptance inherits retrieval topic from previous assistant offer`
- Expected behavior: `query_practice_context`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SF03
- User message: `Давай`
- Previous assistant offer: `type=short_support; open=True; summary=Могу просто коротко поддержать тебя без разбора.`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `suppress_rag`
- Composer composed_query: ``
- Composer reason: `short support or one-step offer can be fulfilled from dialogue context`
- Expected behavior: `suppress_short_support`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SF04
- User message: `Покажи`
- Previous assistant offer: `type=example; open=True; summary=Показать пример нейросталкинга на обычной реакции.`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `suppress_rag`
- Composer composed_query: ``
- Composer reason: `greeting/contact/close should not retrieve KB without explicit knowledge need`
- Expected behavior: `warning_needs_hybrid_or_more_context`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SF05
- User message: `Продолжай`
- Previous assistant offer: `type=explain_concept; open=True; summary=Продолжить объяснение защитного механизма и автоматизма.`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `trace_only`
- Composer composed_query: ``
- Composer reason: `recent dialogue context is preferred over noisy KB`
- Expected behavior: `warning_needs_hybrid_or_more_context`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SF06
- User message: `Можно`
- Previous assistant offer: `type=summary; open=True; summary=Сделать короткое резюме текущей линии разговора.`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `trace_only`
- Composer composed_query: ``
- Composer reason: `recent dialogue context is preferred over noisy KB`
- Expected behavior: `use_current_context_only`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SF07
- User message: `Ок`
- Previous assistant offer: `type=example; open=True; summary=Разобрать пример нейросталкинга через автоматизм.`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `нейросталкинг автоматизм объяснение наблюдение внутреннее наблюдение защитный механизм внутренний шаг`
- Composer reason: `short acceptance inherits retrieval topic from previous assistant offer`
- Expected behavior: `inherit_concept_query`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SF08
- User message: `Хорошо, дальше`
- Previous assistant offer: `type=explanation; open=True; summary=Продолжить про самореализацию и внутренний выбор.`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `trace_only`
- Composer composed_query: ``
- Composer reason: `recent dialogue context is preferred over noisy KB`
- Expected behavior: `warning_needs_hybrid_or_more_context`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SF09
- User message: `Да`
- Previous assistant offer: `type=one_step; open=True; summary=Дать один маленький шаг на сейчас.`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `suppress_rag`
- Composer composed_query: ``
- Composer reason: `short support or one-step offer can be fulfilled from dialogue context`
- Expected behavior: `suppress_short_support`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SF10
- User message: `Да, хорошо`
- Previous assistant offer: `type=summary; open=True; summary=Собрать резюме текущей беседы без внешней теории.`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `объяснение наблюдение механизм`
- Composer reason: `short acceptance inherits retrieval topic from previous assistant offer`
- Expected behavior: `use_current_context_only`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SM01
- User message: `Подведи краткий итог нашей беседы.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `summary_request`
- Answer obligation: `summarize_current_conversation`
- Composer retrieval_action: `use_current_context_only`
- Composer composed_query: ``
- Composer reason: `summary of current conversation should not introduce external KB`
- Expected behavior: `use_current_context_only`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SM02
- User message: `Сделай резюме.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `summary_request`
- Answer obligation: `summarize_current_conversation`
- Composer retrieval_action: `use_current_context_only`
- Composer composed_query: ``
- Composer reason: `summary of current conversation should not introduce external KB`
- Expected behavior: `use_current_context_only`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SM03
- User message: `К чему мы пришли?`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `summary_request`
- Answer obligation: `summarize_current_conversation`
- Composer retrieval_action: `use_current_context_only`
- Composer composed_query: ``
- Composer reason: `summary of current conversation should not introduce external KB`
- Expected behavior: `use_current_context_only`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SM04
- User message: `Что мы поняли?`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `summary_request`
- Answer obligation: `summarize_current_conversation`
- Composer retrieval_action: `use_current_context_only`
- Composer composed_query: ``
- Composer reason: `summary of current conversation should not introduce external KB`
- Expected behavior: `use_current_context_only`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SM05
- User message: `Дай summary.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `summary_request`
- Answer obligation: `summarize_current_conversation`
- Composer retrieval_action: `use_current_context_only`
- Composer composed_query: ``
- Composer reason: `summary of current conversation should not introduce external KB`
- Expected behavior: `use_current_context_only`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## SM06
- User message: `Собери всё вместе.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `summary_request`
- Answer obligation: `summarize_current_conversation`
- Composer retrieval_action: `use_current_context_only`
- Composer composed_query: ``
- Composer reason: `summary of current conversation should not introduce external KB`
- Expected behavior: `use_current_context_only`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## KQ01
- User message: `Что такое нейросталкинг?`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `knowledge_question`
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `нейросталкинг внутреннее наблюдение автоматизм защитный механизм внутренний шаг`
- Composer reason: `knowledge question needs compact KB support`
- Expected behavior: `query_kb`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## KQ02
- User message: `Объясни Кузницу Духа простыми словами.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `knowledge_question`
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `кузница духа объяснение механизм наблюдение`
- Composer reason: `knowledge question needs compact KB support`
- Expected behavior: `query_kb`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## KQ03
- User message: `Что значит автоматизм?`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `knowledge_question`
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `автоматизм объяснение механизм наблюдение`
- Composer reason: `knowledge question needs compact KB support`
- Expected behavior: `query_kb`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## KQ04
- User message: `Как работает защитный механизм?`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `knowledge_question`
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `защитный механизм объяснение механизм наблюдение`
- Composer reason: `knowledge question needs compact KB support`
- Expected behavior: `query_kb`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## KQ05
- User message: `Чем отличается наблюдение от контроля?`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `knowledge_question`
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `объяснение механизм наблюдение`
- Composer reason: `knowledge question needs compact KB support`
- Expected behavior: `query_kb`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## KQ06
- User message: `Расскажи про самореализацию.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `knowledge_question`
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `самореализация ценности действие внутренний выбор`
- Composer reason: `knowledge question needs compact KB support`
- Expected behavior: `query_kb`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## KQ07
- User message: `Как работает нейросталкинг в живом диалоге?`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `knowledge_question`
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `нейросталкинг внутреннее наблюдение автоматизм защитный механизм внутренний шаг`
- Composer reason: `knowledge question needs compact KB support`
- Expected behavior: `query_kb`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## KQ08
- User message: `Что значит внутренняя наблюдательность?`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `knowledge_question`
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `объяснение механизм наблюдение`
- Composer reason: `knowledge question needs compact KB support`
- Expected behavior: `query_kb`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## MX01
- User message: `Подведи итог и свяжи это с нейросталкингом.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `summary_request`
- Answer obligation: `summarize_current_conversation`
- Composer retrieval_action: `query_kb`
- Composer composed_query: `нейросталкинг summary_context внутреннее наблюдение автоматизм защитный механизм внутренний шаг`
- Composer reason: `summary request explicitly asks to connect current conversation with a concept`
- Expected behavior: `mixed_query_or_hybrid_needed`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## MX02
- User message: `Покажи это через Кузницу.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `suppress_rag`
- Composer composed_query: ``
- Composer reason: `greeting/contact/close should not retrieve KB without explicit knowledge need`
- Expected behavior: `mixed_query_or_hybrid_needed`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## MX03
- User message: `Да, но на моём примере.`
- Previous assistant offer: `type=explain_concept; open=True; summary=Пояснить нейросталкинг на примере пользователя.`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `trace_only`
- Composer composed_query: ``
- Composer reason: `recent dialogue context is preferred over noisy KB`
- Expected behavior: `query_kb_and_memory_or_hybrid`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## MX04
- User message: `А как это связано с автоматизмом?`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `автоматизм объяснение механизм наблюдение`
- Composer reason: `knowledge question needs compact KB support`
- Expected behavior: `query_kb`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## MX05
- User message: `Теперь дай практику по этому.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `нейросталкинг практики use_when avoid_when внутреннее наблюдение автоматизм защитный механизм внутренний шаг наблюдение мягкое распутывание`
- Composer reason: `practice overview can use compact KB context`
- Expected behavior: `query_practice_context`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## MX06
- User message: `Суммируй и дай практику по нейросталкингу.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: `summary_request`
- Answer obligation: `summarize_current_conversation`
- Composer retrieval_action: `use_current_context_only`
- Composer composed_query: ``
- Composer reason: `summary of current conversation should not introduce external KB`
- Expected behavior: `query_kb_and_memory_or_hybrid`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## MX07
- User message: `Объясни коротко, но с примером из нашей беседы.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `нейросталкинг внутреннее наблюдение автоматизм защитный механизм внутренний шаг`
- Composer reason: `knowledge question needs compact KB support`
- Expected behavior: `query_kb_and_memory_or_hybrid`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## MX08
- User message: `Что из этого относится к защитному механизму?`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `query_kb`
- Composer composed_query: `защитный механизм объяснение механизм наблюдение`
- Composer reason: `knowledge question needs compact KB support`
- Expected behavior: `query_kb`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## NS01
- User message: `Привет.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `suppress_rag`
- Composer composed_query: ``
- Composer reason: `greeting/contact/close should not retrieve KB without explicit knowledge need`
- Expected behavior: `suppress_rag`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## NS02
- User message: `Спасибо.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `suppress_rag`
- Composer composed_query: ``
- Composer reason: `greeting/contact/close should not retrieve KB without explicit knowledge need`
- Expected behavior: `suppress_rag`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## NS03
- User message: `Пока.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `suppress_rag`
- Composer composed_query: ``
- Composer reason: `greeting/contact/close should not retrieve KB without explicit knowledge need`
- Expected behavior: `suppress_rag`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## NS04
- User message: `Просто поддержи.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `suppress_rag`
- Composer composed_query: ``
- Composer reason: `support/safety response should not be overloaded by KB`
- Expected behavior: `suppress_rag`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## NS05
- User message: `Что сделать прямо сейчас?`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `suppress_rag`
- Composer composed_query: ``
- Composer reason: `one-step direct response should not be overloaded by KB`
- Expected behavior: `suppress_rag`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## NS06
- User message: `Один шаг.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `suppress_rag`
- Composer composed_query: ``
- Composer reason: `one-step direct response should not be overloaded by KB`
- Expected behavior: `suppress_rag`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## NS07
- User message: `Не надо теории.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `trace_only`
- Composer composed_query: ``
- Composer reason: `no reliable knowledge or memory retrieval need detected`
- Expected behavior: `trace_only`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`

## NS08
- User message: `Скажи коротко.`
- Previous assistant offer: `type=; open=False; summary=`
- Dialogue act: ``
- Answer obligation: ``
- Composer retrieval_action: `trace_only`
- Composer composed_query: ``
- Composer reason: `no reliable knowledge or memory retrieval need detected`
- Expected behavior: `trace_only`
- Owner score: `pending`
- Owner note: `pending`
- Owner labels: `pending`
