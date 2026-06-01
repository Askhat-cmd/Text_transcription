# PRD-047.10 Sample Answer Review

## anger_truth
- case_id: `anger_truth`
- user_message: `все верно, а что делать с гневом который внутри кричит и хочет правды?`
- expected_qualities: `min_chars, contains_any, must_not_contain_any`
- manual_review: `pass`
- notes: `none`
- trace_pointers: `writer_debug.final_answer_shape, writer_debug.human_like_answer_policy_enabled, planner.answer_shape`
- answer_excerpt:
```text
Если отвечать прямо, чаще всего цепляет не одна «черта», а связка из нескольких паттернов.

1. Гиперконтроль: попытка заранее исключить риск, из-за чего шаг откладывается.
2. Самообесценивание: внутренний фильтр «мой ответ недостаточно хороший».
3. Избегание конфликта: импульс не проявляться, чтобы не встретиться с напряжением.

Это не диагноз, а рабочие гипотезы. Можно проверить, какая из них сильнее включается в твоей конкретной ситуации.
```

## apply_neurostalking
- case_id: `apply_neurostalking`
- user_message: `как применять нейросталкинг в жизни, дай варианты и пример`
- expected_qualities: `min_chars, contains_any`
- manual_review: `pass`
- notes: `none`
- trace_pointers: `writer_debug.final_answer_shape, writer_debug.human_like_answer_policy_enabled, planner.answer_shape`
- answer_excerpt:
```text
Ключевая идея нейросталкинга — не «исследовать чужой мозг», а внимательно наблюдать свои автоматические реакции, триггеры и внутренние истории так, чтобы они перестали управлять вами бессознательно. Варианты применения: 1) моментальное замечание — в момент раздражения или тревоги коротко пометить («внимание: страх»), дышать и не сразу действовать; 2) дневниковое слежение — записывать триггеры, мысли и повторяющиеся реакции за неделю, чтобы увидеть паттерны; 3) экспериментальная практика — менять маленькое поведение после триггера (например, вместо срыва сделать 2 минуты паузы) и наблюдать, что меняется; 4) контекстная карта — связывать триггеры с ситуациями/людьми и планировать простые обходные ходы. Пример: на работе коллега критикует вас — вы замечаете внутренний голос «я плохой», помеча
```

## direct_concrete_shadow
- case_id: `direct_concrete_shadow`
- user_message: `назови конкретно, какая черта во мне может цепляться за эту ситуацию`
- expected_qualities: `min_chars, contains_any, must_not_contain_any`
- manual_review: `pass`
- notes: `none`
- trace_pointers: `writer_debug.final_answer_shape, writer_debug.human_like_answer_policy_enabled, planner.answer_shape`
- answer_excerpt:
```text
Если отвечать прямо, чаще всего цепляет не одна «черта», а связка из нескольких паттернов.

1. Гиперконтроль: попытка заранее исключить риск, из-за чего шаг откладывается.
2. Самообесценивание: внутренний фильтр «мой ответ недостаточно хороший».
3. Избегание конфликта: импульс не проявляться, чтобы не встретиться с напряжением.

Это не диагноз, а рабочие гипотезы. Можно проверить, какая из них сильнее включается в твоей конкретной ситуации.
```

## explain_neurostalking
- case_id: `explain_neurostalking`
- user_message: `объясни как chatgpt: что такое нейросталкинг, подробно и с примером`
- expected_qualities: `min_chars, contains_any, must_not_contain_any`
- manual_review: `pass`
- notes: `none`
- trace_pointers: `writer_debug.final_answer_shape, writer_debug.human_like_answer_policy_enabled, planner.answer_shape`
- answer_excerpt:
```text
Ключевая идея: нейросталкинг — это внимательное внешнее наблюдение за своими автоматическими реакциями, триггерами и нейрофизиологией страдания — не чтобы лечить «я», а чтобы увидеть и понять, как работает программа поведения. Проще: ты учишься замечать, что запускает старые паттерны, как именно тело и мысли реагируют, и где можно не включаться в автоматический сценарий. Пример: вместо «я снова злюсь, значит я плох/неуспешен», нейросталкинг заметит сначала: «срабатывание — учащённое дыхание, мысль о критике, стремление уйти», и держит это как объект наблюдения, а не как приговор. Применение: помогает прерывать автоматические реакции, уменьшать интенсивность страдания и выбирать ответнее действие осознанно. Хочешь, чтобы я привёл конкретный пример нейросталкинга для ситуации, с которой ты с
```

