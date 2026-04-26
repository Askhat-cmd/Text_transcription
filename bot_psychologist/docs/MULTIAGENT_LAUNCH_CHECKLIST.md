# Чеклист первого живого запуска мультиагентной системы

## 1. Подготовка `.env`

- [ ] `OPENAI_API_KEY` задан и действителен.
- [ ] `MULTIAGENT_ENABLED=true`.
- [ ] `STATE_ANALYZER_MODEL=gpt-4o-mini`.
- [ ] `WRITER_MODEL=gpt-4o-mini`.
- [ ] `MULTIAGENT_LLM_TIMEOUT=30`.
- [ ] `MULTIAGENT_MAX_TOKENS=600`.
- [ ] `MULTIAGENT_TEMPERATURE=0.7`.

## 2. Проверка конфигурации

- [ ] `pytest tests/multiagent/test_multiagent_smoke.py -v` -> 10 passed.
- [ ] `pytest tests/multiagent/ -q` -> весь пакет зеленый.

## 3. Первый тестовый запрос

Запуск из Python REPL или тестового скрипта:

```python
import asyncio
from bot_agent.multiagent.orchestrator import orchestrator

result = asyncio.run(
    orchestrator.run(
        query="Я чувствую тревогу перед важным событием",
        user_id="smoke_test_001",
    )
)

print("Status:", result["status"])
print("Phase:", result["phase"])
print("Mode:", result["response_mode"])
print("Answer preview:", result["answer"][:200])
print("Debug:", result["debug"])
```

Ожидаемо:
- `status == "ok"`
- `answer` непустой
- `debug.validator_blocked == False`
- без исключений в логах

## 4. Проверка после первого запуска

- [ ] В `logs/` нет критических ошибок.
- [ ] `phase` входит в набор: `clarify`, `explore`, `stabilize`, `integrate`.
- [ ] Результат первого запуска отражен в `CHANGELOG.md`.

## 5. Откат

Если новый режим ведет себя нестабильно:

- [ ] В `.env` выставить `MULTIAGENT_ENABLED=false`.
- [ ] Перезапустить API.
- [ ] Убедиться, что бот вернулся на классический путь.

