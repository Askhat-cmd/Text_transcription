# PRD-047.27-HF2 Owner Web Chat Parity Report

- backend_pid: `17324`
- backend_start_time: `2026-06-19T10:21:51.296803+00:00`
- backend_port_or_endpoint: `http://127.0.0.1:8001/api/v1/questions/adaptive-stream`
- app_env: `local`
- semantic_cards_pilot_enabled: `True`
- semantic_cards_pilot_enabled_source: `env`
- semantic_cards_pilot_raw_value: `true`
- semantic_cards_pack_id: `semantic_cards_pilot_v1`
- semantic_cards_loaded_count: `12`

## Cases

### case_01_contact
- query: `Привет, я Максим. Можешь мне отвечать на вопросы?`
- dialogue_act: `greeting`
- answer_obligation: `continue_thread`
- must_answer: `Привет, я Максим. Можешь мне отвечать на вопросы?`
- selected_card_ids: `—`
- writer_payload_enriched: `False`
- semantic_card_id_visible: `False`

### case_02_imperfect_self
- query: `Что такое программа Несовершенное Я?`
- dialogue_act: `knowledge_question`
- answer_obligation: `answer_knowledge_question`
- must_answer: `Что такое программа Несовершенное Я?`
- selected_card_ids: `program_imperfect_self_v1`
- writer_payload_enriched: `True`
- semantic_card_id_visible: `False`

### case_03_awareness
- query: `Что такое осознанность? и как она освещена в теме нейросталкинга?`
- dialogue_act: `knowledge_question`
- answer_obligation: `answer_knowledge_question`
- must_answer: `Что такое осознанность? и как она освещена в теме нейросталкинга?`
- selected_card_ids: `neurostalking_basic_lens_v1, control_as_safety_v1, program_imperfect_self_v1`
- writer_payload_enriched: `True`
- semantic_card_id_visible: `False`

### case_04_work_lie
- query: `Давай на примере. Я разговариваю на работе с коллегой и вижу что он врет, но по должности он выше, и я не хочу его при всех уличать во лжи`
- dialogue_act: `concrete_situation_question`
- answer_obligation: `answer_concrete_situation`
- must_answer: `Давай на примере. Я разговариваю на работе с коллегой и вижу что он врет, но по должности он выше, и я не хочу его при всех уличать во лжи`
- selected_card_ids: `program_imperfect_self_v1`
- writer_payload_enriched: `True`
- semantic_card_id_visible: `True`

### case_05_anger
- query: `а что делать с гневом, меня распирает от ненависти когда я вижу как кто то врет!`
- dialogue_act: `concrete_situation_question`
- answer_obligation: `answer_concrete_situation`
- must_answer: `а что делать с гневом, меня распирает от ненависти когда я вижу как кто то врет!`
- selected_card_ids: `control_as_safety_v1, program_imperfect_self_v1`
- writer_payload_enriched: `True`
- semantic_card_id_visible: `True`

### case_06_no_practice_cause
- query: `мне не нужна практика, я просто хочу понять как быть с самой причиной гнева а не с ее последствиями!`
- dialogue_act: `concrete_situation_question`
- answer_obligation: `answer_concrete_situation`
- must_answer: `мне не нужна практика, я просто хочу понять как быть с самой причиной гнева а не с ее последствиями!`
- selected_card_ids: `one_bounded_practice_not_self_improvement_whip_v1, control_as_safety_v1`
- writer_payload_enriched: `True`
- semantic_card_id_visible: `True`
