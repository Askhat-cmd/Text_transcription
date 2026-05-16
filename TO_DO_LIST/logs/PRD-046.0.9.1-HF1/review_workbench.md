# Human Review Workbench - PRD-046.0.9.1-HF1

## Summary
- queue source: PRD-046.0.9-RUN1
- items: 87
- priorities: P0/P1/P2 = 0/1/86
- production mutation: false

## Review rules
- Check advisory enrichment only.
- Do not mutate governance authority fields.
- Do not quote source directly to end users.
- Do not auto-approve without manual review.
- Use defer when uncertain.

## Decision values
- approved
- rejected
- needs_edit
- defer

## Items

### P0

- none

### P1

#### post_reprocess::66d0f456-a695-4c50-881c-0ce7643baf69 / block_id 66d0f456-a695-4c50-881c-0ce7643baf69
- source_id: 123__кузница_духа
- chunk_type: practice
- allowed_use: writer_context, practice_suggestion
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: low_confidence
- recommended_action: needs_edit
- content_preview: **Цель:** переварить застрявшую ситуацию с другим человеком. **Время:** 30 минут.
- llm_enrichment:
  - summary: Рекомендуется использовать активное слушание и эмпатию для разрешения конфликтов. Важно создать безопасное пространство для открытого диалога, где обе стороны могут выразить свои чувства и мысли.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

### P2

#### post_reprocess::00a10081-935a-4c17-a000-d91c7420ce7f / block_id 00a10081-935a-4c17-a000-d91c7420ce7f
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки точности интерпретаций, потенциальные риски неправильного понимания
- recommended_action: defer
- content_preview: Важно сразу: это название вводит в заблуждение. Речь не только о сексе. Речь о **влечении к интенсивному единению** — с человеком, идеей, проектом, переживанием. **Базовый вопрос:** «Есть ли в моей жизни то, что захватывает меня целиком?»…
- llm_enrichment:
  - summary: Данный блок обсуждает концепцию влечения к интенсивному единению, акцентируя внимание на важности страсти и интенсивности в жизни. Он поднимает вопросы о том, что действительно захватывает человека и как это влияет на...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::02850e6b-1f41-4f94-8413-cdec8c45479b / block_id 02850e6b-1f41-4f94-8413-cdec8c45479b
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки точности интерпретации, сложность темы
- recommended_action: defer
- content_preview: *** **— Я знаю о своей тени уже много лет. Хожу на терапию, читал Юнга. Но она всё равно управляет. Почему знания недостаточно?** — Потому что тень живёт не в знании — она живёт в теле и в эмоциональной памяти. Знать про злость — и встрети…
- llm_enrichment:
  - summary: Понимание своей тени требует не только знания, но и эмоционального опыта. Эмоциональная память и телесные переживания играют ключевую роль в интеграции тени.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::0b3494cd-7acb-46cc-881b-7e478b72513e / block_id 0b3494cd-7acb-46cc-881b-7e478b72513e
- source_id: 123__кузница_духа
- chunk_type: case
- allowed_use: writer_context
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, оценка безопасности рекомендаций, проверка точности научных терминов
- recommended_action: defer
- content_preview: Ключевой принцип — и он идёт вразрез с большинством популярных советов: **Страх уменьшается не от избегания и не от силового преодоления. Он уменьшается от встречи.** Это нейрофизиологически обоснованный факт. Механизм называется **экспози…
- llm_enrichment:
  - summary: Страх уменьшается через встречу с ним в безопасных условиях, что подтверждается нейрофизиологическими исследованиями. Этот подход лежит в основе когнитивно-поведенческой терапии и называется экспозицией с реципрокным...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::0d62f141-572d-4386-b02d-d7f9a46fa27f / block_id 0d62f141-572d-4386-b02d-d7f9a46fa27f
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка точности интерпретации страха.
- recommended_action: defer
- content_preview: Один из самых распространённых страхов, с которыми приходят на сессии Саламата — и один из наименее обсуждаемых публично. **Лиссофобия** — в широком смысле это страх сойти с ума, потерять контроль над собственным разумом. Но в практике раб…
- llm_enrichment:
  - summary: Лиссофобия представляет собой страх потери контроля над разумом и идентичностью, что является распространённым, но редко обсуждаемым страхом. Этот страх может затруднять работу с сознанием и требует внимательного подх...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::0dbf25dc-c955-49f9-b3b8-eab4e3bbeed2 / block_id 0dbf25dc-c955-49f9-b3b8-eab4e3bbeed2
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Оценка актуальности теоретических основ, Проверка на соответствие принципам безопасности
- recommended_action: defer
- content_preview: ***
- llm_enrichment:
  - summary: Данный блок содержит теоретические основы, которые могут быть использованы для обогащения внутреннего консультирования. Он подчеркивает важность соблюдения принципов безопасности и конфиденциальности при работе с данн...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::116415f6-a0c4-4701-86d4-83be1d6a8b4f / block_id 116415f6-a0c4-4701-86d4-83be1d6a8b4f
- source_id: 123__кузница_духа
- chunk_type: case
- allowed_use: writer_context
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, необходима проверка на соответствие контексту, потенциальные риски неверной интерпретации
- recommended_action: defer
- content_preview: **Цель:** использовать менее развитые инстинктивные центры как дополнительный ресурс. **Время:** 20–30 минут как исследование. У каждого есть не только доминирующий инстинкт, но и наименее развитый — «слепое пятно». Именно он чаще всего со…
- llm_enrichment:
  - summary: Исследование менее развитых инстинктивных центров может помочь в понимании своих слабых сторон и улучшении личной эффективности. Важно осознать, что каждый человек имеет доминирующий инстинкт и менее развитый, который...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::1243381f-27fe-4f5e-95bb-605b8ba64c1a / block_id 1243381f-27fe-4f5e-95bb-605b8ba64c1a
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходимость проверки интерпретаций, Потенциальная чувствительность темы
- recommended_action: defer
- content_preview: **Базовая установка:** «Мои потребности неважны. Важны потребности других» Ребёнок выражает своё желание. Родитель реагирует раздражением или игнорированием. Вывод: **«Мои желания создают проблемы. Чтобы быть любимым — надо угождать»**. Во…
- llm_enrichment:
  - summary: Данный блок описывает влияние детских установок на взрослую жизнь, где потребности индивида игнорируются в пользу угождения другим. Это может привести к трудностям в установлении границ и выражении собственных желаний.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::15b76643-6a4a-473f-8f9a-754f608bdc97 / block_id 15b76643-6a4a-473f-8f9a-754f608bdc97
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки интерпретации, потенциальная сложность в понимании
- recommended_action: defer
- content_preview: Теория без практики — это просто информация. Ты можешь понять всё написанное выше, согласиться, кивнуть — и ничего не изменится. Потому что программа работает не на уровне понимания. Она работает на уровне **опыта**. То, что ниже — не упра…
- llm_enrichment:
  - summary: Данный блок подчеркивает важность практического опыта в обучении и исследовании. Он акцентирует внимание на том, что теоретические знания без практического применения не приводят к изменениям. Предлагается рассмотреть...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::1a5e8a48-a1be-4c10-80e9-c2cb714503b2 / block_id 1a5e8a48-a1be-4c10-80e9-c2cb714503b2
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка интерпретаций, потенциальные ошибки в выводах
- recommended_action: defer
- content_preview: Посмотри на ответы в целом. Где повторяется одна тема — там и доминирующий инстинкт.
- llm_enrichment:
  - summary: Анализируя ответы, можно выделить повторяющиеся темы, которые указывают на доминирующие инстинкты. Это может помочь в понимании мотивации и поведения участников.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::201ad0be-2cbf-4499-b92f-f0fc86ee09c0 / block_id 201ad0be-2cbf-4499-b92f-f0fc86ee09c0
