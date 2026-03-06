
# PRD v2.0.2 — Устранение обрыва ответов бота (токены + форматтер)

**Проект:** bot_psychologist / bot_agent  
**Версия:** 2.0.2  
**Дата:** 2026-03-03  
**Статус:** Ready for implementation  
**Приоритет:** High  

---

## 1. КОНТЕКСТ И ЦЕЛЬ

### 1.1 Проблема
Ответы бота обрываются посреди предложения без завершения мысли.
Пример из UI: "Примеры: обостряешь кр" — текст обрывается на полуслове.

### 1.2 Причина
Двухуровневое ограничение длины ответа:

**Уровень 1 — LLM API (главная причина обрыва):**
Файл: `bot_agent/config.py`
```python
LLM_MAX_TOKENS = 1500  # ← слишком мало
```

При достижении лимита OpenAI API обрывает генерацию мгновенно,
без предупреждения и без "...". 1500 токенов = ~900–1100 символов
русского текста. Это меньше, чем char_limit форматтера для большинства
режимов (2000–4000 символов).

**Уровень 2 — ResponseFormatter (вторичный, добавляет "..."):**
Файл: `bot_agent/response/response_formatter.py`
Обрезает уже готовый текст по числу символов и добавляет "...".
До этого уровня при текущем LLM_MAX_TOKENS часто не доходит.

### 1.3 Цель

Согласовать лимиты токенов LLM с лимитами символов форматтера
по каждому режиму, чтобы ответы всегда получали достаточно токенов
для полного завершения и "обрезка с ..." происходила только в
форматтере, а не на уровне API.

---

## 2. SCOPE ИЗМЕНЕНИЙ

### 2.1 Файлы для изменения

| Файл | Тип изменения |
| :-- | :-- |
| `bot_agent/config.py` | Увеличить `LLM_MAX_TOKENS`, добавить `MODE_MAX_TOKENS` |
| `bot_agent/response/response_formatter.py` | Не менять (только сверить) |

### 2.2 Файлы НЕ трогать

- Все файлы `web_ui/` — не трогать
- `bot_agent/state_classifier.py` — не трогать
- `bot_agent/sd_classifier.py` — не трогать
- `api/` — не трогать
- `bot_agent/response/response_formatter.py` — только проверить,
не изменять

---

## 3. ДЕТАЛЬНЫЕ ТРЕБОВАНИЯ

### 3.1 Формула согласования токенов

Русский текст: 1 токен ≈ 0.6 символа (1 символ ≈ 1.65 токена).
Коэффициент пересчёта char_limit → tokens: `char_limit × 1.7`
Добавить запас +20% на safety margin.

Итоговая формула:

```
mode_tokens = round(char_limit × 1.7 × 1.2)
```


### 3.2 Согласованная таблица лимитов

| Режим | char_limit (форматтер) | Минимум токенов | Рекомендуемый лимит |
| :-- | :-- | :-- | :-- |
| PRESENCE | 2000 | 3400 | **3500** |
| CLARIFICATION | 2000 | 3400 | **3500** |
| VALIDATION | 2400 | 4080 | **4200** |
| THINKING | 4000 | 6800 | **7000** |
| INTERVENTION | 3200 | 5440 | **5500** |
| INTEGRATION | 2400 | 4080 | **4200** |
| default (fallback) | 900 | 1530 | **2000** |

### 3.3 Изменения в `config.py`

**3.3.1 Обновить глобальный лимит (fallback для неизвестных режимов):**

```python
# БЫЛО:
LLM_MAX_TOKENS = 1500

# СТАЛО:
LLM_MAX_TOKENS = 2000
```

**3.3.2 Добавить словарь лимитов по режимам:**
Добавить сразу после строки `LLM_MAX_TOKENS`:

```python
# Token limits per response mode (aligned with ResponseFormatter char_limits)
# Formula: char_limit × 1.7 (ru tokens/char) × 1.2 (safety margin)
MODE_MAX_TOKENS: dict = {
    "PRESENCE":      3500,
    "CLARIFICATION": 3500,
    "VALIDATION":    4200,
    "THINKING":      7000,
    "INTERVENTION":  5500,
    "INTEGRATION":   4200,
}
```

**3.3.3 Добавить метод `get_mode_max_tokens`:**
Добавить новый classmethod в класс `Config`, рядом с
`get_effective_max_tokens`:

```python
@classmethod
def get_mode_max_tokens(cls, mode: str | None = None) -> int:
    """Return token limit for given response mode.
    
    Falls back to LLM_MAX_TOKENS if mode is unknown.
    For reasoning models, always returns get_effective_max_tokens().
    """
    if not cls.supports_custom_temperature():
        return cls.get_effective_max_tokens()
    normalized = (mode or "").upper()
    return cls.MODE_MAX_TOKENS.get(normalized, cls.LLM_MAX_TOKENS)
```


