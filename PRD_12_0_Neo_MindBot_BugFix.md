# PRD 12.0 — Neo MindBot: Bug Fix Sprint
## Устранение критических дефектов по итогам аудита v0.11.0

| Поле | Значение |
|---|---|
| Версия | PRD 12.0 |
| Дата | 08.04.2026 |
| Статус | ACTIVE |
| Ссылка на аудит | AUDIT_NeoMindBot_v0.11.0.md |
| Предыдущий PRD | PRD 11.0 |
| Целевая версия | v0.12.0 |

---

## 0. Контекст и цель

По итогам аудита v0.11.0 структурная миграция с SD-архитектуры завершена успешно (11/11 структурных требований PRD 11.0 пройдены). Однако выявлено **4 критических бага** и **3 важных дефекта**, которые снижают функциональность Memory Layer до ~40% и нарушают качество ответов.

**Модель gpt-5-mini оставить без изменений** — принято решение сохранить модель ради качества ответов.

### Definition of Done (DoD)

PRD 12.0 считается выполненным, если **все** следующие критерии соблюдены:
- [ ] SUMMARY LENGTH > 0 после 3+ туров диалога
- [ ] `laststatesnapshot` содержит все 7 обязательных полей PRD
- [ ] `nervous_system_state` в DIAG и METHOD SNAPSHOT имеют **одинаковое** значение
- [ ] SEMANTIC HITS > 0 на 3-м туре и далее
- [ ] StateClassifier output в логах — только `window | hyper | hypo`
- [ ] PRACTICE блок **не попадает** в промт при `route=contacthold`
- [ ] Ответ на User Correction Protocol — ≥ 3 предложений + 1 вопрос
- [ ] Все тесты секции 8 проходят

---

## 1. Реестр дефектов

| ID | Уровень | Название | Файл | Симптом |
|---|---|---|---|---|
| BUG-01 | 🔴 Critical | SummarizerAgent не генерирует summary | `conversation_memory.py` | SUMMARY LENGTH = 0 |
| BUG-02 | 🔴 Critical | Схема Memory Snapshot устарела | `memory_updater.py` | Поля `user_state`, нет `request_function` и др. |
| BUG-03 | 🔴 Critical | Конфликт `nervous_system_state` в промте | `prompt_builder.py` / промт-файлы | DIAG=hyper, METHOD=window одновременно |
| BUG-04 | 🔴 Critical | SEMANTIC HITS = 0 | `semantic_memory.py` | Эмбеддинги пишутся, но не находятся |
| IMP-01 | 🟡 Important | StateClassifier терминология не мигрирована | `state_classifier.py` | Выдаёт curious/committed/confused |
| IMP-02 | 🟡 Important | Двойной SNAPSHOT в промте | `prompts/reflective_method.txt` + `output_layer.txt` | +~200 лишних токенов |
| IMP-03 | 🟡 Important | User Correction — ответ слишком короткий | `prompts/procedural_scripts.txt` | Нарушение Pre-Send Checklist |

---

## 2. BUG-01 — SummarizerAgent: пустой summary

### 2.1 Диагностика

Из `bot-10.log` (turn 5):
```
WARNING botagent.conversationmemory SUMMARY LLM returned empty content 
keeping existing summary len=0 chars. Check reasoning_effort config.
```

Из Config Snapshot в admin: `SUMMARY LENGTH: 0`

**Корневая причина:** Конфигурация `reasoning_effort` для SummarizerAgent отсутствует или равна `none` / пустой строке. При этом gpt-5-mini может игнорировать промт с reasoning=none и возвращать пустой контент.

Вторичная возможная причина: промт Summarizer не обновлён под формат gpt-5-mini и не возвращает контент в ожидаемом формате.

### 2.2 Требования к исправлению

**F-01-A: Установить reasoning_effort для Summarizer**

В `config/system_config.yaml` (или аналоге):
```yaml
summarizer:
  model: "gpt-4o-mini"        # Summarizer не требует мощи gpt-5-mini
  reasoning_effort: "low"      # ОБЯЗАТЕЛЬНО установить
  min_turns_to_summarize: 3    # Генерировать summary с 3-го тура, не 5-го
  max_summary_tokens: 300      # Лимит для контроля размера
  fallback_on_empty: true      # Повторить запрос при пустом ответе
  fallback_retries: 2
```

**F-01-B: Добавить retry-логику при пустом ответе**

В `conversation_memory.py` (метод `update_summary` или аналог):
```python
async def _generate_summary(self, session_text: str, retries: int = 2) -> str:
    for attempt in range(retries + 1):
        result = await self.llm_client.complete(
            model=self.config.summarizer.model,
            messages=self._build_summarizer_prompt(session_text),
            reasoning_effort=self.config.summarizer.reasoning_effort,
            max_tokens=self.config.summarizer.max_summary_tokens
        )
        content = result.choices[0].message.content
        if content and len(content.strip()) > 10:
            return content.strip()
        logger.warning(f"SUMMARY empty on attempt {attempt+1}/{retries+1}")

    # Fallback: сгенерировать минимальный summary из последних сообщений
    return self._build_minimal_summary_fallback(session_text)

def _build_minimal_summary_fallback(self, session_text: str) -> str:
    """Fallback: извлечь последние 2 реплики как summary"""
    lines = [l for l in session_text.split("\n") if l.strip()]
    return " | ".join(lines[-4:])[:300] if lines else ""
```