- source_id: 123__кузница_духа
- chunk_type: case
- allowed_use: writer_context
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, Проверка на соответствие эмоциональной безопасности, Убедиться в отсутствии потенциально чувствительных тем
- recommended_action: defer
- content_preview: **Цель:** определить, в каком «костюме» сейчас ходит твоя программа «несовершенное Я». **Время:** 10 минут. Вспомни, что в последние дни говорил внутренний голос программы. Не общие ощущения — конкретные фразы, которые ты слышал внутри. Те…
- llm_enrichment:
  - summary: Определение текущего состояния внутреннего голоса программы 'несовершенное Я' с акцентом на конкретные фразы и их эмоциональную окраску.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::28d35b6b-6b5c-4c5a-bb14-0b8a3f2b5d37 / block_id 28d35b6b-6b5c-4c5a-bb14-0b8a3f2b5d37
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка на соответствие контексту, проверка на точность интерпретации
- recommended_action: defer
- content_preview: Теперь самое важное для практики. Каждый уровень — это **замкнутая система смыслов**. У каждого своя «очевидная правда», которая внутри уровня не ставится под вопрос. И именно поэтому люди с разных уровней не просто не соглашаются — они не…
- llm_enrichment:
  - summary: Разные уровни восприятия создают барьеры в коммуникации, что затрудняет понимание и согласие между людьми с различными взглядами.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::33747757-5b99-4cb6-a4c4-99154d889205 / block_id 33747757-5b99-4cb6-a4c4-99154d889205
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки точности культурных интерпретаций, учет контекста при использовании информации
- recommended_action: defer
- content_preview: **Мантра:** «Мы — одно целое. Духи защищают нас». **Что важно:** принадлежность к племени — семье, роду, этносу, клану. Магическое мышление: духи, ритуалы, приметы, заговоры. Авторитет — старейшины, традиция. Страх — быть изгнанным из плем…
- llm_enrichment:
  - summary: Культура, основанная на коллективной идентичности и магическом мышлении, подчеркивает важность принадлежности к племени и традициям. Взаимодействие с духами и ритуалами играет ключевую роль в жизни сообщества, а старе...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::36350a15-7144-4bc9-b79f-fe227d2b39ee / block_id 36350a15-7144-4bc9-b79f-fe227d2b39ee
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки точности интерпретаций, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: - Если сжат — это тревога или страх? - Если пустота — что это за пустота?
- llm_enrichment:
  - summary: Исследование эмоциональных состояний, таких как тревога и страх, а также концепция пустоты и её возможные интерпретации. Обсуждение различных подходов к пониманию этих состояний в контексте психологии.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::40de9766-584b-4fd7-a6e9-fadd34146e91 / block_id 40de9766-584b-4fd7-a6e9-fadd34146e91
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка на соответствие эмоциональному контексту, проверка на возможность использования в других контекстах
- recommended_action: defer
- content_preview: Нет правильного письма. Нет неправильного. Единственное условие — не лгать себе ни в одном предложении. После того как написал — прочитай вслух. Если возникают слёзы, злость, облегчение — это нормально. Это не «надломился». Это просто что-…
- llm_enrichment:
  - summary: Письмо отражает важность самовыражения и признательности, а также эмоциональную нагрузку, связанную с процессом написания. Это может быть полезным для понимания собственных чувств и улучшения коммуникации.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::49f52f32-1157-4450-b155-e268e89b2248 / block_id 49f52f32-1157-4450-b155-e268e89b2248
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, оценка актуальности и полезности, проверка на соответствие безопасности
- recommended_action: defer
- content_preview: **Цель:** увидеть, в чём именно твоя программа черпает «топливо» — и насколько часто. **Время:** 15–20 минут. Делать один раз — как исследование. Это немного длиннее остальных практик. Зато она даёт очень точную карту. Возьми лист бумаги.…
- llm_enrichment:
  - summary: Исследование для понимания источников эмоционального состояния и частоты их влияния на жизнь.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::537704a8-d617-476e-8ae2-bc48d1c3d09f / block_id 537704a8-d617-476e-8ae2-bc48d1c3d09f
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие контексту и безопасности.
- recommended_action: defer
- content_preview: Есть вещи, которые ты не делаешь. Не потому что не хочешь — а потому что страшно. Разговор, который давно нужен. Решение, которое давно созрело. Шаг, который уже виден — но нога не двигается. Ты знаешь это ощущение. Все знают. Первый рефле…
- llm_enrichment:
  - summary: Обсуждение страха и его влияния на действия человека. Рассматривается необходимость преодоления страха для достижения целей, а также критика традиционных подходов к мотивации.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::538dcd01-2545-4ecf-9e7e-a8699ca76164 / block_id 538dcd01-2545-4ecf-9e7e-a8699ca76164
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима оценка контекста и чувствительности информации.
- recommended_action: defer
- content_preview: > Из сессии: > > **Максим, 40 лет:** Я несколько месяцев в каком-то странном состоянии. Ничего не хочу, ничего не радует, ничего не делаю — хотя дела есть. Просто лежу. Думал — депрессия. > > **Саламат:** Расскажи, что было до этого. Полго…
- llm_enrichment:
  - summary: Клиент описывает состояние апатии и отсутствие интереса к жизни после периода высокой нагрузки и стресса. Это может указывать на возможные симптомы депрессии или выгорания.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::56c62ae3-7bce-4525-b460-a64f86441657 / block_id 56c62ae3-7bce-4525-b460-a64f86441657
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки точности интерпретаций, потенциальные недопонимания концепции
- recommended_action: defer
- content_preview: Юнг ввёл понятие тени в начале XX века. Но только в последние десятилетия нейронаука дала этому понятию конкретный механизм. **Тень** — это не «плохая часть» личности. Это совокупность психических содержаний, которые были **вытеснены из ос…
- llm_enrichment:
  - summary: Концепция тени, введенная Юнгом, описывает вытесненные аспекты личности, которые могут быть опасными или неприемлемыми в социальной среде. Нейронаука предоставляет механизмы, объясняющие это явление.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::5808a31f-2872-4e48-826c-b318bf0d60b0 / block_id 5808a31f-2872-4e48-826c-b318bf0d60b0
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки точности интерпретации, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: Программа не возникает в один момент. Она складывается постепенно. **От рождения до 2 лет — базовое ощущение мира** Ребёнок ещё не думает словами. Он просто чувствует и запоминает телом: *мир безопасен или нет*. Если рядом был стабильный,…
- llm_enrichment:
  - summary: Программа развития ребенка формируется постепенно, начиная с раннего возраста. В первые два года жизни базовые ощущения мира формируются через взаимодействие с взрослыми. Стабильные и предсказуемые взрослые способству...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::5943bece-db10-460a-bc21-7e23e6485925 / block_id 5943bece-db10-460a-bc21-7e23e6485925
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: self_worth
- review_reasons: needs_human_review, необходима проверка на точность, потенциальные риски интерпретации
- recommended_action: defer
- content_preview: НейроСталкинг и НеоСталкинг — это два уровня одного процесса. **НейроСталкинг** — это работа с первым этажом. Паттерны, триггеры, автоматические реакции, нейрофизиология страдания. Здесь ты исследуешь, как работает программа. Смотришь на н…
- llm_enrichment:
  - summary: НейроСталкинг и НеоСталкинг представляют собой два уровня анализа и взаимодействия с программами. НейроСталкинг фокусируется на первичных реакциях и паттернах, в то время как НеоСталкинг предлагает более глубокую перс...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::5bd68e84-d34a-487b-ab73-7cd1ac889e7a / block_id 5bd68e84-d34a-487b-ab73-7cd1ac889e7a
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка на соответствие контексту, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: Зрелость добавляет свой слой. Профессиональная среда говорит: «здесь не место эмоциям». Партнёрские отношения говорят: «ты слишком много требуешь». Социальные роли говорят: «мужчины так себя не ведут», «матери так не думают». Каждый раз, к…
- llm_enrichment:
  - summary: Зрелость и социальные роли могут создавать давление, заставляя людей скрывать свои эмоции и истинные чувства, что приводит к внутреннему конфликту и самоограничению.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::5be3f5b0-a073-4c15-8ed6-429ad22c029b / block_id 5be3f5b0-a073-4c15-8ed6-429ad22c029b
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, обеспечение соответствия этическим стандартам, проверка точности психологических интерпретаций
- recommended_action: defer
- content_preview: Представь, что твой мозг — это компьютер. В возрасте примерно от 2 до 6 лет на этот компьютер устанавливается операционная система. Но это не Windows и не macOS. Это **OS «Я недостаточен»**. Эта операционная система запускает один базовый…
- llm_enrichment:
  - summary: В раннем возрасте формируется восприятие себя как недостаточного, что может влиять на дальнейшее развитие личности и самооценку. Этот паттерн может стать основой для различных психологических проблем и потребности в с...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::5d1fc4fd-0fe3-430e-be38-37aa453a5bf0 / block_id 5d1fc4fd-0fe3-430e-be38-37aa453a5bf0
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие стандартам коммуникации, Потенциально чувствительный контент
- recommended_action: defer
- content_preview: - Обвиняющим? — «ты снова облажался» - Тревожным? — «всё идёт не так, надо срочно что-то делать» - Сравнивающим? — «у других получается, а у тебя нет» - Требующим? — «нужно быстрее, больше, лучше»
- llm_enrichment:
  - summary: В данном контексте рассматриваются различные типы обвинений и их эмоциональная окраска. Важно понимать, как такие фразы могут влиять на восприятие и взаимодействие в команде.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::5d99473f-b1e2-4f20-b169-1e578c64fd51 / block_id 5d99473f-b1e2-4f20-b169-1e578c64fd51
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка точности научных данных, проверка на соответствие этическим стандартам
- recommended_action: defer
- content_preview: Это работает. Не потому что красиво звучит — потому что так устроена нейрохимия. ***
- llm_enrichment:
  - summary: Нейрохимия играет ключевую роль в формировании нашего восприятия и поведения. Понимание этих процессов может помочь в разработке более эффективных стратегий для улучшения психического здоровья и благополучия.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::6248b3d0-7fd6-4d9e-8b0b-5bc604b0bf98 / block_id 6248b3d0-7fd6-4d9e-8b0b-5bc604b0bf98
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, обеспечение соответствия контексту, проверка точности теоретических интерпретаций
- recommended_action: defer
- content_preview: Коржибский описал язык как главный инструмент искажения. Нейролингвистика пошла дальше и выделила три базовых механизма, через которые мозг превращает сырую реальность в «личную версию»: ***
- llm_enrichment:
  - summary: Коржибский подчеркивает, что язык является ключевым инструментом искажения восприятия реальности. Нейролингвистика развивает эту идею, выделяя три основных механизма, через которые мозг интерпретирует окружающий мир.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::6440c58d-424c-4d15-9856-0775b2baa161 / block_id 6440c58d-424c-4d15-9856-0775b2baa161
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие этическим стандартам, Проверка на чувствительность содержания
- recommended_action: defer
- content_preview: После заполнения — посмотри на карту целиком. Три вопроса: - *Где больше всего страдания?* - *Это страдание «живое» — то есть связано с реальной текущей ситуацией — или оно «хроническое», фоновое, непонятно откуда?* - *Есть ли области, где…
- llm_enrichment:
  - summary: Анализ эмоционального состояния пользователя с акцентом на области страдания и благополучия. Важно исследовать, где страдания наиболее выражены и как они соотносятся с текущими и хроническими переживаниями.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::648f6960-e5cf-4558-a111-fcd668b2096a / block_id 648f6960-e5cf-4558-a111-fcd668b2096a
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки точности интерпретации, потенциальная сложность концепции
- recommended_action: defer
- content_preview: Когда слышишь «безусловная любовь» — первый импульс обычно: умиление, что-то про принятие, про добро. Мягкое. Здесь — другое. Безусловная любовь в понимании НеоСталкинга — это не эмоция. Не решение «любить всех». Не духовная практика. Это…
- llm_enrichment:
  - summary: Безусловная любовь в контексте НеоСталкинга рассматривается как качество восприятия, а не как эмоция или духовная практика. Это состояние, возникающее при отстранении от программы.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::650e5ee6-4072-449e-9b93-bc2729e553db / block_id 650e5ee6-4072-449e-9b93-bc2729e553db
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, обеспечение контекстуальной корректности, проверка точности интерпретаций
- recommended_action: defer
- content_preview: Мозг **удаляет** часть информации — просто не замечает её. Как в примере с Бекзатом: похвала была — мозг её удалил. Удаление работает по принципу: **важно то, что соответствует текущей программе**. Это объясняет, почему два человека в одно…
- llm_enrichment:
  - summary: Мозг фильтрует информацию в зависимости от текущих приоритетов и программ, что приводит к различным восприятиям одних и тех же событий у разных людей.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::677843aa-2939-4b07-9a57-d2fe14337291 / block_id 677843aa-2939-4b07-9a57-d2fe14337291
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка на соответствие контексту, проверка на актуальность теоретических концепций
- recommended_action: defer
- content_preview: ***
- llm_enrichment:
  - summary: Данный блок содержит теоретическую информацию, которая может быть использована для обогащения контекста написания. Он предлагает идеи и концепции, которые могут быть полезны для дальнейшего анализа и разработки.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::6af86446-6b2e-4fed-a4b2-c44cc378e1fa / block_id 6af86446-6b2e-4fed-a4b2-c44cc378e1fa
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка на точность интерпретации, потенциальные нюансы в контексте
- recommended_action: defer
- content_preview: Посмотри на список целиком. Есть ли тема, которая повторяется? Один центральный страх, который порождает несколько других? ***
- llm_enrichment:
  - summary: Анализ повторяющихся тем и центральных страхов в контексте теории. Выявление взаимосвязей между различными страхами и их корнями.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::6b2cc0f2-32e5-4b1e-8ae1-82e611b285aa / block_id 6b2cc0f2-32e5-4b1e-8ae1-82e611b285aa
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие внутренним стандартам, Проверка на возможность применения в конкретных контекстах
- recommended_action: defer
- content_preview: ***
- llm_enrichment:
  - summary: Представленный теоретический блок предлагает анализ и рекомендации по улучшению процессов управления и взаимодействия в организации. Он подчеркивает важность гибкости и адаптивности в управлении, а также необходимость...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::6bf8b1df-463c-4fd0-9e34-289518dd849d / block_id 6bf8b1df-463c-4fd0-9e34-289518dd849d
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие контексту, Потенциальные риски неправильной интерпретации
- recommended_action: defer
- content_preview: После трёх версий — посмотри на них рядом. Версия программы — это правда о реальности? Или это одна из нескольких возможных интерпретаций? ***
- llm_enrichment:
  - summary: Обсуждение различных версий программы и их интерпретаций в контексте реальности. Важно рассмотреть, как разные версии могут влиять на восприятие и понимание информации.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::6d0c2432-96ca-4293-beec-9bf337955a7a / block_id 6d0c2432-96ca-4293-beec-9bf337955a7a
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие контексту, Потенциальные риски неверного толкования
- recommended_action: defer
- content_preview: **Базовая установка:** «Любовь нужно заслужить достижениями» Родители хвалят только за успехи. «Пятёрка — молодец! Четвёрка — мог бы лучше». Или сравнивают: «А вот Маша в классе учится на отлично». Мозг ребёнка делает вывод: **«Меня любят…
- llm_enrichment:
  - summary: Формирование представления о любви как о чем-то, что нужно заслужить, может негативно сказаться на самооценке и эмоциональном состоянии человека. Важно понимать, что любовь и принятие не зависят от достижений.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::6d484c8a-f7f0-407e-99e5-d35048f7b48d / block_id 6d484c8a-f7f0-407e-99e5-d35048f7b48d
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка точности научных данных, проверка на соответствие контексту использования
- recommended_action: defer
- content_preview: Страх — самая быстрая из всех эмоций. Быстрее злости, быстрее радости, быстрее любви. Это не случайность — это архитектура выживания. Вот что происходит, когда нервная система регистрирует угрозу: **0–70 миллисекунд:** сигнал от органов чу…
- llm_enrichment:
  - summary: Страх является одной из самых быстрых эмоций, активирующихся в ответ на угрозу. Этот процесс происходит мгновенно, когда сигнал от органов чувств достигает таламуса и передается в миндалину, что запускает стрессовую р...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::6db17c5b-638d-452e-8a9c-8384c9ed78a4 / block_id 6db17c5b-638d-452e-8a9c-8384c9ed78a4
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, необходима проверка на соответствие контексту, проверка на точность интерпретаций
- recommended_action: defer
- content_preview: Программа «несовершенное Я» — не монолит. Она говорит разными голосами. У каждого человека один-два из них звучат особенно громко. Посмотри на каждый — ты узнаешь свой. ***
- llm_enrichment:
  - summary: Программа «несовершенное Я» представляет собой многогранный проект, который исследует различные аспекты человеческой идентичности и самовосприятия. Каждый участник может обнаружить в себе уникальные голоса, отражающие...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::71ca41f6-57de-4f57-badb-35e34e8bd9c6 / block_id 71ca41f6-57de-4f57-badb-35e34e8bd9c6
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие этическим стандартам, Потенциальная чувствительность темы
- recommended_action: defer
- content_preview: > **Из сессии** > > **Мария, 39 лет, топ-менеджер:** Я не понимаю, что со мной. Всё есть — работа, деньги, отношения, здоровье. Я занимаюсь всем, чем «надо»: терапия, медитация, книги. И при этом — ощущение, что меня нет. Как будто я смотр…
- llm_enrichment:
  - summary: Клиент испытывает чувство пустоты и отсутствия эмоциональной связи с жизнью, несмотря на наличие всех внешних факторов успеха. Это может указывать на депрессию или эмоциональное выгорание.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::7292f9ff-3e15-4258-a8dc-e4860f1cc103 / block_id 7292f9ff-3e15-4258-a8dc-e4860f1cc103
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки интерпретаций, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: И вот самый неудобный вопрос. Тот, который легко обойти стороной. Если тебе так плохо от этой программы — почему она до сих пор работает? Ты умный человек. Читал, практиковал, осознавал. **Почему ничего не изменилось?** Потому что программ…
- llm_enrichment:
  - summary: Вопрос о том, почему программа продолжает функционировать, несмотря на негативные последствия для пользователей, поднимает важные аспекты о выгодах и мотивациях систем. Это может указывать на то, что программа оптимиз...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::7451908b-565b-4d40-a214-88c5adfceac4 / block_id 7451908b-565b-4d40-a214-88c5adfceac4