### 3.4 Использование нового метода

Найти в кодовой базе все места, где идёт вызов LLM с параметром
`max_tokens` (или `max_completion_tokens`), и заменить значение
`config.LLM_MAX_TOKENS` на `config.get_mode_max_tokens(mode)`,
где `mode` — текущий режим ответа (PRESENCE, VALIDATION и т.д.).

Ключевые места поиска:

- `bot_agent/response/` — генераторы ответов
- `bot_agent/orchestrator.py` (если существует)
- Любой файл с `openai.chat.completions.create(...)`

Паттерн поиска:

```python
# Искать:
config.LLM_MAX_TOKENS
# или:
Config.LLM_MAX_TOKENS
# или:
"max_tokens": ...LLM_MAX_TOKENS...

# Заменить на:
config.get_mode_max_tokens(mode)
```

Если переменная `mode` в точке вызова недоступна — передать её
через параметр функции из вышестоящего контекста.

---

## 4. ЧТО НЕ ТРОГАТЬ (важно)

1. `get_effective_max_tokens()` — этот метод для reasoning-моделей
(gpt-5, o1, o3, o4), не изменять его логику. Новый метод
`get_mode_max_tokens()` уже учитывает это через
`supports_custom_temperature()`.
2. `ResponseFormatter.mode_char_limits` — не менять значения
в форматтере. Они правильные, проблема была только в токенах.
3. `LLM_MAX_TOKENS = 2000` остаётся как fallback — если режим
неизвестен или None, используется он.
4. Логику `_clip()` в форматтере не трогать.

---

## 5. ОЖИДАЕМОЕ ПОВЕДЕНИЕ ПОСЛЕ ИЗМЕНЕНИЙ

**До:**

```
LLM генерирует → обрыв на 1500 токенах → текст режется на полуслове
ResponseFormatter → текст уже оборван, "..." не добавляется корректно
```

**После:**

```
LLM генерирует → получает достаточно токенов по режиму (3500–7000)
                → завершает мысль полностью
ResponseFormatter → при необходимости обрезает по char_limit + "..."
                  → текст всегда заканчивается на логичной границе
```


---

## 6. ТЕСТИРОВАНИЕ

### 6.1 Запуск линтинга

```bash
cd bot_psychologist
python -m py_compile bot_agent/config.py
python -c "from bot_agent.config import config; print(config.info())"
```

Ожидаемый результат: конфиг выводится без ошибок.

### 6.2 Проверка нового метода

```python
from bot_agent.config import config

# Тест 1: режим PRESENCE
assert config.get_mode_max_tokens("PRESENCE") == 3500

# Тест 2: режим THINKING (самый длинный)
assert config.get_mode_max_tokens("THINKING") == 7000

# Тест 3: неизвестный режим → fallback
assert config.get_mode_max_tokens("UNKNOWN") == 2000

# Тест 4: None → fallback
assert config.get_mode_max_tokens(None) == 2000

# Тест 5: регистр не важен
assert config.get_mode_max_tokens("presence") == 3500

print("Все тесты прошли ✓")
```


### 6.3 Функциональный тест в браузере

**Тест 1 — Режим PRESENCE (самый частый):**

- [ ] Отправить сообщение, которое провоцирует развёрнутый ответ
(например: "расскажи подробно про старую боль")
- [ ] Ответ завершается полным предложением
- [ ] Ответ НЕ обрывается на полуслове
- [ ] Если ответ длинный — заканчивается на "..." (форматтер)
а не на обрыве

**Тест 2 — Режим THINKING:**

- [ ] Отправить философский/глубокий вопрос
- [ ] Ответ полный, не обрывается

**Тест 3 — Регрессия (короткие ответы):**

- [ ] Короткие ответы бота не изменились
- [ ] Режим CLARIFICATION заканчивается вопросом (логика форматтера)


### 6.4 Проверка времени ответа

- [ ] Время ответа не выросло значительно (модель должна
завершить ответ раньше лимита, лимит — страховка)
- [ ] Если время ответа выросло > 20% — проверить, не генерирует
ли модель лишний текст вместо естественного завершения

---

## 7. DEFINITION OF DONE

- [ ] `config.py`: `LLM_MAX_TOKENS = 2000`
- [ ] `config.py`: словарь `MODE_MAX_TOKENS` добавлен
- [ ] `config.py`: метод `get_mode_max_tokens()` добавлен
- [ ] Все вызовы LLM используют `config.get_mode_max_tokens(mode)`
вместо `config.LLM_MAX_TOKENS`
- [ ] `python -c "from bot_agent.config import config; print(config.info())"` — OK
- [ ] Тесты из раздела 6.2 пройдены
- [ ] Ответы в браузере не обрываются на полуслове
- [ ] Короткие ответы не изменились (регрессия OK)

```
```