**F-01-C: Обновить промт Summarizer**

Файл `prompts/summarizer_prompt.txt` (создать если нет):
```
Summarize the following therapy coaching session in 2-4 sentences.
Focus on: (1) main emotional theme, (2) user's core concern, 
(3) last discussed direction or practice.
Output: plain text, no headers, no lists. Russian language.
Session:
{session_text}
```

**F-01-D: Логирование результата**

```python
if summary:
    logger.info(f"SUMMARY generated len={len(summary)} chars turn={turn_index}")
else:
    logger.error(f"SUMMARY FAILED after {retries} retries turn={turn_index}")
```

### 2.3 Acceptance тест T1

```python
# tests/test_summary.py

def test_t1_1_summary_generated_after_3_turns(client):
    """SUMMARY LENGTH > 0 после 3 туров"""
    session = create_session()
    send_message(session, "привет")
    send_message(session, "я чувствую тревогу на работе")
    send_message(session, "как мне справиться с этим?")

    memory = get_memory(session.user_id)
    assert memory["summary_length"] > 0, "SUMMARY пустой после 3 туров"
    assert len(memory["current_summary"]) > 20, "Summary слишком короткий"

def test_t1_2_summary_contains_theme(client):
    """Summary отражает тему разговора"""
    session = create_session()
    send_message(session, "у меня проблемы с самооценкой")
    send_message(session, "я постоянно сомневаюсь в себе")
    send_message(session, "как перестать так думать?")

    summary = get_memory(session.user_id)["current_summary"]
    theme_words = ["самооценк", "сомнен", "думат", "тревог", "уверен"]
    assert any(w in summary.lower() for w in theme_words),         f"Summary не содержит тему разговора: {summary}"

def test_t1_3_summary_persists_across_turns(client):
    """Summary обновляется, но не обнуляется"""
    session = create_session()
    for i in range(6):
        send_message(session, f"сообщение {i}")

    memory = get_memory(session.user_id)
    assert memory["summary_length"] > 0
    assert memory["turns"] == 6

def test_t1_4_empty_summary_fallback(client, mock_llm_empty_response):
    """При пустом ответе LLM используется fallback"""
    session = create_session()
    send_message(session, "тест")
    send_message(session, "ещё тест")
    send_message(session, "ещё одно сообщение")

    memory = get_memory(session.user_id)
    # Fallback должен создать минимальный summary
    assert memory["summary_length"] > 0, "Fallback summary не создан"

def test_t1_5_summarizer_uses_correct_model(mock_llm):
    """Summarizer использует gpt-4o-mini, не gpt-5-mini"""
    session = create_session()
    for i in range(3):
        send_message(session, f"msg {i}")

    summarizer_calls = [c for c in mock_llm.calls if c["context"] == "summarizer"]
    assert all(c["model"] == "gpt-4o-mini" for c in summarizer_calls)
```

---

## 3. BUG-02 — Memory Snapshot: устаревшая схема

### 3.1 Диагностика

**Текущее состояние** (из admin Memory Snapshot):
```json
{
  "timestamp": "2026-04-08T19:32:06.718109",
  "user_input": "...",
  "bot_response": "Понял — тебе было неясно. Это нормально.",
  "user_state": "confused",
  "blocks_used": 3,
  "concepts": []
}
```

**Проблемы:**
- Используется `user_state` вместо `nervous_system_state`
- Отсутствуют 6 обязательных полей PRD
- `concepts: []` — всегда пусто (не реализовано)
- Snapshot сохраняет только последний тур, не состояние сессии

### 3.2 Целевая схема `laststatesnapshot`

```json
{
  "nervous_system_state": "window | hyper | hypo",
  "request_function": "understand | discharge | solution | validation | explore | contact",
  "dominant_part": "string",
  "active_quadrant": "i | it | we | its",
  "core_theme": "string",
  "last_practice_channel": "body | thinking | action | null",
  "active_track": null,
  "insights_log": []
}
```

### 3.3 Требования к исправлению

**F-02-A: Обновить MemoryUpdater**

В `memory/memory_updater.py`:
```python
class MemoryUpdater:
    def build_snapshot(
        self,
        state_result: StateClassifierResult,
        practice_result: Optional[PracticeResult],
        session: SessionState
    ) -> dict:
        return {
            # ОБЯЗАТЕЛЬНЫЕ поля — все 7 из PRD
            "nervous_system_state": state_result.nervous_system_state,  # НЕ user_state!
            "request_function":     state_result.request_function,
            "dominant_part":        state_result.dominant_part,
            "active_quadrant":      state_result.active_quadrant,
            "core_theme":           state_result.core_theme or "unspecified_current_issue",
            "last_practice_channel": practice_result.channel if practice_result else None,
            "active_track":         session.active_track,
            "insights_log":         session.insights_log or [],
            # Служебные поля (опционально, не передавать в промт)
            "_last_route":          state_result.resolved_route,
            "_turn_index":          session.turn_count,
            "_timestamp":           datetime.utcnow().isoformat()
        }
```

**F-02-B: Миграция данных**