- source_id: 123__кузница_духа
- chunk_type: safety
- allowed_use: writer_context, safety_protocol
- safety_flags: not_for_direct_quote
- lens_family: safety
- review_reasons: needs_human_review, необходимость проверки интерпретации концепций, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: **Мантра:** «Выжить. Сейчас». **Что важно:** еда, тепло, безопасность, вода. Нет «я» в социальном смысле — только биологическое существо. Нет планирования — только момент. Нет морали — только нужда. Исторически это уровень раннего человека…
- llm_enrichment:
  - summary: В условиях острого кризиса, когда базовые потребности становятся приоритетом, важно сосредоточиться на выживании. Это состояние требует минимализма в социальных взаимодействиях и акцентирования на физиологических нуждах.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::760cd26e-e9c1-4d42-90b8-5726aa9fd129 / block_id 760cd26e-e9c1-4d42-90b8-5726aa9fd129
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка на соответствие контексту, проверка на точность интерпретации
- recommended_action: defer
- content_preview: Это не медитация. Это тренировка способности вкусить — не присвоить. Разница небольшая. Но она меняет качество жизни фундаментально. ***
- llm_enrichment:
  - summary: Тренировка способности воспринимать опыт без привязки и присвоения может значительно улучшить качество жизни. Это требует осознанности и практики.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::7b61940d-f6ff-46f8-9514-797efaf0ad00 / block_id 7b61940d-f6ff-46f8-9514-797efaf0ad00
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки на соответствие безопасности, проверка на корректность интерпретации вопросов
- recommended_action: defer
- content_preview: *Это реальные вопросы участников сессий. Они возникают почти у всех. Если ты читаешь и узнаёшь свой вопрос — значит, ты в правильном месте.* *** **— Я всё понял про программу. Но как её убрать? Должен же быть какой-то метод.** — Смотри, «у…
- llm_enrichment:
  - summary: Участники сессий задают вопросы о том, как изменить или убрать программу, что указывает на их желание понять механизмы работы и управления программами. Это подчеркивает важность осознания иронии в том, что программа с...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::7b658406-6fa8-4d88-84dc-1b49ebf53465 / block_id 7b658406-6fa8-4d88-84dc-1b49ebf53465
