# PRD-047.29 Live Pilot Smoke Report

- generated_at: `2026-06-23T06:55:34.749436+00:00`
- base_url: `http://127.0.0.1:8001`
- fixture_path: `TO_DO_LIST/fixtures/PRD-047.29/current_pipeline_simplification_cases_ru.jsonl`
- case_count: `8`
- passed_count: `8`
- blocked_count: `0`
- status: `passed`

## Cases

### P29-001 - Explicit no-practice pushback
- status: `passed`
- latest_turn_constraints: `no_practice`
- kb_visible_to_writer: `True`
- semantic_cards_visible_to_writer: `True`
- final_directive_mode: `answer_directly_without_practice`
- practice_blocked_by_user_request: `True`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Понимать, почему вас так злит поведение близкого, — это не про «вы сумасшедший/перестаньте», а про смысловые слои за эмоцией. Кратко и по сути — злость обычно сигнализирует о том, что какое‑то ваше важное ожидание, потребность или граница б`

### P29-002 - Alternatives beyond breathing
- status: `passed`
- latest_turn_constraints: `no_breathing_only`
- kb_visible_to_writer: `True`
- semantic_cards_visible_to_writer: `True`
- final_directive_mode: `answer_with_non_breathing_alternatives`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Коротко — нет, дыхание не единственный способ повлиять на состояние нервной системы. Ниже — структурированное объяснение ключевых альтернатив, как они действуют и в каких ситуациях могут быть полезны. Я не даю пошаговых упражнений, а описыв`

### P29-003 - Simplify after complexity
- status: `passed`
- latest_turn_constraints: `simplify`
- kb_visible_to_writer: `True`
- semantic_cards_visible_to_writer: `True`
- final_directive_mode: `simplified_direct_answer`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Твой мозг автоматически читает обычное событие как «угрозу» — и запускает эмоцию (тревога, стыд, злость) и реакцию (контроль, оправдания или уход).  

Проще: что‑то случилось → внутри сработал фильтр «со мной что‑то не так» → ты почувствова`

### P29-004 - Long-term perspective requested
- status: `passed`
- latest_turn_constraints: `long_term_perspective`
- kb_visible_to_writer: `True`
- semantic_cards_visible_to_writer: `True`
- final_directive_mode: `long_term_frame_first`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Сделайте один конкретный шаг прямо сейчас: заведите простую еженедельную «тёплую» тетрадь злости — записывайте по 10–15 минут раз в неделю, что вызвало злость, какие мысли и тело при этом, как вы отреагировали и что вы хотели бы сделать по‑`

### P29-005 - No internal DB grounding
- status: `passed`
- latest_turn_constraints: `no_internal_db`
- kb_visible_to_writer: `False`
- semantic_cards_visible_to_writer: `False`
- final_directive_mode: `answer_without_internal_db_grounding`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Программа «Несовершенное Я» — это образное название внутренней установки или «части» личности, которая признаёт: я не идеален, у меня есть ошибки, ограничения и не всегда всё получается. Простыми словами — это разрешение себе быть неидеальн`

### P29-006 - Direct KB question still allowed
- status: `passed`
- latest_turn_constraints: `none`
- kb_visible_to_writer: `True`
- semantic_cards_visible_to_writer: `True`
- final_directive_mode: `structured_explanation`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Коротко и по сути.

1) Определение
Программа «Несовершенное Я» — это образное название устоявшегося внутреннего автомата восприятия, который постоянно интерпретирует обычные события как подтверждение мысли «со мной что‑то не так», «я неудач`

### P29-007 - Safety case with no practice
- status: `passed`
- latest_turn_constraints: `no_practice`
- kb_visible_to_writer: `True`
- semantic_cards_visible_to_writer: `True`
- final_directive_mode: `answer_directly_without_practice`
- practice_blocked_by_user_request: `True`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Я здесь. Ты не один. Если тебе сейчас очень тяжело, можно позвонить на линию психологической помощи.`

### P29-008 - Combined simplify plus long-term plus no-breathing
- status: `passed`
- latest_turn_constraints: `no_breathing_only, simplify, long_term_perspective`
- kb_visible_to_writer: `True`
- semantic_cards_visible_to_writer: `True`
- final_directive_mode: `simplified_direct_answer`
- practice_blocked_by_user_request: `False`
- warnings: `none`
- mismatches: `none`
- answer_excerpt: `Просто: «взрыв» — это ваш мозг, который чувствует потерю контроля (времени, статуса или ценностей) и включает крайнее средство — резкую реакцию. Чтобы этого было меньше, нужно не учиться дышать в моменте, а менять причину и систему в долгой`