```python
# migrations/migrate_snapshots.py
# Запустить ОДИН РАЗ для обновления существующих записей

def migrate_user_state_to_nervous_system_state(db_connection):
    """
    Маппинг старых user_state значений на новые
    """
    STATE_MAP = {
        "curious":     "window",
        "committed":   "window",
        "confused":    "hyper",
        "overwhelmed": "hyper",
        "detached":    "hypo",
        "flat":        "hypo",
        "frustrated":  "hyper",
        "calm":        "window",
    }

    rows = db_connection.execute(
        "SELECT user_id, last_state_snapshot FROM session_state WHERE last_state_snapshot IS NOT NULL"
    )

    for user_id, snapshot_json in rows:
        snapshot = json.loads(snapshot_json)
        if "user_state" in snapshot and "nervous_system_state" not in snapshot:
            old_state = snapshot.pop("user_state")
            snapshot["nervous_system_state"] = STATE_MAP.get(old_state, "window")
            snapshot.setdefault("request_function", "understand")
            snapshot.setdefault("dominant_part", "unknown")
            snapshot.setdefault("active_quadrant", "i")
            snapshot.setdefault("core_theme", "unspecified_current_issue")
            snapshot.setdefault("last_practice_channel", None)
            snapshot.setdefault("active_track", None)
            snapshot.setdefault("insights_log", [])

            db_connection.execute(
                "UPDATE session_state SET last_state_snapshot = ? WHERE user_id = ?",
                (json.dumps(snapshot, ensure_ascii=False), user_id)
            )

    logger.info("Migration complete: user_state → nervous_system_state")
```

**F-02-C: Обновить StateClassifierResult dataclass**

```python
@dataclass
class StateClassifierResult:
    nervous_system_state: Literal["window", "hyper", "hypo"]  # НЕ старые термины
    request_function: Literal["understand", "discharge", "solution", 
                               "validation", "explore", "contact"]
    dominant_part: str
    active_quadrant: Literal["i", "it", "we", "its"]
    core_theme: str
    confidence: float
    resolved_route: str
    interaction_mode: Literal["coaching", "informational", "crisis"]
```

### 3.4 Acceptance тесты T2

```python
# tests/test_memory_snapshot.py

REQUIRED_FIELDS = [
    "nervous_system_state", "request_function", "dominant_part",
    "active_quadrant", "core_theme", "last_practice_channel",
    "active_track", "insights_log"
]

def test_t2_1_snapshot_has_all_required_fields(client):
    """laststatesnapshot содержит все 8 обязательных полей"""
    session = create_session()
    send_message(session, "я чувствую тревогу перед важной встречей")

    snapshot = get_last_state_snapshot(session.user_id)
    for field in REQUIRED_FIELDS:
        assert field in snapshot, f"Поле '{field}' отсутствует в snapshot"

def test_t2_2_no_legacy_user_state_field(client):
    """Поле 'user_state' отсутствует в snapshot (legacy)"""
    session = create_session()
    send_message(session, "тест")

    snapshot = get_last_state_snapshot(session.user_id)
    assert "user_state" not in snapshot, "'user_state' — legacy поле, должно быть удалено"

def test_t2_3_nervous_system_state_valid_values(client):
    """nervous_system_state принимает только window | hyper | hypo"""
    valid = {"window", "hyper", "hypo"}

    for query, expected_state in [
        ("я в панике, не могу думать", "hyper"),
        ("хочу разобраться в себе", "window"),
        ("не знаю, всё как в тумане", "hypo"),
    ]:
        session = create_session()
        send_message(session, query)
        snapshot = get_last_state_snapshot(session.user_id)

        nss = snapshot["nervous_system_state"]
        assert nss in valid, f"Недопустимое значение: {nss}"
        assert nss == expected_state,             f"Ожидалось '{expected_state}', получено '{nss}' для: '{query}'"

def test_t2_4_request_function_valid_values(client):
    """request_function принимает только 6 допустимых значений"""
    valid = {"understand", "discharge", "solution", "validation", "explore", "contact"}

    session = create_session()
    send_message(session, "как мне справиться с тревогой?")

    snapshot = get_last_state_snapshot(session.user_id)
    assert snapshot["request_function"] in valid

def test_t2_5_snapshot_passed_to_llm_prompt(client, capture_llm_calls):
    """Snapshot корректно передаётся в системный промт LLM"""
    session = create_session()
    send_message(session, "я чувствую тревогу")
    send_message(session, "расскажи подробнее")

    last_call = capture_llm_calls[-1]
    system_prompt = last_call["messages"][0]["content"]

    assert "nervous_system_state" in system_prompt
    assert "request_function" in system_prompt
    assert "user_state" not in system_prompt  # legacy не должен попасть

def test_t2_6_migration_script_converts_old_records(db_fixture):
    """Скрипт миграции корректно конвертирует старые записи"""
    # Создать старую запись с user_state
    db_fixture.insert_snapshot(user_id="test_user", snapshot={
        "user_state": "confused",
        "blocks_used": 3,
        "concepts": []
    })

    run_migration(db_fixture)

    snapshot = db_fixture.get_snapshot("test_user")
    assert "nervous_system_state" in snapshot
    assert snapshot["nervous_system_state"] == "hyper"  # confused → hyper
    assert "user_state" not in snapshot
    assert "request_function" in snapshot
```

---

## 4. BUG-03 — Конфликт nervous_system_state в промте

### 4.1 Диагностика

В полотне LLM последнего сообщения зафиксировано:
- Блок `[DIAG_ALGORITHM]` → `nervous_system_state: hyper`
- Блок `[REFLECTIVE_METHOD]` → SNAPSHOT: `nervous_system_state: window`

LLM получает два разных значения одного поля в рамках одного system prompt, что создаёт противоречие и нестабильность ответов.