- source_id: 123__кузница_духа
- chunk_type: case
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходимость в дополнительной проверке чувствительности темы, потенциальные риски неверного толкования
- recommended_action: defer
- content_preview: > **Надежда**, 41 год, предприниматель. > > — Я занималась разными практиками. Медитация, работа с телом, расстановки. Мне кажется, я проработала своё прошлое. Но что-то всё равно продолжает мешать. Как будто под слоем уже есть ещё слой. >…
- llm_enrichment:
  - summary: Клиентка, предприниматель, ощущает, что несмотря на проведенные практики самопознания и проработки прошлого, ей все еще мешают внутренние барьеры. Она осознает свои паттерны, но чувствует, что под ними скрываются боле...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::87df2063-9514-4bf6-b833-6815fc1652d3 / block_id 87df2063-9514-4bf6-b833-6815fc1652d3
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Оценка оригинальности и актуальности, Проверка на соответствие контексту
- recommended_action: defer
- content_preview: ***
- llm_enrichment:
  - summary: Данный блок представляет собой теоретическую основу, которая может быть использована для обогащения контента. Он содержит ключевые концепции и идеи, которые могут быть полезны для создания более глубокого и информатив...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::8e8eae66-7d04-4b55-b0ee-0b5c29c6d750 / block_id 8e8eae66-7d04-4b55-b0ee-0b5c29c6d750
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима оценка контекста использования, потенциальные риски неверной интерпретации
- recommended_action: defer
- content_preview: **Мантра:** «Я — сам. Кто сильнее — тот прав». **Что важно:** власть, автономия, немедленное удовлетворение желаний. Нет чувства вины — есть только «хочу» и «могу». Импульсивность. Сила как главная ценность. Уважение завоёвывается через де…
- llm_enrichment:
  - summary: Данная мантра подчеркивает важность автономии и силы в межличностных отношениях, акцентируя внимание на импульсивности и тактическом подходе к взаимодействию с окружающими. В здоровом проявлении эти качества могут спо...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::90f9393b-7ae3-42e3-a5f5-29c20451c2a9 / block_id 90f9393b-7ae3-42e3-a5f5-29c20451c2a9
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, необходима проверка на соответствие безопасности, проверка на соответствие этическим стандартам
- recommended_action: defer
- content_preview: *Эта практика не погружение в травму. Это встреча с тем, что застряло — с позиции того, кто уже прошёл через это.* ***
- llm_enrichment:
  - summary: Данная практика направлена на работу с застрявшими эмоциями и переживаниями, обеспечивая поддержку и понимание без углубления в травматические события.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::95c58778-e710-4ac7-95ae-9530bf55f3b1 / block_id 95c58778-e710-4ac7-95ae-9530bf55f3b1