## explicit_one_step
- case_id: `explicit_one_step`
- user_message: `дай один конкретный шаг прямо сейчас, без теории`
- expected_qualities: `max_chars, max_questions, must_not_contain_any`
- manual_review: `pass`
- notes: `none`
- trace_pointers: `writer_debug.final_answer_shape, writer_debug.human_like_answer_policy_enabled, planner.answer_shape`
- answer_excerpt:
```text
Сделай один шаг прямо сейчас: открой задачу и выполни первый минимальный фрагмент в течение 5 минут.
```

## practice_catalog
- case_id: `practice_catalog`
- user_message: `скажи, а в нейросталкинге какие практики предлагаются чтобы это видеть?`
- expected_qualities: `min_chars, list_min, contains_any`
- manual_review: `pass`
- notes: `none`
- trace_pointers: `writer_debug.final_answer_shape, writer_debug.human_like_answer_policy_enabled, planner.answer_shape`
- answer_excerpt:
```text
В нашей рамке нейросталкинга это лучше смотреть не как один шаг, а как несколько практических направлений.

1. Практика наблюдения триггера. Смысл: вовремя заметить момент, где включается автопилот. Пример: в разговоре с начальником отследить первую мысль «сейчас лучше промолчать», чтобы не провалиться в автоматическое согласие.
2. Практика распознавания паттерна реакции. Смысл: увидеть повторяющийся сценарий (контроль, самообесценивание, избегание) и назвать его простыми словами. Пример: заметить, что перед важной задачей включается цикл «перепроверяю и откладываю старт».
3. Практика микро-сдвига поведения. Смысл: вернуть себе выбор через небольшой осознанный ход. Пример: вместо внутреннего спора сформулировать одну короткую фактическую реплику или начать первый фрагмент задачи на фиксиро
```

## sarcastic_dissatisfaction
- case_id: `sarcastic_dissatisfaction`
- user_message: `спасибо что ты не дал мне никаких ответов`
- expected_qualities: `min_chars, contains_any, must_not_contain_any`
- manual_review: `pass`
- notes: `none`
- trace_pointers: `writer_debug.final_answer_shape, writer_debug.human_like_answer_policy_enabled, planner.answer_shape`
- answer_excerpt:
```text
Ты прав, прошлый ответ был мимо сути. Исправляюсь и отвечаю прямо.

Если тебе нужен рабочий ориентир, смотри на три узла: где запускается триггер, какой автопаттерн перехватывает реакцию, и какой конкретный ответ возвращает тебе выбор в этой ситуации.

Если хочешь, могу сразу разобрать это на твоем примере в формате: механизм -> варианты -> фраза/действие.
```

## short_support
- case_id: `short_support`
- user_message: `коротко поддержи, без анализа`
- expected_qualities: `max_chars, max_questions, contains_any`
- manual_review: `pass`
- notes: `none`
- trace_pointers: `writer_debug.final_answer_shape, writer_debug.human_like_answer_policy_enabled, planner.answer_shape`
- answer_excerpt:
```text
Сфокусируюсь на разборе, без практик по умолчанию. Здесь ключевой узел в том, как автоматический контроль включает перегруз ещё до действия.
```

## summarize_full_chat
- case_id: `summarize_full_chat`
- user_message: `обобщи весь разговор и дай главное`
- expected_qualities: `min_chars, contains_any, must_not_contain_any`
- manual_review: `pass`
- notes: `none`
- trace_pointers: `writer_debug.final_answer_shape, writer_debug.human_like_answer_policy_enabled, planner.answer_shape`
- answer_excerpt:
```text
Соберу итог по разговору коротко и по сути.

1. Что с тобой происходит сейчас. Есть внутренний конфликт между желанием действовать и автоматической защитой через контроль.
2. Где застревание. До действия включается прогноз риска, и ресурс уходит в внутренний спор вместо шага.
3. Ключевой сдвиг. Отделять факт ситуации от автоматической реакции и возвращать себе выбор в моменте.
4. Куда двигаться дальше. Выбрать один повторяющийся триггер и посмотреть, какой ответ по факту поддерживает твою цель.
```