**Корневая причина:** PromptBuilder заполняет DIAG-контекст и METHOD-контекст из разных источников — вероятно, DIAG берёт `nervous_system_state` из текущего классификатора, а METHOD SNAPSHOT — из устаревшего `laststatesnapshot` из БД.

### 4.2 Требования к исправлению

**F-03-A: Единый источник истины для nervous_system_state**

В `bot_agent/prompt_builder.py` (или аналоге):
```python
class PromptBuilder:
    def build_system_prompt(
        self,
        state: StateClassifierResult,
        session: SessionState,
        retrieved_blocks: List[Block]
    ) -> str:

        # ЕДИНЫЙ контекст для всего промта
        current_context = {
            "interaction_mode":     state.interaction_mode,
            "nervous_system_state": state.nervous_system_state,  # ОДИН источник
            "request_function":     state.request_function,
            "dominant_part":        state.dominant_part,
            "core_theme":           state.core_theme or "unspecified_current_issue",
            "resolved_route":       state.resolved_route,
            "llm_mode":             state.llm_mode,
        }

        # Передавать ОДИН И ТОТ ЖЕ current_context во все блоки
        diag_block    = self._render_diag(current_context)
        method_block  = self._render_method(current_context, session)  # ТОТ ЖЕ контекст
        output_block  = self._render_output(current_context, session)

        return "\n\n".join([
            self._render_aa_safety(),
            self._render_seasonal(),
            self._render_core_identity(),
            diag_block,
            method_block,
            self._render_procedural_scripts(session),
            output_block
        ])
```

**F-03-B: Убрать дублирующий SNAPSHOT из [OUTPUT_LAYER]**

Файл `prompts/output_layer.txt`:
- **Удалить** блок `SNAPSHOT` и `RECENT DIALOG` из Output Layer
- **Оставить** только: Output rules, Task instruction, Anti-Bland Rule
- SNAPSHOT должен существовать **только** в блоке `[REFLECTIVE_METHOD]`

Итоговая структура `output_layer.txt`:
```
Output Layer
Output rules:
- Telegram-safe text
- No markdown code fences  
- Concrete and complete response
- End with a useful bridge question only if needed

Task instruction:
- Route: {resolved_route}
- Mode: {llm_mode}
- User request: {user_input_summary}
- Do not use code blocks or HTML tags.
- Provide a complete, useful answer; avoid vague filler.
{conditional_instructions}
```

*Примечание: `{conditional_instructions}` — динамическая вставка только нужных правил*

**F-03-C: Добавить assertion в PromptBuilder для контроля**

```python
def _validate_prompt_consistency(self, system_prompt: str):
    """Проверяет что nervous_system_state упоминается с одним значением"""
    import re

    values_found = re.findall(
        r"nervous_system_state[:\s]+(\w+)", system_prompt
    )
    unique_values = set(values_found)

    if len(unique_values) > 1:
        logger.error(
            f"PROMPT CONFLICT: nervous_system_state has multiple values: {unique_values}. "
            f"Промт содержит противоречие!"
        )
        # В dev режиме — raise; в prod — log и продолжить
        if self.config.env == "development":
            raise PromptConsistencyError(f"Conflicting states: {unique_values}")
```

### 4.3 Acceptance тесты T3

```python
# tests/test_prompt_consistency.py

def test_t3_1_single_nervous_system_state_in_prompt(client, capture_llm_calls):
    """nervous_system_state появляется в промте с одним значением"""
    session = create_session()
    send_message(session, "я чувствую панику")

    system_prompt = capture_llm_calls[-1]["messages"][0]["content"]

    import re
    values = re.findall(r"nervous_system_state[:\s]+(\w+)", system_prompt)
    unique = set(values)

    assert len(unique) == 1,         f"Конфликт! nervous_system_state имеет значения: {unique}"

def test_t3_2_no_duplicate_snapshot_in_output_layer(client, capture_llm_calls):
    """SNAPSHOT не дублируется в [OUTPUT_LAYER]"""
    session = create_session()
    send_message(session, "как справиться с тревогой?")

    system_prompt = capture_llm_calls[-1]["messages"][0]["content"]

    # Подсчитать количество вхождений SNAPSHOT
    snapshot_count = system_prompt.count("SNAPSHOT")
    assert snapshot_count <= 1,         f"SNAPSHOT дублируется {snapshot_count} раза в промте"

def test_t3_3_diag_and_method_same_state(client, capture_llm_calls):
    """DIAG и METHOD используют одинаковое nervous_system_state"""
    session = create_session()
    send_message(session, "мне очень плохо, я не могу справиться")

    system_prompt = capture_llm_calls[-1]["messages"][0]["content"]

    # Найти значения в обоих блоках
    import re
    diag_match   = re.search(r"Diagnostic Algorithm.*?nervous_system_state[:\s]+(\w+)", 
                              system_prompt, re.DOTALL)
    method_match = re.search(r"Reflective Method.*?nervous_system_state[:\s]+(\w+)", 
                              system_prompt, re.DOTALL)

    if diag_match and method_match:
        assert diag_match.group(1) == method_match.group(1),             f"DIAG={diag_match.group(1)}, METHOD={method_match.group(1)} — конфликт!"

def test_t3_4_prompt_consistency_validator_works(prompt_builder):
    """Валидатор промта обнаруживает конфликт состояний"""
    conflicting_prompt = """
    nervous_system_state: hyper
    ...
    nervous_system_state: window
    """
    with pytest.raises(PromptConsistencyError):
        prompt_builder._validate_prompt_consistency(conflicting_prompt)

def test_t3_5_token_reduction_after_dedup(client, capture_llm_calls):
    """Удаление дублирующего SNAPSHOT уменьшает размер промта"""
    session = create_session()
    send_message(session, "тестовое сообщение")

    prompt_tokens = capture_llm_calls[-1]["usage"]["prompt_tokens"]
    # Ожидаем уменьшение на ~150-250 токенов по сравнению с v0.11.0
    # Baseline v0.11.0: ~4060 tokens (из аудита)
    assert prompt_tokens < 4060,         f"Размер промта не уменьшился: {prompt_tokens} >= 4060"
```