- source_id: 123__кузница_духа
- chunk_type: case
- allowed_use: writer_context
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, Проверка точности интерпретации нейрофизиологических аспектов.
- recommended_action: defer
- content_preview: > Из сессии: > > **Марина, 41 год:** Когда я написала, что это голос похож на мою маму — я просто замерла. Я все эти годы думала, что это **я** так думаю. А это она всё это время говорила внутри меня. > > **Саламат:** Точно. И это не мисти…
- llm_enrichment:
  - summary: Обсуждение о влиянии голосов значимых людей на формирование нейронных паттернов и восприятие собственных мыслей.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::98527f7c-9223-4751-ae11-f201e6dc6558 / block_id 98527f7c-9223-4751-ae11-f201e6dc6558
- source_id: 123__кузница_духа
- chunk_type: practice
- allowed_use: writer_context, practice_suggestion
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, оценка качества самоанализа, проверка на соответствие безопасности
- recommended_action: defer
- content_preview: **Цель:** разобрать конкретный конфликт через линзу тени и проекции. **Время:** 20–30 минут. Возьми один реальный конфликт, который тебя беспокоит прямо сейчас. С конкретным человеком. Ответь письменно на три вопроса: **Вопрос 1:** Что име…
- llm_enrichment:
  - summary: Разбор конфликта с использованием линз тени и проекции, направленный на понимание собственных реакций и эмоций в отношении другого человека.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::99c31e75-b401-40df-96e5-c82c5cb11569 / block_id 99c31e75-b401-40df-96e5-c82c5cb11569
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки на соответствие безопасности, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: > **Из сессии** > > **Сергей, 44 года:** Я три месяца в этой пустоте. Пробовал всё — новый проект, поездки, смена работы. Всё равно пусто. Начал думать, что что-то сломалось. > > **Саламат:** А что если ничего не сломалось? Что если ты про…
- llm_enrichment:
  - summary: Сергей испытывает чувство пустоты и неопределенности после нескольких попыток изменить свою жизнь. Саламат предлагает рассмотреть ситуацию как возможность для остановки и саморазмышления.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::9ddf6440-7f67-4ad9-bfa9-dd6be134f8ec / block_id 9ddf6440-7f67-4ad9-bfa9-dd6be134f8ec
- source_id: 123__кузница_духа
- chunk_type: practice
- allowed_use: writer_context, practice_suggestion
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, необходимость проверки на соответствие безопасности, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: **Цель:** снизить интенсивность инстинктивной реакции через телесное заземление. **Время:** 5–10 минут в момент острой инстинктивной реакции. Когда инстинкт захватил — и ты это заметил — не пытайся думать его обратно. Кора не победит лимби…
- llm_enrichment:
  - summary: Рекомендация по снижению интенсивности инстинктивной реакции через телесное заземление. Практика направлена на использование физических ощущений для управления эмоциональными реакциями в моменты стресса.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::a15d79f8-0ac0-42fc-9bc3-6985a529fb07 / block_id a15d79f8-0ac0-42fc-9bc3-6985a529fb07
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: avoidance
- review_reasons: needs_human_review, необходимость проверки точности научных интерпретаций, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: Страх становится тюрьмой не сам по себе — а через один конкретный механизм: **избегание**. Когда человек избегает ситуации, которая вызывает страх — нервная система запоминает: «избегание сработало, угроза прошла». Это подкрепляет избегани…
- llm_enrichment:
  - summary: Избегание как механизм реакции на страх приводит к его усилению и сужению зоны жизни человека. Это явление объясняется нейропсихологическими процессами, которые закрепляют избегание как стратегию.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::a601e45d-9bef-4d6e-90df-0e8b6a1c8c1e / block_id a601e45d-9bef-4d6e-90df-0e8b6a1c8c1e
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки интерпретации, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: **— Я понял, что живу в оранжевом. Как перейти в зелёный?** — Никак. Не напрямую. Переход происходит, когда оранжевые инструменты исчерпывают себя перед реальным вызовом. Не в теории — на практике. Когда ты достиг всего — и внутри пусто. К…
- llm_enrichment:
  - summary: Переход от состояния оранжевого к зелёному происходит не через прямые действия, а через осознание и принятие внутренней пустоты, возникающей после достижения успеха. Это процесс, требующий времени и саморефлексии.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::ae905f5d-9ca4-40ed-88e4-d43f73e9afa8 / block_id ae905f5d-9ca4-40ed-88e4-d43f73e9afa8
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, необходимость проверки на соответствие контексту, потенциальная сложность интерпретации
- recommended_action: defer
- content_preview: *** Девять глав до этой — это была карта. Подробная, с масштабом, с легендой. Ты изучил рельеф: программу несовершенного Я, химию страдания, фильтры восприятия, тени, инстинкты, страхи, потоковые состояния. Ты понял, как работает автопилот…
- llm_enrichment:
  - summary: Текст обсуждает концепцию самосознания и восприятия реальности, акцентируя внимание на различии между теоретическим пониманием и практическим опытом. Он исследует внутренние механизмы, которые влияют на поведение и во...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::b05b4278-62cd-44e1-936e-24346e45b6ac / block_id b05b4278-62cd-44e1-936e-24346e45b6ac
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Проверка точности интерпретаций, Убедиться в соответствии с этическими стандартами
- recommended_action: defer
- content_preview: Самый ранний и самый плотный слой. Ребёнок усваивает: есть качества, которые «хорошие», и есть — которые «плохие». Злость — плохая. Послушание — хорошее. Эгоизм — плохой. Забота о других — хорошая. Сексуальность — стыдная. Чистота — правил…
- llm_enrichment:
  - summary: Ранние этапы формирования моральных качеств у детей связаны с усвоением понятий о 'хорошем' и 'плохом'. Эти категории влияют на эмоциональное развитие и восприятие себя и окружающих.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::b26c589d-4531-4cbb-b8ed-0d3c34d685c4 / block_id b26c589d-4531-4cbb-b8ed-0d3c34d685c4
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: avoidance
- review_reasons: needs_human_review, необходимость проверки точности интерпретаций, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: Один вопрос, который меняет рамку: «Если бы неудача этого проекта ничего не говорила обо мне как о человеке — только о проекте — ты бы начал?» Почти всегда ответ — «да». Потому что страх не в провале проекта. Страх в идентификации себя с р…
- llm_enrichment:
  - summary: Страх близости в отношениях часто связан с опасениями быть уязвимым и потерять контроль. Понимание этих страхов может помочь в их преодолении и улучшении взаимодействия с партнёром.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::b4bfea36-667a-447f-9631-0049b0f96f2f / block_id b4bfea36-667a-447f-9631-0049b0f96f2f
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Проверка на точность интерпретаций, Убедиться в отсутствии личных предположений
- recommended_action: defer
- content_preview: Мозг **переписывает** факт — добавляет к нему смысл, которого в самом факте не было. Коллега не поздоровался → «он на меня злится». Партнёр помолчал вечером → «что-то не так в наших отношениях». Руководитель написал коротко → «он недоволен…
- llm_enrichment:
  - summary: Человек склонен интерпретировать факты, добавляя к ним личные эмоции и предположения, что может привести к искажению реальности и негативным выводам о себе.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::b70ae542-7b02-463b-bfc3-46bfd37a0a19 / block_id b70ae542-7b02-463b-bfc3-46bfd37a0a19
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие контексту, Потенциальные риски неверного понимания
- recommended_action: defer
- content_preview: - «Будь сильным» — закрылся, не попросил помощи, сделал вид что всё нормально? - «Будь лучшим» — начал оправдываться, обесценил свой результат? - «Радуй других» — подавил своё, согласился с чужим? - «Старайся сильнее» — почувствовал, что с…
- llm_enrichment:
  - summary: Анализ поведения, связанного с внутренними конфликтами и социальным давлением, которое может привести к подавлению собственных эмоций и потребностей.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::b870528b-313c-46ef-b5a1-5266a4bedf2c / block_id b870528b-313c-46ef-b5a1-5266a4bedf2c
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие этическим стандартам, Потенциальные риски неправильного понимания
- recommended_action: defer
- content_preview: Здесь — важная оговорка. Потому что знание о спиральной динамике может стать новым инструментом программы. Программа «несовершенное Я» немедленно захватывает эту модель и начинает использовать её для сортировки людей: «он — синий, с ним бе…
- llm_enrichment:
  - summary: Использование модели спиральной динамики в программе может привести к неправильной интерпретации и оценке людей, что создает риск социальной дистанции и предвзятости.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::bb6d02e4-e12c-4e53-adf3-e854c53f382b / block_id bb6d02e4-e12c-4e53-adf3-e854c53f382b
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка на точность научных данных, проверка на соответствие контексту
- recommended_action: defer
- content_preview: Многие люди годами ходят на терапию — и при этом чувствуют, что топчутся на месте. «Я всё понимаю, но ничего не меняется». Это не значит, что терапия плохая. Это значит, что работа идёт преимущественно через **вербальный канал** — через сл…
- llm_enrichment:
  - summary: Терапия может не всегда приводить к изменениям, если работа ведется преимущественно через вербальный канал. Непереваренный опыт может храниться вне слов, что требует дополнительных подходов для обработки.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::bba54eed-9d56-461b-bf0c-bac28893ebb5 / block_id bba54eed-9d56-461b-bf0c-bac28893ebb5
