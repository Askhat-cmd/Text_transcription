# NEO Safety System (Система безопасности NEO)

## Principle (Принцип)

Безопасность проверяется до генерации финального ответа и не зависит только от LLM.
Основной подход — детерминированные правила + fallback-проверки.

Источник: `bot_agent/multiagent/agents/state_analyzer.py`.

## Safety-сигналы

### Deterministic Layer (Детерминированный слой)

В State Analyzer используется список `_SAFETY_KEYWORDS`.
Если сообщение содержит триггерные формулировки, выставляется:
- `safety_flag=True`
- повышенный приоритет защитного режима.

### LLM safety check

Дополнительно может применяться `_llm_safety_check` для неоднозначных случаев.
Это слой уточнения, а не единственный источник решения.

## mojibake protection (Нормализация кодировок)

Перед анализом входной текст нормализуется.
Цель — не потерять safety-триггеры из-за испорченной кодировки и кривых символов.

## What Happens When safety_flag=True (Что происходит при safety_flag=True)

Пайплайн переходит в защитный контур:
- Writer работает в безопасном режиме;
- финальный `response_mode` может стать `safe_override`;
- Validator блокирует потенциально рискованные формулировки;
- пользователю возвращается безопасная версия ответа.

## Validator Agent Role (Роль Validator Agent)

Validator проверяет:
- фатальные нарушения (`is_blocked=true`);
- причину и категорию блокировки;
- безопасную замену (`safe_replacement`);
- нефатальные флаги качества (`quality_flags`).

Контракт: `bot_agent/multiagent/contracts/validation_result.py`.

## What Is NOT a Default safety-trigger (Что НЕ считается safety-trigger по умолчанию)

- нейтральные обсуждения эмоций без признаков риска;
- абстрактные философские вопросы;
- обычные бытовые запросы.

Важно: итоговое решение всегда опирается на совокупность сигналов (ключевые слова, контекст, валидатор).

## Trace Observability (Наблюдаемость в trace)

В debug/trace доступны:
- `safety_flag`
- `response_mode`
- `validator_blocked`
- `validator_block_reason`
- `validator_quality_flags`

Это позволяет быстро видеть, почему система выбрала защитный режим.

## Tests (Тесты)

```bash
pytest tests/multiagent/test_safety_detection.py -q
pytest tests/multiagent/test_orchestrator_e2e.py -q
pytest tests/multiagent -q
```

Ожидаемый базовый маркер: сценарии SD-01..SD-10 проходят стабильно.