---

## 5. BUG-04 — Semantic Memory: HITS = 0

### 5.1 Диагностика

**Симптом:** `SEMANTIC HITS: 0` при 5 турах, несмотря на то что эмбеддинги добавляются:
```
botagent.semanticmemory SEMANTIC embedding added turnindex=1
botagent.semanticmemory SEMANTIC embedding added turnindex=2
...
```

**Вероятные причины (проверить в порядке приоритета):**

1. **Порог cosine similarity завышен** — наиболее вероятно. Если threshold = 0.8, то при 5-10 турах разговора семантическая близость нового запроса к прошлым репликам редко превышает 0.8.
2. **MIN_TURNS_FOR_SEMANTIC не достигнут** — семантический поиск включается только после N туров.
3. **Top-K для semantic = 0** — `SEMANTIC_SEARCH_TOP_K` мог быть переопределён.
4. **Индекс не перестраивается** — новые эмбеддинги добавляются, но поиск идёт по старому индексу.

### 5.2 Требования к исправлению

**F-04-A: Снизить порог similarity**

В `config/system_config.yaml` или `semantic_memory.py`:
```yaml
semantic_memory:
  similarity_threshold: 0.60     # Снизить с текущего (предположительно 0.80+) до 0.60
  top_k: 3                       # Возвращать до 3 семантически близких туров
  min_turns_before_search: 2     # Включать с 2-го тура (не 5-го)
  index_update_strategy: "eager" # Обновлять индекс сразу после добавления эмбеддинга
```

**F-04-B: Диагностическое логирование**

```python
class SemanticMemory:
    def search(self, query: str, user_id: str, top_k: int = 3) -> List[SemanticHit]:
        embeddings = self._get_embeddings(user_id)

        logger.debug(
            f"SEMANTIC search: user={user_id}, "
            f"embeddings_count={len(embeddings)}, "
            f"threshold={self.threshold}"
        )

        if not embeddings:
            logger.info(f"SEMANTIC no embeddings yet for user={user_id}")
            return []

        query_emb = self.model.encode(query)
        scores = cosine_similarity([query_emb], embeddings)[0]

        # ДОБАВИТЬ: логировать топ-3 скора для диагностики
        top_scores = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:3]
        logger.info(
            f"SEMANTIC top scores: {[(i, round(s, 3)) for i, s in top_scores]}, "
            f"threshold={self.threshold}"
        )

        hits = [
            SemanticHit(turn_index=i, score=s)
            for i, s in enumerate(scores)
            if s >= self.threshold
        ]

        logger.info(f"SEMANTIC HITS: {len(hits)} for user={user_id}")
        return hits[:top_k]
```

**F-04-C: Проверить и починить index update**

```python
def add_turn_embedding(self, user_id: str, turn_index: int, text: str):
    embedding = self.model.encode(text)
    self._store_embedding(user_id, turn_index, embedding)

    # КРИТИЧНО: явно инвалидировать кэш индекса после добавления
    self._invalidate_index_cache(user_id)

    logger.info(
        f"SEMANTIC embedding added turnindex={turn_index} "
        f"total_embeddings={self._count_embeddings(user_id)}"
    )
```

### 5.3 Acceptance тесты T4

```python
# tests/test_semantic_memory.py

def test_t4_1_semantic_hits_after_3_turns(client):
    """SEMANTIC HITS > 0 начиная с 3-го тура"""
    session = create_session()
    send_message(session, "я чувствую тревогу на работе")
    send_message(session, "это связано с моим начальником")
    metrics = get_session_metrics(session)
    assert metrics["semantic_hits"] == 0  # На 2-м туре — норма

    send_message(session, "как справиться с тревогой на работе?")
    metrics = get_session_metrics(session)
    assert metrics["semantic_hits"] > 0, "SEMANTIC HITS = 0 на 3-м туре"

def test_t4_2_semantic_threshold_respected(semantic_memory):
    """Поиск возвращает хиты при threshold=0.60"""
    user_id = "test_user"
    semantic_memory.add_turn_embedding(user_id, 1, "тревога на работе")
    semantic_memory.add_turn_embedding(user_id, 2, "страх оценки коллег")

    hits = semantic_memory.search("как справиться с тревогой?", user_id)
    assert len(hits) > 0, f"Нет хитов при threshold={semantic_memory.threshold}"

def test_t4_3_index_updated_after_add(semantic_memory):
    """Индекс обновляется сразу после добавления эмбеддинга"""
    user_id = "test_user"

    # До добавления — нет хитов
    hits_before = semantic_memory.search("тревога", user_id)
    assert len(hits_before) == 0

    semantic_memory.add_turn_embedding(user_id, 1, "я чувствую тревогу")

    # После добавления — есть хит
    hits_after = semantic_memory.search("тревога", user_id)
    assert len(hits_after) > 0, "Индекс не обновился после add"

def test_t4_4_semantic_hits_logged(client, caplog):
    """SEMANTIC HITS: N логируется корректно"""
    session = create_session()
    for i in range(4):
        send_message(session, f"сообщение про тревогу {i}")

    assert "SEMANTIC HITS:" in caplog.text
    assert "SEMANTIC HITS: 0" not in caplog.text  # Не должно быть нулевых хитов

def test_t4_5_top_scores_logged_for_diagnostics(client, caplog):
    """Top scores логируются для диагностики"""
    session = create_session()
    for i in range(3):
        send_message(session, "тревога самооценка")

    assert "SEMANTIC top scores:" in caplog.text
```