- source_id: 123__кузница_духа
- chunk_type: practice
- allowed_use: writer_context, practice_suggestion
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, Необходима проверка на соответствие внутренним стандартам, Потенциальные риски неправильной интерпретации
- recommended_action: defer
- content_preview: **Цель:** обнаружить, где в теле хранится непереваренный опыт. **Время:** 20–25 минут.
- llm_enrichment:
  - summary: Рекомендуется провести анализ текста для выявления непереваренного опыта, что может помочь в улучшении понимания и интеграции информации. Процесс займет 20–25 минут.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::c3757cbe-4cfc-4e47-9a78-5fb785654f28 / block_id c3757cbe-4cfc-4e47-9a78-5fb785654f28
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка на соответствие контексту, проверка на точность и актуальность информации
- recommended_action: defer
- content_preview: ***
- llm_enrichment:
  - summary: Данный блок содержит теоретическую информацию, которая может быть полезна для понимания определенных концепций. Он предназначен для использования в контексте написания и не должен использоваться в качестве прямой цитаты.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::cb02003e-69b1-46da-9935-d7c29f67640b / block_id cb02003e-69b1-46da-9935-d7c29f67640b
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, оценка подхода к чувствительным темам, проверка точности научных данных
- recommended_action: defer
- content_preview: Ты уже видишь программу. Видишь драйверы. Замечаешь, как она включается. И всё равно — тянет обратно. Что-то тянет в знакомую тревогу, в привычное беспокойство, в старое «со мной что-то не так». Это не слабость воли. Это химия. В этой глав…
- llm_enrichment:
  - summary: Глава исследует связь между мозгом и страданием на молекулярном уровне, подчеркивая, что зависимость от негативных эмоций имеет биологическую основу.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::cb98214b-1a7d-45ab-87ec-4a801f1b391c / block_id cb98214b-1a7d-45ab-87ec-4a801f1b391c
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки интерпретаций, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: Работа с тенью движется линейно: «я вижу это в себе — и это меняет мои реакции». Фокус — на конкретных паттернах. Результат — реальные изменения в поведении и в отношениях. Простой тест: после сессии работы с тенью ты стал ближе к людям —…
- llm_enrichment:
  - summary: Работа с тенью предполагает линейное развитие самосознания, что может привести к изменениям в поведении и отношениях. Важно оценивать, как эти изменения влияют на близость к окружающим.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::cc979440-d02f-4bff-8920-59982597b4cc / block_id cc979440-d02f-4bff-8920-59982597b4cc
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки интерпретации эмоций, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: > Пример: > *Ситуация:* начальник сказал, что отчёт можно было сделать лучше. > *Тело:* сжатие в груди, жар в лице. > *Мысль:* «я облажался». > *Реакция:* начал оправдываться, пообещал переделать. > *Драйвер:* «будь лучшим» + «старайся сил…
- llm_enrichment:
  - summary: Анализ ситуации, в которой человек испытывает давление из-за ожиданий начальства, приводит к эмоциональным реакциям и внутренним конфликтам. Важно осознавать свои паттерны поведения и реакции на критику.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::cf618346-aa79-49e4-8756-0be86e889897 / block_id cf618346-aa79-49e4-8756-0be86e889897
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки на чувствительность, потенциальные риски неправильного толкования
- recommended_action: defer
- content_preview: Ещё более тонкая история: **твоё страдание стало частью твоей личности**. Ты так долго живёшь с ощущением «я недостаточен», что оно стало своим. Знакомым. И если убрать его — кто ты тогда? > Из сессии: > > — Устал страдать. Реально устал.…
- llm_enrichment:
  - summary: Исследование связи между личной идентичностью и хроническим страданием. Обсуждение того, как страдание может стать частью самовосприятия и как это влияет на желание изменить свою жизнь.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::d13ec321-be95-42ff-8ebc-87e903f7e9ce / block_id d13ec321-be95-42ff-8ebc-87e903f7e9ce
- source_id: 123__кузница_духа
- chunk_type: case
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки интерпретации эмоциональных реакций, потенциальная чувствительность темы
- recommended_action: defer
- content_preview: > **Азиз**, 33 года, менеджер в крупной компании. > > — Я не понимаю, почему меня так сильно задевает критика. Я знаю, что она конструктивная. Я умом понимаю, что начальник прав. Но у меня внутри — как будто меня ударили. > > — Ты помнишь,…
- llm_enrichment:
  - summary: Клиент испытывает сильные эмоциональные реакции на конструктивную критику, что может быть связано с детскими переживаниями. Важно исследовать корни этих реакций и их влияние на текущую жизнь.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::d24c9855-d738-4ef6-aead-c6051be65dce / block_id d24c9855-d738-4ef6-aead-c6051be65dce
