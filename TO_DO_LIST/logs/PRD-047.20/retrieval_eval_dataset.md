# PRD-047.20 Retrieval Eval Dataset

- case_count: `18`

## Cases
- `B1-001` | `control_as_safety`
  query: Когда человек все держит под контролем, потому что иначе страшно, как это понять?
  expected_candidate_ids: `["a15d79f8-0ac0-42fc-9bc3-6985a529fb07", "47928bce-3306-4351-862e-290b3edeea59"]`
- `B1-002` | `control_as_safety_panic`
  query: Паника и страх потерять контроль: какой здесь безопасный смысл, а не просто слабость?
  expected_candidate_ids: `["47928bce-3306-4351-862e-290b3edeea59", "a15d79f8-0ac0-42fc-9bc3-6985a529fb07"]`
- `B1-003` | `shame_visibility`
  query: Почему так стыдно быть увиденным и показаться неправильным?
  expected_candidate_ids: `["d527d369-beb2-4113-b370-cb2738e76b55", "5be3f5b0-a073-4c15-8ed6-429ad22c029b"]`
- `B1-004` | `self_criticism_as_control`
  query: Самокритика будто держит меня в узде. Это про контроль?
  expected_candidate_ids: `["5808a31f-2872-4e48-826c-b318bf0d60b0", "7b61940d-f6ff-46f8-9514-797efaf0ad00", "a15d79f8-0ac0-42fc-9bc3-6985a529fb07"]`
- `B1-005` | `avoidance_as_protection`
  query: Объясни механизм избегания как защиты, а не как лени.
  expected_candidate_ids: `["3dfeca39-dbb2-4da0-b12f-15ef07fdad2b", "a15d79f8-0ac0-42fc-9bc3-6985a529fb07"]`
- `B1-006` | `fact_vs_interpretation`
  query: Я все время вижу не факты, а свои истории. Есть короткая практика?
  expected_candidate_ids: `["4ea6de6c-5dd9-4914-9fa6-75ecb70a2457"]`
- `B1-007` | `short_step_stop_frame`
  query: Нужен один бережный шаг, чтобы остановиться и заметить реакцию.
  expected_candidate_ids: `["468fb5d0-85f4-45c5-a7c3-5d593f51682e"]`
- `B1-008` | `threat_check`
  query: Как проверить, реальная ли это угроза, а не только тревога?
  expected_candidate_ids: `["88a9ca94-e506-423b-8685-e462b9beaa48"]`
- `B1-009` | `imperfect_self_program`
  query: Как разговаривать с этой внутренней программой несовершенного я?
  expected_candidate_ids: `["121bdc40-8633-469e-9837-ea9949f73de3", "5808a31f-2872-4e48-826c-b318bf0d60b0"]`
- `B1-010` | `diagnostic_translation`
  query: Объясни нормально, без диагнозов, почему программа так устойчива.
  expected_candidate_ids: `["d527d369-beb2-4113-b370-cb2738e76b55", "6db17c5b-638d-452e-8a9c-8384c9ed78a4"]`
- `B1-011` | `practice_overview`
  query: Какие здесь вообще есть несколько практических направлений, если я хочу это замечать?
  expected_candidate_ids: `["468fb5d0-85f4-45c5-a7c3-5d593f51682e", "4ea6de6c-5dd9-4914-9fa6-75ecb70a2457", "88a9ca94-e506-423b-8685-e462b9beaa48", "121bdc40-8633-469e-9837-ea9949f73de3"]`
- `B1-012` | `low_resource_answer`
  query: Нужен короткий ответ для состояния, где ресурса почти нет.
  expected_candidate_ids: `["47928bce-3306-4351-862e-290b3edeea59", "6db17c5b-638d-452e-8a9c-8384c9ed78a4"]`
- `B1-013` | `survival_drivers`
  query: Что такое пять драйверов выживания простым языком?
  expected_candidate_ids: `["6db17c5b-638d-452e-8a9c-8384c9ed78a4"]`
- `B1-014` | `parental_gaze`
  query: Это похоже на родительский взгляд внутри меня?
  expected_candidate_ids: `["5808a31f-2872-4e48-826c-b318bf0d60b0", "7b61940d-f6ff-46f8-9514-797efaf0ad00", "3dfeca39-dbb2-4da0-b12f-15ef07fdad2b"]`
- `B1-015` | `source_fragment_guard`
  query: Мне хочется прямую цитату из книги про это.
  expected_candidate_ids: `["5be3f5b0-a073-4c15-8ed6-429ad22c029b"]`
- `B1-016` | `practice_guardrails`
  query: Стоит ли сразу давать глубокую практику, если человек в перегрузе?
  expected_candidate_ids: `["468fb5d0-85f4-45c5-a7c3-5d593f51682e", "121bdc40-8633-469e-9837-ea9949f73de3"]`
- `B1-017` | `fact_vs_interpretation_conflict`
  query: Хочу различать факт и интерпретацию в конфликте.
  expected_candidate_ids: `["4ea6de6c-5dd9-4914-9fa6-75ecb70a2457"]`
- `B1-018` | `avoidance_low_resource`
  query: Если избегание защищает, с чего начать без перегруза?
  expected_candidate_ids: `["3dfeca39-dbb2-4da0-b12f-15ef07fdad2b", "468fb5d0-85f4-45c5-a7c3-5d593f51682e"]`