---

## 6. IMP-01 — StateClassifier: мигрировать терминологию

### 6.1 Диагностика

Из логов аудита:
```
botagent.stateclassifier  curious  0.70
botagent.stateclassifier  committed  0.86
botagent.stateclassifier  curious  0.60
botagent.stateclassifier  confused  0.40
```
Admin State Trajectory: `curious → committed → curious → curious → confused`

StateClassifier возвращает старую терминологию. Это создаёт риск что маппинг где-то применяется неполно или неконсистентно.

### 6.2 Требования

**F-05-A: Обновить StateClassifier**

Два варианта (выбрать по архитектуре):

**Вариант A — LLM-based classifier (если StateClassifier использует gpt-4o-mini):**

Обновить промт классификатора:
```
Classify the user's nervous system state. 
Return ONLY one of: window | hyper | hypo

Definitions:
- window: Calm, curious, reflective, committed, engaged, ready to explore
- hyper: Anxious, confused, overwhelmed, frustrated, tense, scattered
- hypo: Flat, detached, numb, exhausted, withdrawn, disengaged

User message: {user_message}
Context: {recent_context}

Respond with ONLY the state label (window/hyper/hypo) and confidence 0.0-1.0
Format: STATE CONFIDENCE
Example: window 0.85
```

**Вариант B — Rule-based / hybrid classifier:**

```python
# Добавить явный маппинг как safety net
LEGACY_STATE_MAP = {
    "curious":     "window",
    "committed":   "window", 
    "calm":        "window",
    "engaged":     "window",
    "confused":    "hyper",
    "overwhelmed": "hyper",
    "frustrated":  "hyper",
    "anxious":     "hyper",
    "detached":    "hypo",
    "flat":        "hypo",
    "numb":        "hypo",
    "exhausted":   "hypo",
}

def classify(self, raw_output: str) -> StateClassifierResult:
    state_raw = raw_output.strip().lower().split()[0]

    # Если получен legacy термин — конвертировать и залогировать
    if state_raw not in ("window", "hyper", "hypo"):
        mapped = LEGACY_STATE_MAP.get(state_raw)
        if mapped:
            logger.warning(
                f"STATE LEGACY TERM '{state_raw}' → '{mapped}' "
                f"(обновите промт классификатора)"
            )
            state_raw = mapped
        else:
            logger.error(f"STATE UNKNOWN TERM '{state_raw}' → fallback 'window'")
            state_raw = "window"

    return StateClassifierResult(nervous_system_state=state_raw, ...)
```

### 6.3 Acceptance тесты T5

```python
# tests/test_state_classifier.py

VALID_STATES = {"window", "hyper", "hypo"}

@pytest.mark.parametrize("query,expected", [
    ("я в полной панике, не могу думать", "hyper"),
    ("мне тревожно и я не понимаю что происходит", "hyper"),
    ("хочу разобраться, как это работает", "window"),
    ("мне интересно изучить эту тему", "window"),
    ("не знаю... всё как в тумане, нет сил", "hypo"),
    ("я просто устал от всего, ничего не хочу", "hypo"),
])
def test_t5_1_state_classifier_valid_output(client, query, expected):
    """StateClassifier возвращает только window|hyper|hypo"""
    session = create_session()
    send_message(session, query)

    state = get_last_classifier_output(session)
    assert state in VALID_STATES, f"Недопустимое состояние: {state}"
    assert state == expected, f"Для '{query}': ожидалось '{expected}', получено '{state}'"

def test_t5_2_no_legacy_terms_in_logs(client, caplog):
    """Логи не содержат legacy-терминов"""
    LEGACY_TERMS = ["curious", "committed", "confused", "overwhelmed", "frustrated"]

    session = create_session()
    for query in ["привет", "я тревожусь", "хочу разобраться"]:
        send_message(session, query)

    for term in LEGACY_TERMS:
        assert f"stateclassifier  {term}" not in caplog.text,             f"Legacy термин '{term}' найден в логах"

def test_t5_3_state_trajectory_uses_new_terms(client):
    """State Trajectory в admin показывает только window|hyper|hypo"""
    session = create_session()
    messages = [
        "привет",
        "я сильно тревожусь",
        "хочу понять причины",
        "мне сложно объяснить словами"
    ]
    for msg in messages:
        send_message(session, msg)

    trajectory = get_state_trajectory(session)
    for state in trajectory:
        assert state in VALID_STATES, f"Legacy состояние в trajectory: {state}"
```

---

## 7. IMP-02 + IMP-03 — Промт и User Correction