- source_id: 123__кузница_духа
- chunk_type: practice
- allowed_use: writer_context, practice_suggestion
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, оценка качества анализа, проверка на соответствие безопасности
- recommended_action: defer
- content_preview: **Цель:** взять один реальный конфликт — и увидеть его как межуровневый, а не как личный. **Время:** 20–30 минут. Выбери один конфликт, в котором давно не можешь договориться. С партнёром, родителем, коллегой, другом. Ответь письменно:
- llm_enrichment:
  - summary: Анализ конфликта с фокусом на межуровневые аспекты, а не на личные. Участникам предлагается выбрать конфликт, который долго не удается разрешить, и описать его в письменной форме, чтобы выявить различные уровни взаимо...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::d4b3595f-b34e-47d1-ae3f-c5b293082f3c / block_id d4b3595f-b34e-47d1-ae3f-c5b293082f3c
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на точность интерпретаций, Потенциальные искажения в представлении информации
- recommended_action: defer
- content_preview: Начнём с фундамента. Каждый раз, когда ты что-то переживаешь — мозг записывает не само событие. Он записывает **твоё психоэмоциональное отношение к нему**. Это ключевое различие. Условно говоря: два человека попадают в одну и ту же ситуаци…
- llm_enrichment:
  - summary: Психоэмоциональное восприятие событий влияет на формирование воспоминаний и самооценки. Разные реакции на одни и те же ситуации могут привести к различным внутренним убеждениям.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::d527d369-beb2-4113-b370-cb2738e76b55 / block_id d527d369-beb2-4113-b370-cb2738e76b55
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, обеспечение соответствия безопасности, проверка точности интерпретации
- recommended_action: defer
- content_preview: Три причины, по которым программа «несовершенное Я» держится так крепко: **1. Нейропластичность в критический период** Мозг ребёнка — пластилин. Всё, что записалось в возрасте от 2 до 6 лет, записалось **на уровне базовой архитектуры**. Эт…
- llm_enrichment:
  - summary: Программа 'несовершенное Я' сохраняется благодаря нейропластичности в критический период и эмоциональной окраске, что влияет на формирование базовой архитектуры мозга и восприятие информации.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::d60e5a31-835c-4ce9-b14b-40b1706b6353 / block_id d60e5a31-835c-4ce9-b14b-40b1706b6353
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, Оценка качества рекомендаций, Проверка на соответствие безопасности
- recommended_action: defer
- content_preview: ***
- llm_enrichment:
  - summary: Этот блок предоставляет рекомендации по использованию диагностических линз для улучшения контекста написания. Он акцентирует внимание на необходимости соблюдения безопасности и требует дополнительной проверки.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::d8911af4-919c-4ea5-808c-5efada1eb0ca / block_id d8911af4-919c-4ea5-808c-5efada1eb0ca
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Проверка на соответствие безопасности, Убедиться в отсутствии директивных указаний
- recommended_action: defer
- content_preview: ***
- llm_enrichment:
  - summary: Предоставление рекомендаций по улучшению теоретических основ в контексте управления и анализа. Фокус на безопасных подходах к обогащению знаний без изменения существующих структур власти.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::d9f6dfb9-e6fe-4417-8df3-9c8991661af4 / block_id d9f6dfb9-e6fe-4417-8df3-9c8991661af4
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка точности интерпретации исследований.
- recommended_action: defer
- content_preview: Вытесненное содержание тени хранится не только в психике — оно хранится в теле. Это не метафора — это нейрофизиология. Исследования **Бессел ван дер Колка**, автора книги «Тело помнит всё», показали: травматические и вытесненные эмоциональ…
- llm_enrichment:
  - summary: Исследования показывают, что вытесненные эмоциональные паттерны могут проявляться в теле через хроническое напряжение, что связано с нейрофизиологией.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::dca9489e-c183-4b91-b55d-9f05372898cb / block_id dca9489e-c183-4b91-b55d-9f05372898cb
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Проверка на соответствие безопасности, Убедиться в корректности интерпретации концепций
- recommended_action: defer
- content_preview: **Мантра:** «Жизнь сакральна. Я — часть живого целого». **Что важно:** глобальные живые системы, сознание как основа реальности, холистическое восприятие. Разграничение «я» и «мир» ощущается как искусственное. Это редкое состояние — не кон…
- llm_enrichment:
  - summary: Тема рассматривает сакральность жизни и единство с глобальными живыми системами, подчеркивая важность холистического восприятия реальности. Ощущение единства между 'я' и 'миром' представляется как живое переживание, а...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::e0d0659a-e21e-467c-9f22-97cdd4721ced / block_id e0d0659a-e21e-467c-9f22-97cdd4721ced
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие контексту, Потенциальные риски неверной интерпретации концепции
- recommended_action: defer
- content_preview: Есть ещё один уровень информационного метаболизма, который почти никто не замечает. Мы живём в мире, где информации бесконечно много. Новости, соцсети, подкасты, книги, разговоры, видео. Каждый день — терабайты входящего. И мы потребляем в…
- llm_enrichment:
  - summary: Обсуждается концепция символического питания, которая относится к быстрому и поверхностному потреблению информации в современном мире, где доступно огромное количество контента.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::e49d8638-4f2d-4185-8e50-1726081a1654 / block_id e49d8638-4f2d-4185-8e50-1726081a1654
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, оценка соответствия контексту, проверка точности интерпретации
- recommended_action: defer
- content_preview: **Мантра:** «Есть правила — и им нужно следовать. Есть высший смысл». **Что важно:** дисциплина, ответственность, иерархия, долг. Правильное и неправильное — чётко разграничены. Есть высший авторитет: Бог, закон, традиция, государство. Жер…
- llm_enrichment:
  - summary: Текст подчеркивает важность дисциплины, ответственности и иерархии в обществе. Он акцентирует внимание на необходимости следовать установленным правилам и высшему авторитету, который может быть представлен в виде Бога...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::e796cd02-6301-489f-906b-716f76e8cd63 / block_id e796cd02-6301-489f-906b-716f76e8cd63
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие контексту, Проверка на точность интерпретации
- recommended_action: defer
- content_preview: Здесь необходимо остановиться отдельно. Это то место, которое не описано в большинстве книг по спиральной динамике — но именно здесь застревают умные, ищущие люди. Между **зелёным** и **жёлтым** — не просто очередной переход. Это **разрыв…
- llm_enrichment:
  - summary: Переход между зелёным и жёлтым уровнями в спиральной динамике представляет собой значимый разрыв, который требует глубокого понимания и осознания. Этот этап может быть сложным для людей, стремящихся к самосовершенство...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::e7b8c0fd-aafd-47df-85d5-603b2ce5ae7f / block_id e7b8c0fd-aafd-47df-85d5-603b2ce5ae7f
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходимость уточнения контекста, проверка на соответствие безопасности
- recommended_action: defer
- content_preview: Вернёмся к лиссофобии — страху потерять себя при исследовании себя. Потому что это не просто страх, о котором можно рассказать и пойти дальше. Это структурный вопрос всей работы с сознанием. Когда человек начинает видеть свои программы — о…
- llm_enrichment:
  - summary: Лиссофобия представляет собой глубокий страх, связанный с самопознанием и осознанием своих автоматических реакций и убеждений. Это явление может быть как освобождающим, так и пугающим, поскольку требует переосмысления...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::ebf047f2-c678-40a1-8747-b98dfae1a2ea / block_id ebf047f2-c678-40a1-8747-b98dfae1a2ea
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие контексту, Потенциальные риски неверного понимания
- recommended_action: defer
- content_preview: **Базовая установка:** «Показывать слабость = опасно» Ребёнок плачет. Родитель говорит: «Не реви. Ты же мальчик» / «Хватит ныть, ты уже большая». Или просто игнорирует — показывает всем своим видом, что чувства неуместны. Мозг ребёнка дела…
- llm_enrichment:
  - summary: Детские эмоции часто подавляются родителями, что формирует у ребенка убеждение о неприемлемости своих чувств. Это может привести к трудностям во взрослом возрасте, включая неспособность просить о помощи.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::ec985517-5548-4d75-b7f5-24d7e1de79ab / block_id ec985517-5548-4d75-b7f5-24d7e1de79ab
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки точности интерпретаций, потенциальные нюансы в понимании концепций
- recommended_action: defer
- content_preview: Это тонкое, но важное различие. **Программа «несовершенное Я»** — это психологический слой. Она формируется в детстве через опыт, отношения, послания среды. Она работает с образом себя: «я недостаточно хороший». **Инстинкт** — это биологич…
- llm_enrichment:
  - summary: Различие между психологическим слоем, формируемым в детстве, и биологическим слоем инстинктов, существующим с древних времен. Психологический слой связан с образом себя, в то время как инстинкты ориентированы на выжив...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::ee024cf7-74d8-4cab-8b58-ce89e2cd880c / block_id ee024cf7-74d8-4cab-8b58-ce89e2cd880c
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, обеспечение соответствия безопасности, проверка точности интерпретаций
- recommended_action: defer
- content_preview: Вот то, о чём редко говорят — и что меняет всё. Программа «несовершенное Я» не исчезает при переходе на «следующий уровень». Она **меняет костюм**. | Уровень | Что говорит программа | | :-- | :-- | | Красный | «Ты недостаточно сильный — до…
- llm_enrichment:
  - summary: Программа 'несовершенное Я' продолжает влиять на восприятие себя на разных уровнях, изменяя внутренние установки и самооценку.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::eed49fa0-58cb-475a-b72d-3eca72995c9b / block_id eed49fa0-58cb-475a-b72d-3eca72995c9b
