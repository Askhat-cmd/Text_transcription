# PRD-047.30 Live Pilot Smoke Report

- generated_at: `2026-06-24T04:35:11.889157+00:00`
- base_url: `http://127.0.0.1:8001`
- fixture_path: `TO_DO_LIST/fixtures/PRD-047.30/writer_input_authority_cases_ru.jsonl`
- case_count: `10`
- passed_count: `10`
- blocked_count: `0`
- status: `passed`

## Cases

### P30-001 - Emotional support without KB pressure
- status: `passed`
- latest_turn_constraints: `none`
- kb_visible_to_writer: `False`
- semantic_cards_visible_to_writer: `False`
- visibility_reason: `non_kb_emotional_support_turn`
- final_directive_mode: `structured_explanation`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Понимаю — это звучит очень тяжело. Ты злишься на начальника и при этом чувствуешь растерянность: «что со мной» — как будто реакция выходит за рамки ожидаемого. Давай посмотрим, что могло это породить, чтобы стало понятнее.

1) Что происходи`

### P30-002 - Anger without term request
- status: `passed`
- latest_turn_constraints: `none`
- kb_visible_to_writer: `False`
- semantic_cards_visible_to_writer: `False`
- visibility_reason: `non_kb_emotional_support_turn`
- final_directive_mode: `structured_explanation`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Это важное и понятное наблюдение — спасибо, что написал(а). Коротко и ясно — здесь обычно работает такой механизм:

1) Триггер и мгновенная реакция. Что-то задевает — ощущение угрозы, фрустрации или несправедливости — и тело/ум быстро отвеч`

### P30-003 - Direct KB question
- status: `passed`
- latest_turn_constraints: `none`
- kb_visible_to_writer: `True`
- semantic_cards_visible_to_writer: `True`
- visibility_reason: `direct_knowledge_question`
- final_directive_mode: `structured_explanation`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Программа «Несовершенное Я» — это образное название внутренней автоматической схемы восприятия и интерпретации опыта, которая быстро переводит любую ситуацию в вывод «со мной что‑то не так» / «я недостаточен» / «я плохой». Это не диагноз и `

### P30-004 - Concept explanation allowed
- status: `passed`
- latest_turn_constraints: `none`
- kb_visible_to_writer: `True`
- semantic_cards_visible_to_writer: `True`
- visibility_reason: `direct_knowledge_question`
- final_directive_mode: `structured_explanation`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Коротко — потому что «понимание» работает на одном уровне (когнитивном, обученном сознанием), а реакция часто запускается на другом (автоматическом, эмоционально‑физиологическом). Ниже — структурированное объяснение механизма, пример и крат`

### P30-005 - No internal DB hard suppression
- status: `passed`
- latest_turn_constraints: `no_internal_db`
- kb_visible_to_writer: `False`
- semantic_cards_visible_to_writer: `False`
- visibility_reason: `latest_turn_no_internal_db`
- final_directive_mode: `answer_without_internal_db_grounding`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Хорошо. Ключевой механизм — это простая цепочка: событие → мысль (оценка) → эмоция → реакция. Объясню своими словами, коротко и по сути.

1) Что это значит  
- Событие — то, что произошло: чья‑то фраза, ситуация, телесное ощущение.  
- Мысл`

### P30-006 - Simplify repair becomes trace only
- status: `passed`
- latest_turn_constraints: `simplify`
- kb_visible_to_writer: `False`
- semantic_cards_visible_to_writer: `False`
- visibility_reason: `repair_turn`
- final_directive_mode: `simplified_direct_answer`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Понял — проще так:

1) Заметь, что происходит внутри: мысль, чувство, телесная реакция.  
2) Найди мысль, которая это запускает.  
3) Измени что‑то маленькое — и реакция поменяется.

Хочешь — пришли конкретную фразу, я перепишу ещё короче.`

### P30-007 - Practice pushback keeps grounding hidden
- status: `passed`
- latest_turn_constraints: `no_practice`
- kb_visible_to_writer: `False`
- semantic_cards_visible_to_writer: `False`
- visibility_reason: `repair_turn`
- final_directive_mode: `answer_directly_without_practice`
- practice_blocked_by_user_request: `True`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Понял — без практики, просто пояснить. Под «объясни нормально» я буду делать так: кратко дать определение понятия, объяснить простыми словами главную идею, привести один понятный пример и коротко сказать, зачем это может пригодиться.  

Сей`

### P30-008 - Safety boundary can keep grounding
- status: `passed`
- latest_turn_constraints: `none`
- kb_visible_to_writer: `True`
- semantic_cards_visible_to_writer: `True`
- visibility_reason: `safety_grounding_allowed`
- final_directive_mode: `direct_answer`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Понимаю — это пугающее ощущение. Я не могу поставить диагноз по тексту, но помогу быстро сориентироваться и чуть успокоить.

Коротко о механизмах (чтобы увидеть, что происходит):
- Паника/тревога: сжатие в груди часто связано с напряжением `

### P30-009 - Context follow-up should not force KB
- status: `passed`
- latest_turn_constraints: `none`
- kb_visible_to_writer: `False`
- semantic_cards_visible_to_writer: `False`
- visibility_reason: `contextual_followup_without_knowledge_need`
- final_directive_mode: `structured_explanation`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Коротко пройдусь по каждому из «пяти драйверов» и покажу типичные поведенческие паттерны в обычной ссоре с начальником — что происходит автоматически и как это выглядит в словах/тоне/действиях.

1) «Будь совершенным» (Be Perfect)  
- Что вн`

### P30-010 - Direct source request keeps KB visible
- status: `passed`
- latest_turn_constraints: `none`
- kb_visible_to_writer: `True`
- semantic_cards_visible_to_writer: `True`
- visibility_reason: `direct_source_request`
- final_directive_mode: `direct_answer`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `В базе говорится, что «пять драйверов» — это не черты характера, а выученные внутренние «команды» или правила, которые автоматизированно подталкивают поведение в попытке снизить тревогу, получить безопасность или одобрение. Их полезность — `