### 7.1 IMP-02: Удалить PRACTICE блок при skip

**F-06-A:** В `prompt_builder.py`:
```python
def _render_practice_suggestion(
    self, 
    practice: Optional[PracticeResult],
    route: str
) -> str:
    """Добавлять PRACTICE блок ТОЛЬКО если практика не скипнута"""

    SKIP_ROUTES = {"contacthold", "presence", "crisis_hold"}

    if route in SKIP_ROUTES or practice is None:
        # НЕ добавлять блок в промт — экономия ~80-120 токенов
        return ""

    return self._format_practice_block(practice)
```

### 7.2 IMP-03: User Correction Protocol — минимум 3 предложения + вопрос

**F-07-A:** В `prompts/procedural_scripts.txt`, секция `User Correction Protocol`:
```
User Correction Protocol:
IF user signals confusion, misunderstanding, or asks to simplify:

MANDATORY response structure:
1. Acknowledge in 1 sentence (do NOT just say "Понял — тебе было неясно. Это нормально.")
2. Rephrase the core idea in simpler language (1-2 sentences)
3. Give ONE concrete example or analogy  
4. End with a clarifying question to check understanding

MINIMUM length: 3 sentences + 1 question
FORBIDDEN: Responses under 2 sentences when user_correction=true
Example trigger phrases: "не понятно", "объясни", "непонятно", "слишком сложно", 
                          "что это значит", "можешь проще"
```

### 7.3 Acceptance тесты T6

```python
# tests/test_prompt_and_ux.py

def test_t6_1_practice_block_absent_on_contacthold(client, capture_llm_calls):
    """PRACTICE блок отсутствует в промте при route=contacthold"""
    session = create_session()
    send_message(session, "привет")  # Первое сообщение → contacthold

    system_prompt = capture_llm_calls[-1]["messages"][0]["content"]
    assert "PRACTICE SUGGESTION" not in system_prompt,         "PRACTICE SUGGESTION попал в промт при route=contacthold"

def test_t6_2_user_correction_response_length(client):
    """Ответ на confusion содержит ≥3 предложения"""
    session = create_session()
    send_message(session, "расскажи о когнитивных искажениях")
    response = send_message(session, "ты отвечаешь непонятно, объясни проще")

    sentences = [s.strip() for s in response.split(".") if len(s.strip()) > 5]
    assert len(sentences) >= 3,         f"User Correction response слишком короткий: {len(sentences)} предложений"

def test_t6_3_user_correction_ends_with_question(client):
    """Ответ на correction заканчивается вопросом"""
    session = create_session()
    send_message(session, "объясни мне про тревогу")
    response = send_message(session, "не понятно что ты имеешь в виду")

    assert "?" in response, "Ответ на correction не содержит вопроса"

def test_t6_4_token_savings_practice_skip(client, capture_llm_calls):
    """Токены уменьшились при skip практики"""
    session = create_session()
    send_message(session, "привет")  # contacthold — practice skip

    tokens_turn1 = capture_llm_calls[-1]["usage"]["prompt_tokens"]

    send_message(session, "я тревожусь")  # обычный тур — practice может быть
    tokens_turn2 = capture_llm_calls[-1]["usage"]["prompt_tokens"]

    # Turn 1 (contacthold) должен быть легче
    assert tokens_turn1 < tokens_turn2,         "Токены contacthold не меньше обычного тура"
```

---

## 8. Финальный Regression Suite (T7)

```python
# tests/test_regression_v12.py

def test_r1_full_pipeline_no_sd_across_all_turns(client):
    """SD отключён на всех турах — регрессия"""
    session = create_session()
    queries = [
        "привет",
        "я чувствую тревогу",
        "как справиться?",
        "не понятно, объясни",
        "окей, понял"
    ]
    for q in queries:
        send_message(session, q)

    logs = get_session_logs(session)
    for log_line in logs:
        assert "SD runtime disabled" in log_line or "SD" not in log_line,             f"SD активирован в логе: {log_line}"

def test_r2_memory_snapshot_v12_schema_all_turns(client):
    """Схема snaphot v12 соблюдается на всех турах"""
    session = create_session()
    for i in range(5):
        send_message(session, f"сообщение {i} о тревоге и работе")
        snapshot = get_last_state_snapshot(session.user_id)

        assert "nervous_system_state" in snapshot, f"Поле отсутствует на туре {i}"
        assert "user_state" not in snapshot, f"Legacy поле на туре {i}"

def test_r3_summary_exists_after_session(client):
    """Summary генерируется по итогам сессии"""
    session = create_session()
    for msg in ["привет", "тревожусь", "как помочь себе?"]:
        send_message(session, msg)

    memory = get_memory(session.user_id)
    assert memory["summary_length"] > 0

def test_r4_semantic_hits_nonzero_mid_session(client):
    """Semantic hits > 0 в середине сессии"""
    session = create_session()
    for msg in ["я боюсь ошибок", "это влияет на работу", "как с этим работать?"]:
        send_message(session, msg)

    metrics = get_session_metrics(session)
    assert metrics["semantic_hits"] > 0

def test_r5_no_conflict_in_system_prompt(client, capture_llm_calls):
    """Нет конфликта состояний в системном промте"""
    session = create_session()
    send_message(session, "мне очень тревожно прямо сейчас")

    import re
    system_prompt = capture_llm_calls[-1]["messages"][0]["content"]
    states = set(re.findall(r"nervous_system_state[:\s]+(\w+)", system_prompt))
    assert len(states) <= 1, f"Конфликт состояний: {states}"

def test_r6_state_classifier_new_terms_only(client):
    """Classifier выдаёт только window|hyper|hypo"""
    VALID = {"window", "hyper", "hypo"}
    session = create_session()

    for msg in ["привет", "тревожусь", "устал от всего"]:
        send_message(session, msg)
        state = get_last_classifier_output(session)
        assert state in VALID, f"Недопустимый термин: {state}"

def test_r7_user_correction_quality(client):
    """User Correction: ≥3 предложений и вопрос"""
    session = create_session()
    send_message(session, "расскажи про ACT")
    response = send_message(session, "слишком непонятно, объясни проще")

    assert len([s for s in response.split(".") if len(s.strip()) > 5]) >= 3
    assert "?" in response

def test_r8_no_legacy_schema_in_db(db_fixture):
    """В БД нет записей со старой схемой snapshot"""
    old_records = db_fixture.query(
        "SELECT COUNT(*) FROM session_state WHERE last_state_snapshot LIKE \'%"user_state"%\'"
    )
    assert old_records == 0, f"Найдено {old_records} записей с legacy схемой"

def test_r9_practice_skip_no_practice_in_prompt(client, capture_llm_calls):
    """При route=contacthold PRACTICE не в промте"""
    session = create_session()
    send_message(session, "привет")

    system_prompt = capture_llm_calls[-1]["messages"][0]["content"]
    assert "PRACTICE SUGGESTION" not in system_prompt

def test_r10_prompt_tokens_reduced_vs_v11(client, capture_llm_calls):
    """Токены промта ≤ baseline v0.11.0 (4060)"""
    session = create_session()
    send_message(session, "тестовый запрос про тревогу")

    tokens = capture_llm_calls[-1]["usage"]["prompt_tokens"]
    assert tokens <= 4060, f"Промт не уменьшился: {tokens} > 4060"
```

