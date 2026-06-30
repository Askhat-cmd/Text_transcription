# PRD-047.36-HF2 Retrieval Recall Audit

- backend_base_url: `http://127.0.0.1:8001`
- botdb_base_url: `http://127.0.0.1:8003`
- source_material_phrase_present_in_workspace: `True`

## A1
- query: `Что такое анестетическая депрессия?`
- classification: `FAIL_raw_source_missing`
- loss_stage: `raw_source`
- loss_reason: `no_raw_source_match_in_runtime_top_k`
- best_raw_match: `e796cd02-6301-489f-906b-716f76e8cd63`
- best_runtime_match: `99c31e75-b401-40df-96e5-c82c5cb11569`
- payload_match: `99c31e75-b401-40df-96e5-c82c5cb11569`
- answer_preview: `Анестетическая депрессия — это состояние эмоциональной «пустоты» или онемения: человек продолжает функционировать (работа, обязанности, поведение в целом), но не испытывает ни боли, ни радости — словно под стеклянным колпаком. Главный механизм: нервная сист...`

## A2
- query: `анестетическая депрессия это ведь еще и психологический термин, что ты знаешь об этом?`
- classification: `FAIL_raw_source_missing`
- loss_stage: `raw_source`
- loss_reason: `no_raw_source_match_in_runtime_top_k`
- best_raw_match: `99c31e75-b401-40df-96e5-c82c5cb11569`
- best_runtime_match: `99c31e75-b401-40df-96e5-c82c5cb11569`
- payload_match: `99c31e75-b401-40df-96e5-c82c5cb11569`
- answer_preview: `Коротко — да: «анестетическая депрессия» в психологическом употреблении обычно описывает состояние эмоционального оцепенения или пустоты (эмоциональная «анестезия»), когда человек чувствует пустоту, апатию и потерю смысла, несмотря на отсутствие ярко выраже...`

## A3
- query: `Так стоп! Что такое анестетическая депрессия в Нейросталкинге?`
- classification: `FAIL_raw_source_missing`
- loss_stage: `raw_source`
- loss_reason: `no_raw_source_match_in_runtime_top_k`
- best_raw_match: `99c31e75-b401-40df-96e5-c82c5cb11569`
- best_runtime_match: `99c31e75-b401-40df-96e5-c82c5cb11569`
- payload_match: `99c31e75-b401-40df-96e5-c82c5cb11569`
- answer_preview: `Анестетическая депрессия в нейросталкинге — это состояние, когда нервная система «онемела»: эмоции и телесные ощущения притупляются, интерес и мотивация как будто выключаются. Один главный механизм — эмоциональное онемение: мозг снижает чувствительность, чт...`

## A4
- query: `Что такое программа несовершенное Я?`
- classification: `PASS_source_found_and_payload_visible`
- loss_stage: `none`
- loss_reason: ``
- best_raw_match: `d527d369-beb2-4113-b370-cb2738e76b55`
- best_runtime_match: `d527d369-beb2-4113-b370-cb2738e76b55`
- payload_match: `d527d369-beb2-4113-b370-cb2738e76b55`
- answer_preview: `Программа «несовершенное Я» — это устойчивая внутренняя схема или автоматическая реакция, которая убеждает вас, что вы «недостаточны» или «не такой, как нужно», и запускает чувства стыда, тревоги и попытки исправить себя. Главный механизм: эмоциональная авт...`

## A5
- query: `Назови пять драйверов выживания.`
- classification: `INCONCLUSIVE_missing_trace_or_insufficient_fields`
- loss_stage: `unknown`
- loss_reason: `not_an_explicit_knowledge_question`
- best_raw_match: `5808a31f-2872-4e48-826c-b318bf0d60b0`
- best_runtime_match: `5808a31f-2872-4e48-826c-b318bf0d60b0`
- payload_match: `none`
- answer_preview: `Я слышу тебя. Расскажи больше, если хочешь.`

## A6
- query: `Что значит страдание как безопасность?`
- classification: `PASS_source_found_and_payload_visible`
- loss_stage: `none`
- loss_reason: ``
- best_raw_match: `2a2ffcc2-89c6-41f2-bb53-3188eac08875`
- best_runtime_match: `2a2ffcc2-89c6-41f2-bb53-3188eac08875`
- payload_match: `2a2ffcc2-89c6-41f2-bb53-3188eac08875`
- answer_preview: `Коротко: «страдание как безопасность» — это поведение, когда человек сознательно или бессознательно выбирает страдать, потому что это кажется способом снизить риск: страдание сигнализирует подчинение и даёт иллюзию контроля над будущей болью. Главный механи...`

## A7
- query: `Что такое контролёр в панике?`
- classification: `FAIL_raw_source_missing`
- loss_stage: `raw_source`
- loss_reason: `no_raw_source_match_in_runtime_top_k`
- best_raw_match: `5be3f5b0-a073-4c15-8ed6-429ad22c029b`
- best_runtime_match: `5be3f5b0-a073-4c15-8ed6-429ad22c029b`
- payload_match: `semantic_card:panic_control_support_v1`
- answer_preview: `Контролёр в панике — это поведение (или роль), когда человек пытается усиленно управлять событиями, людьми или собой в ответ на сильный страх или тревогу. Главный механизм: желание восстановить предсказуемость и безопасность — контроль снижает неопределённо...`

## A8
- query: `Что такое духовная кома?`
- classification: `FAIL_raw_source_missing`
- loss_stage: `raw_source`
- loss_reason: `no_raw_source_match_in_runtime_top_k`
- best_raw_match: `6d484c8a-f7f0-407e-99e5-d35048f7b48d`
- best_runtime_match: `6d484c8a-f7f0-407e-99e5-d35048f7b48d`
- payload_match: `semantic_card:program_imperfect_self_v1`
- answer_preview: `Духовная кома — это образное описание состояния, когда человек эмоционально и смыслово «отключается»: теряет интерес к ценностям, утрачивает внутреннюю мотивацию и чувствует пустоту или апатию, как будто душевная жизнь притупилась. Главный механизм здесь —...`