- source_id: 123__кузница_духа
- chunk_type: theory
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка на соответствие контексту, проверка на возможность использования в других контекстах
- recommended_action: defer
- content_preview: ***
- llm_enrichment:
  - summary: Данный блок содержит теоретическую информацию, которая может быть полезна для понимания определенных концепций. Он предназначен для использования в контексте написания и не должен использоваться в качестве прямых цитат.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::f3299182-733f-4c63-8622-b7cc456f68f7 / block_id f3299182-733f-4c63-8622-b7cc456f68f7
- source_id: 123__кузница_духа
- chunk_type: case
- allowed_use: writer_context
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, Необходима проверка на соответствие этическим стандартам, Проверка на наличие потенциальных рисков для клиентов
- recommended_action: defer
- content_preview: **Цель:** встретиться со страхом потери идентичности — намеренно и постепенно. **Время:** 15–20 минут. Для тех, кто работает с вопросами идентичности. Сядь в тишине. Закрой глаза. Начни с простого наблюдения: замечай мысли, которые приходя…
- llm_enrichment:
  - summary: Методика для работы с страхом потери идентичности, основанная на наблюдении за мыслями и внутреннем диалоге. Рекомендуется проводить в тишине, сосредоточившись на процессе осознания.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::f5716360-1635-4026-8568-3404b4569d2a / block_id f5716360-1635-4026-8568-3404b4569d2a
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие контексту и целям использования.
- recommended_action: defer
- content_preview: Позже — подростковый возраст, социальная среда — ребёнок начинает понимать, кем «надо быть» в своей группе. Если ты растёшь в среде, где «умный — значит слабый», интеллект идёт в тень. Если среда говорит «чувствовать — стыдно», чувства ухо…
- llm_enrichment:
  - summary: В подростковом возрасте социальная среда начинает оказывать значительное влияние на самоидентификацию и восприятие себя. Важно понимать, как культурные и социальные нормы могут формировать представления о том, что счи...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::f648d244-df01-4d43-a130-bea5dada3ccf / block_id f648d244-df01-4d43-a130-bea5dada3ccf
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, Необходима проверка на соответствие контексту, Потенциальные риски неверного толкования
- recommended_action: defer
- content_preview: **Базовая установка:** «Времени всегда мало. Надо успеть» Атмосфера вечного цейтнота. «Быстрее! Мы опаздываем! Ты как черепаха!». Вывод: **«Времени всегда не хватает. Я всегда опаздываю»**. Во взрослой жизни — ты не можешь быть в настоящем…
- llm_enrichment:
  - summary: В современном мире люди часто испытывают нехватку времени, что приводит к постоянному стрессу и невозможности сосредоточиться на настоящем моменте. Это создает атмосферу спешки и тревоги, где внимание сосредоточено на...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::f68050f9-d789-4d8b-b5b1-d6302ddfb88e / block_id f68050f9-d789-4d8b-b5b1-d6302ddfb88e
- source_id: 123__кузница_духа
- chunk_type: practice
- allowed_use: writer_context, diagnostic_lens, practice_suggestion
- safety_flags: not_for_direct_quote, requires_grounding, practice_requires_low_resource_check
- lens_family: -
- review_reasons: needs_human_review, необходимость проверки на соответствие безопасности, потенциальные эмоциональные триггеры
- recommended_action: defer
- content_preview: **Шаг 1: Триггер** Что-то случается — начальник делает замечание, партнёр не отвечает, кто-то посмотрел не так. Само по себе — просто факт. Нейтральное событие. **Шаг 2: Мгновенная оценка (0,2 секунды)** Лимбическая система мгновенно скани…
- llm_enrichment:
  - summary: Процесс реагирования на триггеры включает в себя мгновенную оценку ситуации, основанную на предыдущем опыте, что может привести к эмоциональной реакции.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::f6cbdc2c-0bf7-4d5e-a828-b305fdb72c89 / block_id f6cbdc2c-0bf7-4d5e-a828-b305fdb72c89
- source_id: 123__кузница_духа
- chunk_type: lens
- allowed_use: writer_context, diagnostic_lens
- safety_flags: not_for_direct_quote, requires_grounding
- lens_family: -
- review_reasons: needs_human_review, Оценка безопасности использования, Проверка на соответствие контексту
- recommended_action: defer
- content_preview: **Мантра:** «Я могу добиться всего, если приложу усилия. Результат важнее правил». **Что важно:** личный успех, конкуренция, рациональность, прогресс. Законы природы познаваемы и используемы. Наука, технологии, рынок — инструменты достижен…
- llm_enrichment:
  - summary: Данный блок фокусируется на личном успехе и стратегическом мышлении, подчеркивая важность усилий и рационального подхода к достижению целей. Он рассматривает использование науки и технологий как инструменты для прогре...
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::fb24a1e9-848d-452d-a160-d4020fa727cd / block_id fb24a1e9-848d-452d-a160-d4020fa727cd
- source_id: 123__кузница_духа
- chunk_type: quote
- allowed_use: writer_context
- safety_flags: not_for_direct_quote
- lens_family: -
- review_reasons: needs_human_review, необходима проверка на соответствие безопасности, проверка на наличие потенциально тревожного контента
- recommended_action: defer
- content_preview: **Базовый вопрос:** «Достаточно ли у меня ресурсов, чтобы выжить?» **Что он отслеживает:** безопасность, здоровье, деньги, еда, комфорт, жильё, энергия, стабильность. Постоянный фоновый мониторинг: «у меня достаточно? я в безопасности? что…
- llm_enrichment:
  - summary: Пользователь задает вопрос о достаточности ресурсов для выживания, что отражает его стремление к безопасности и стабильности. Важно отслеживать состояние здоровья, финансов, продовольствия и жилья.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:

#### post_reprocess::fb92553a-a1b4-4c6f-81c5-47f29c3e2dd6 / block_id fb92553a-a1b4-4c6f-81c5-47f29c3e2dd6
- source_id: 123__кузница_духа
- chunk_type: case
- allowed_use: writer_context
- safety_flags: not_for_direct_quote, practice_requires_low_resource_check
- lens_family: somatic
- review_reasons: needs_human_review, Проверка на эмоциональную целостность, Убедиться в отсутствии директивных указаний
- recommended_action: defer
- content_preview: **Цель:** найти золотую тень — вытесненные позитивные качества. **Время:** 20–30 минут. Та же структура — но теперь про восхищение. Напиши имена или описания людей, которыми ты восхищаешься непропорционально. Не просто «уважаю» — а что-то…
- llm_enrichment:
  - summary: Исследование восхищения и вытесненных позитивных качеств, направленное на выявление личных качеств, которые вызывают сильные эмоции и стремление к их достижению.
  - tags:
  - lens_family_candidates:
  - use_when:
  - avoid_when:
  - confidence:
- reviewer_notes:
- suggested_decision_slot:
