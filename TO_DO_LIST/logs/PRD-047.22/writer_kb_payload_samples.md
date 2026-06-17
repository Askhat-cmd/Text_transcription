# PRD-047.22 Writer KB Payload Samples

## known_concept_neurostalking
                - query: что такое Нейросталкинг?
                - payload_chunk_count: 1
                - original_char_count: 228
                - sent_char_count: 116
                - content_truncated: true
                - truncation_strategy: paragraph_then_sentence_boundary
                - truncated_mid_sentence: false
                - overlay_metadata_used: false

                ```text
                version=writer_kb_payload_v1
chunk_count=1
total_sent_char_count=116

[KB-1]
chunk_id=kb-neuro-1
source_doc=Кузница Духа
chunk_type=concept
quote_policy=paraphrase_only
allowed_use=direct_to_writer
core_thesis=**Нейросталкинг** — это наблюдение за триггерами, автоматическими реакциями и повторяющимися внутренними паттернами.
content_excerpt:
**Нейросталкинг** — это наблюдение за триггерами, автоматическими реакциями и повторяющимися внутренними паттернами.
writer_instruction=Use as grounding. Paraphrase. Do not dump raw quote.
content_truncated=true
truncation_strategy=paragraph_then_sentence_boundary
                ```

## mechanism_control_as_safety
                - query: почему меня так тянет всё контролировать?
                - payload_chunk_count: 1
                - original_char_count: 209
                - sent_char_count: 125
                - content_truncated: true
                - truncation_strategy: paragraph_then_sentence_boundary
                - truncated_mid_sentence: false
                - overlay_metadata_used: false

                ```text
                version=writer_kb_payload_v1
chunk_count=1
total_sent_char_count=125

[KB-1]
chunk_id=kb-mech-1
source_doc=Кузница Духа
chunk_type=mechanism
quote_policy=paraphrase_only
allowed_use=direct_to_writer
core_thesis=Контроль как безопасность — это механизм, при котором человек цепляется за контроль не ради порядка, а ради снижения тревоги.
content_excerpt:
Контроль как безопасность — это механизм, при котором человек цепляется за контроль не ради порядка, а ради снижения тревоги.
writer_instruction=Use as grounding. Paraphrase. Do not dump raw quote.
content_truncated=true
truncation_strategy=paragraph_then_sentence_boundary
                ```

## diagnostic_lens_shame_visibility
                - query: почему мне стыдно когда меня видят?
                - payload_chunk_count: 1
                - original_char_count: 207
                - sent_char_count: 110
                - content_truncated: true
                - truncation_strategy: paragraph_then_sentence_boundary
                - truncated_mid_sentence: false
                - overlay_metadata_used: false

                ```text
                version=writer_kb_payload_v1
chunk_count=1
total_sent_char_count=110

[KB-1]
chunk_id=kb-lens-1
source_doc=Кузница Духа
chunk_type=diagnostic_lens
quote_policy=paraphrase_only
allowed_use=direct_to_writer
core_thesis=Линза стыда и видимости помогает замечать момент, когда человеку невыносимо быть увиденным в своей уязвимости.
content_excerpt:
Линза стыда и видимости помогает замечать момент, когда человеку невыносимо быть увиденным в своей уязвимости.
writer_instruction=Use as grounding. Paraphrase. Do not dump raw quote.
content_truncated=true
truncation_strategy=paragraph_then_sentence_boundary
                ```

## practice_stop_frame
                - query: какая практика поможет замедлиться перед реакцией?
                - payload_chunk_count: 1
                - original_char_count: 295
                - sent_char_count: 137
                - content_truncated: true
                - truncation_strategy: word_boundary
                - truncated_mid_sentence: true
                - overlay_metadata_used: false

                ```text
                version=writer_kb_payload_v1
chunk_count=1
total_sent_char_count=137

[KB-1]
chunk_id=kb-practice-1
source_doc=Кузница Духа
chunk_type=practice
quote_policy=paraphrase_only
allowed_use=direct_to_writer
core_thesis=Практика стоп-кадр предлагает на несколько секунд остановить автоматическую реакцию и отдельно заметить три слоя: мысль, телесный импульс и желание немедленно защититься.
content_excerpt:
Практика стоп-кадр предлагает на несколько секунд остановить автоматическую реакцию и отдельно заметить три слоя: мысль, телесный импульс
writer_instruction=Use as grounding. Paraphrase. Do not dump raw quote.
content_truncated=true
truncation_strategy=word_boundary
                ```

## irrelevant_no_kb_case
                - query: какая у тебя архитектура?
                - payload_chunk_count: 1
                - original_char_count: 75
                - sent_char_count: 75
                - content_truncated: false
                - truncation_strategy: none
                - truncated_mid_sentence: false
                - overlay_metadata_used: false

                ```text
                version=writer_kb_payload_v1
chunk_count=1
total_sent_char_count=75

[KB-1]
chunk_id=kb-none-1
source_doc=Generic Bot Notes
chunk_type=general_text
quote_policy=paraphrase_only
allowed_use=writer_support
core_thesis=Короткая справка по общему устройству бота без психологического содержания.
content_excerpt:
Короткая справка по общему устройству бота без психологического содержания.
writer_instruction=Use as grounding. Paraphrase. Do not dump raw quote.
content_truncated=false
truncation_strategy=none
                ```