---

## 9. Технический план выполнения

### Волна 1 — Критические (BUG-01, BUG-02, BUG-03) ~2-3 часа

```
1.1 [BUG-01] Установить reasoning_effort: "low" для Summarizer
1.2 [BUG-01] Добавить retry-логику + fallback в _generate_summary()
1.3 [BUG-01] Создать/обновить prompts/summarizer_prompt.txt
1.4 [BUG-02] Обновить build_snapshot() в memory_updater.py
1.5 [BUG-02] Запустить migrate_snapshots.py
1.6 [BUG-03] Рефакторинг PromptBuilder: единый current_context
1.7 [BUG-03] Убрать дублирующий SNAPSHOT из output_layer.txt
1.8 [BUG-03] Добавить _validate_prompt_consistency()
```

### Волна 2 — BUG-04 и IMP-01 ~1-2 часа

```
2.1 [BUG-04] Снизить similarity_threshold до 0.60
2.2 [BUG-04] Добавить диагностическое логирование в SemanticMemory
2.3 [BUG-04] Починить _invalidate_index_cache() после add
2.4 [IMP-01] Обновить промт StateClassifier (Вариант A) ИЛИ добавить маппинг (Вариант B)
```

### Волна 3 — IMP-02, IMP-03 и тесты ~1 час

```
3.1 [IMP-02] Добавить условный рендер PRACTICE блока
3.2 [IMP-03] Обновить User Correction Protocol в procedural_scripts.txt
3.3 Запустить все тесты T1-T7
3.4 Зафиксировать version: 0.12.0 в api/main.py
```

---

## 10. Definition of Done — финальный чеклист

```
КРИТИЧЕСКИЕ БАГИ:
[ ] BUG-01: SUMMARY LENGTH > 0 после 3+ туров
[ ] BUG-01: Тесты T1.1 - T1.5 PASS
[ ] BUG-02: laststatesnapshot содержит все 8 полей
[ ] BUG-02: Поле "user_state" отсутствует
[ ] BUG-02: Тесты T2.1 - T2.6 PASS
[ ] BUG-03: Один nervous_system_state в промте
[ ] BUG-03: Нет дублирующего SNAPSHOT
[ ] BUG-03: Тесты T3.1 - T3.5 PASS
[ ] BUG-04: SEMANTIC HITS > 0 на 3-м туре
[ ] BUG-04: Тесты T4.1 - T4.5 PASS

ВАЖНЫЕ УЛУЧШЕНИЯ:
[ ] IMP-01: Classifier выдаёт только window|hyper|hypo
[ ] IMP-01: Тесты T5.1 - T5.3 PASS
[ ] IMP-02: PRACTICE отсутствует при route=contacthold
[ ] IMP-03: User Correction ≥3 предложений + вопрос
[ ] Тесты T6.1 - T6.4 PASS

REGRESSION:
[ ] Все тесты T7 (R1-R10) PASS
[ ] Версия обновлена: 0.12.0
[ ] SD disabled на всех турах (проверить логами)

ЗАПРЕЩЕНО МЕНЯТЬ:
[ ] Модель основного LLM остаётся gpt-5-mini
[ ] Prompt Stack порядок AA→A→CORE→DIAG→METHOD→PROC→OUTPUT
[ ] VoyageReranker (rerank-2) 
[ ] Botdatabase API как источник данных
```

---

*PRD 12.0 — Neo MindBot Bug Fix Sprint | v0.12.0 target*
