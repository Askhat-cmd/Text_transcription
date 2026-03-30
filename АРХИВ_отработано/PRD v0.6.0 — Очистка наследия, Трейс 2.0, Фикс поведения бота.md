# PRD v0.6.0 — Очистка наследия, Трейс 2.0, Фикс поведения бота

**Версия:** 0.6.0  
**Дата:** 25.03.2026  
**Репозиторий:** `Askhat-cmd/Text_transcription`  
**Директория:** `bot_psychologist/`  
**Исполнитель:** Cursor IDE Agent  
**Предыдущий PRD:** v0.5.0 — упрощение retrieval pipeline  
**Статус предыдущего PRD:** ✅ Выполнен  

---

## ⚠️ ИНСТРУКЦИЯ АГЕНТУ — ЧИТАТЬ ПЕРВЫМ

Перед началом работы агент **обязан**:

1. **Создать файл** `PRD_TASKS_v0.6.0.md` в корне проекта с полным чеклистом
   всех тасков из этого PRD (чекбоксы `[ ]`). При завершении каждого шага
   ставить `[x]`.
2. **Создать ветку:**
   ```bash
   git checkout -b fix/v0.6.0-cleanup-trace-behavior
```

3. **Сделать checkpoint-коммит:**

```bash
git add -A && git commit -m "checkpoint: before v0.6.0 — state before cleanup"
```

4. **После каждого блока** — делать коммит с тегом блока (шаблоны в конце PRD).
5. **Если сессия прерывается** — в следующем чате первым делом читать
`PRD_TASKS_v0.6.0.md` и продолжать с первого незакрытого таска.
6. **Не переходить к следующему блоку** без коммита предыдущего.
7. **Не угадывать** — если что-то неясно, читать код, не предполагать.

---

## Контекст для агента

Бот-психолог реализует концепции Спиральной Динамики. В PRD v0.5.0 был
выполнен рефакторинг retrieval pipeline: удалены `stage_filter.py` и
`sd_filter.py`, SD-уровень теперь передаётся в LLM-промпт, а не
используется для фильтрации блоков. Это работает.

**Текущие проблемы, которые решает этот PRD:**

- Конфиги из веб-админки не применяются к runtime бота (три разных
источника дают три разных значения `top_k`)
- Бот начинает каждый ответ с перефразирования вопроса пользователя
("Я слышу, что ты хочешь...") — это захардкожено в промпте
- В коде остались мёртвые модули: `prompt_system_level_*.md`,
`KnowledgeGraphClient`, дублирующееся логирование блоков
- Трейс не показывает что именно ушло в OpenAI API — невозможно
отлаживать качество ответов
- Embedding-модель грузится при первом запросе пользователя (+7 сек)

**Этот PRD разделён на 5 независимых блоков.** Выполняй строго
последовательно. Каждый блок — отдельный коммит.

---

## БЛОК 0 — Подготовка и аудит стека

Этот блок обязателен. Без него агент будет угадывать архитектуру.

### Таски

```
[ ] 0.1  Создать PRD_TASKS_v0.6.0.md с полным чеклистом всех тасков
[ ] 0.2  Создать ветку: git checkout -b fix/v0.6.0-cleanup-trace-behavior
[ ] 0.3  Checkpoint-коммит: git commit -m "checkpoint: before v0.6.0"
[ ] 0.4  Определить фронтенд-стек:
         ls web_ui/ и открыть package.json (если есть)
         Определить: React / Vue / Vanilla JS / Jinja2 / другое
         Записать результат в PRD_TASKS_v0.6.0.md как:
         FRONTEND_STACK: <результат>
[ ] 0.5  Определить модель хранения конфига:
         grep -rn "top_k\|RETRIEVAL_TOP_K\|rerank_top_k" \
           --include="*.py" bot_psychologist/
         Найти где читается конфиг в answer_adaptive.py:
         из config.py напрямую / из runtime-объекта / из .env
         Записать: CONFIG_SOURCE: <результат>
[ ] 0.6  Определить хранение трейса:
         grep -rn "trace\|session_id\|TraceData" \
           --include="*.py" bot_psychologist/api/
         Определить: хранится в памяти (dict) / Redis / БД
         Записать: TRACE_STORAGE: <результат>
[ ] 0.7  Определить применяются ли уровни сложности:
         grep -rn "level_beginner\|level_intermediate\|level_advanced\
           \|user_level\|complexity_level\|skill_level" \
           --include="*.py" bot_psychologist/
         Записать: LEVELS_USED: yes/no
[ ] 0.8  Запустить baseline тесты и сохранить:
         cd bot_psychologist && \
         python -m pytest tests/ -v --tb=short > tests_v060_before.txt 2>&1
[ ] 0.9  Зафиксировать все находки в PRD_TASKS_v0.6.0.md
```

**Критерий готовности:** заполнены все 4 переменные окружения
(FRONTEND_STACK, CONFIG_SOURCE, TRACE_STORAGE, LEVELS_USED), есть baseline
тестов, ветка создана.

---

## БЛОК 1 — Диагностика и починка Web Admin (hot-reload конфига)

### Проблема

После PRD v0.5.0 возникло три несовпадающих источника значения `top_k`:


| Источник | Значение |
| :-- | :-- |
| Веб-админка (UI) | `TOP-K: 5`, `Voyage TOP-K: 1` |
| Config Snapshot в трейсе | `SEMANTIC_SEARCH_TOP_K: 3` |
| Фактическое поведение бота | `top_k=10`, `confidence_cap=5` |

Это означает разрыв между `POST /api/admin/config` и runtime-объектом,
который читает `answer_adaptive.py`.

### 1.1 Диагностика — найти разрыв

```
[ ] 1.1  Открыть api/admin_routes.py
         Найти endpoint POST /api/admin/config
         Определить: что именно он обновляет после получения данных?
         Варианты: записывает в файл / обновляет in-memory объект /
                   обновляет os.environ / только валидирует

[ ] 1.2  Открыть bot_agent/answer_adaptive.py
         Найти все места где читается top_k, confidence_cap, rerank_top_k
         Определить: они берутся из config.py (статика при импорте) или
                     из runtime-объекта (динамика)?

[ ] 1.3  Задокументировать разрыв прямо в коде комментарием перед правкой:
         # BUG v0.6.0: admin POST /config writes to X,
         # but answer_adaptive reads from Y — no sync
         # Fixed below
```


### 1.2 Починить связку admin → runtime

```
[ ] 1.4  Создать или найти singleton runtime-конфиг:
         Если его нет — создать bot_agent/runtime_config.py:

         class RuntimeConfig:
             _instance = None

             def __init__(self):
                 self.retrieval_top_k: int = int(
                     os.getenv("RETRIEVAL_TOP_K", "5"))
                 self.voyage_top_k: int = int(
                     os.getenv("VOYAGE_TOP_K", "5"))
                 self.min_relevance: float = float(
                     os.getenv("MIN_RELEVANCE_THRESHOLD", "0.1"))
                 self.confidence_threshold_fast_path: float = float(
                     os.getenv("CONFIDENCE_FAST_PATH_THRESHOLD", "0.40"))

             @classmethod
             def get(cls) -> "RuntimeConfig":
                 if cls._instance is None:
                     cls._instance = RuntimeConfig()
                 return cls._instance

             def update(self, **kwargs) -> dict:
                 changed = {}
                 for key, value in kwargs.items():
                     if hasattr(self, key):
                         old = getattr(self, key)
                         setattr(self, key, type(old)(value))
                         changed[key] = {"from": old, "to": value}
                 return changed

         runtime_config = RuntimeConfig.get()

[ ] 1.5  В answer_adaptive.py заменить все прямые обращения к config.py
         на вызовы RuntimeConfig.get():
         # Было: top_k = config.RETRIEVAL_TOP_K
         # Стало: top_k = RuntimeConfig.get().retrieval_top_k

[ ] 1.6  В admin_routes.py обновить POST /api/admin/config:
         - Парсить входящие поля
         - Вызывать RuntimeConfig.get().update(**validated_fields)
         - Возвращать в ответе:
           {
             "status": "ok",
             "applied": true,
             "changes": {"retrieval_top_k": {"from": 3, "to": 5}},
             "not_applied": []   # поля, которые не нашлись в RuntimeConfig
           }

[ ] 1.7  Установить правильные дефолтные значения (важно!):
         В RuntimeConfig.__init__ и в .env.example прописать:
         RETRIEVAL_TOP_K=5
         VOYAGE_TOP_K=5
         MIN_RELEVANCE_THRESHOLD=0.1
         CONFIDENCE_FAST_PATH_THRESHOLD=0.40
         Это устраняет расхождение top_k=10 из старых захардкоженных значений.
```


### 1.3 Персистентность конфига (важно!)

```
[ ] 1.8  Решить вопрос сохранения конфига между перезапусками:
         При изменении через админку — сохранять в файл
         bot_psychologist/config_override.json:
         {"retrieval_top_k": 5, "voyage_top_k": 5}

[ ] 1.9  В RuntimeConfig.__init__ добавить загрузку оверрайда:
         override_path = Path("config_override.json")
         if override_path.exists():
             overrides = json.loads(override_path.read_text())
             for k, v in overrides.items():
                 if hasattr(self, k):
                     setattr(self, k, type(getattr(self, k))(v))
             logger.info(f"[CONFIG] Loaded overrides: {overrides}")

[ ] 1.10 В RuntimeConfig.update() после изменений — сохранять в файл:
         override_path.write_text(json.dumps(current_state, indent=2))

[ ] 1.11 Добавить config_override.json в .gitignore

[ ] 1.12 В .env.example добавить секцию с комментарием:
         # Runtime config (можно менять через /admin без перезапуска)
         # Значения ниже — дефолты. Изменения через UI
         # сохраняются в config_override.json
         RETRIEVAL_TOP_K=5
         VOYAGE_TOP_K=5
         MIN_RELEVANCE_THRESHOLD=0.1
         CONFIDENCE_FAST_PATH_THRESHOLD=0.40
```


### 1.4 Тест блока

```
[ ] 1.13 Написать tests/test_admin_config.py:

         def test_admin_config_hot_reload(client, bot_client):
             # 1. Получить текущий top_k
             r = client.get("/api/admin/config")
             original_top_k = r.json()["retrieval_top_k"]

             # 2. Изменить через админку
             r = client.post("/api/admin/config",
                             json={"retrieval_top_k": 7})
             assert r.json()["applied"] == True
             assert r.json()["changes"]["retrieval_top_k"]["to"] == 7

             # 3. Отправить вопрос боту
             r = bot_client.post("/api/v1/questions/adaptive",
                                 json={"query": "что такое самосознание"})

             # 4. Проверить в трейсе
             trace = get_last_trace(r)
             assert trace["config_snapshot"]["SEMANTIC_SEARCH_TOP_K"] == 7

             # 5. Восстановить
             client.post("/api/admin/config",
                         json={"retrieval_top_k": original_top_k})

         def test_config_persists_after_reload():
             # Проверить что config_override.json создаётся
             # и значения из него загружаются при новом RuntimeConfig()
             pass

[ ] 1.14 Smoke-тест блока 1:
         - Запустить бота
         - В админке установить TOP-K: 7
         - Отправить любой вопрос
         - В трейсе (Config Snapshot) убедиться: SEMANTIC_SEARCH_TOP_K = 7
         - В логах нет top_k=10

[ ] 1.15 Коммит:
         git commit -m "feat(config): fix admin hot-reload,
           add RuntimeConfig singleton, persist overrides [БЛОК 1]"
```


---

## БЛОК 2 — Фикс поведения: бот перестаёт зеркалить вопросы

### Проблема

При каждом ответе бот начинает с перефразирования вопроса:

> *"Я слышу, что ты хочешь не просто понять поведение — а увидеть,
> что внутри запускает этот паттерн"*

Это происходит независимо от темы, SD-уровня пользователя и типа вопроса.
Источник — инструкция в одном или нескольких файлах промптов.

### 2.1 Найти источник инструкции

```
[ ] 2.1  Просмотреть ВСЕ файлы промптов (открыть каждый и прочитать):
         - bot_agent/prompt_system_base.md
         - bot_agent/prompt_sd_beige.md
         - bot_agent/prompt_sd_purple.md
         - bot_agent/prompt_sd_red.md
         - bot_agent/prompt_sd_blue.md
         - bot_agent/prompt_sd_orange.md
         - bot_agent/prompt_sd_green.md
         - bot_agent/prompt_sd_yellow.md
         - bot_agent/prompt_system_level_beginner.md (если существует)
         - bot_agent/prompt_system_level_intermediate.md (если существует)
         - bot_agent/prompt_system_level_advanced.md (если существует)

[ ] 2.2  Искать ключевые фразы в каждом файле (grep + ручная проверка):
         grep -rn "перефразир\|отрази\|покажи что услышал\
           \|I hear\|я слышу\|ты хочешь\|зеркал\|reflect\|rephrase\
           \|начни с\|начинай с" bot_agent/

[ ] 2.3  Зафиксировать в PRD_TASKS_v0.6.0.md: в каком файле(ах) найдена
         инструкция и точный текст фразы
```


### 2.2 Убрать или смягчить инструкцию

```
[ ] 2.4  Если инструкция явная ("всегда начинай с отражения запроса",
         "перефразируй вопрос пользователя" и т.п.) — удалить её полностью
         из всех найденных файлов.

[ ] 2.5  Если инструкция мягкая ("можешь отразить", "при необходимости
         покажи понимание") — заменить на явный запрет:

         Добавить в prompt_system_base.md в секцию ограничений:
         """
         ВАЖНО: Никогда не начинай ответ с перефразирования вопроса
         пользователя. Не используй конструкции "Я слышу, что ты...",
         "Ты хочешь...", "Ты говоришь...". Начинай сразу с содержательного
         ответа по существу вопроса.
         """

[ ] 2.6  Если инструкция находится в нескольких файлах — убрать из каждого.

[ ] 2.7  Сохранить все изменённые .md файлы промптов.
```


### 2.3 Тесты поведения (все SD-уровни)

```
[ ] 2.8  Написать tests/test_prompt_behavior.py с параметризованными тестами
         по ВСЕМ SD-уровням:

         import pytest

         MIRROR_PHRASES = [
             "я слышу",
             "ты хочешь",
             "ты говоришь",
             "я понимаю что ты",
             "i hear",
             "you want",
             "ты ищешь",
         ]

         SD_LEVELS = ["BEIGE", "PURPLE", "RED", "BLUE",
                      "ORANGE", "GREEN", "YELLOW"]

         @pytest.mark.parametrize("sd_level", SD_LEVELS)
         def test_no_mirror_phrase_in_response(sd_level, mock_bot_with_level):
             """Бот не должен начинать с зеркала ни на одном SD-уровне"""
             bot = mock_bot_with_level(sd_level)
             response = bot.answer("Хочу понять свой паттерн избегания")
             first_sentence = response.split(".").lower()
             for phrase in MIRROR_PHRASES:
                 assert phrase not in first_sentence, \
                     f"SD={sd_level}: ответ начинается с зеркала: {phrase!r}"

         @pytest.mark.parametrize("sd_level", SD_LEVELS)
         def test_no_mirror_on_greeting(sd_level, mock_bot_with_level):
             bot = mock_bot_with_level(sd_level)
             response = bot.answer("Привет!")
             first_sentence = response.split(".").lower()
             for phrase in MIRROR_PHRASES:
                 assert phrase not in first_sentence

[ ] 2.9  Вручную проверить в UI:
         Отправить "Хочу понять свой паттерн избегания ответственности"
         → ответ НЕ начинается с "Я слышу..." или похожей фразы
         → ответ начинается с содержательного текста

[ ] 2.10 Коммит:
         git commit -m "fix(prompt): remove mirror-question instruction,
           add parametrized tests for all SD levels [БЛОК 2]"
```


---

## БЛОК 3 — Очистка уровней сложности (Начинающий/Средний/Продвинутый)

### Контекст

В репозитории существуют файлы промптов уровней:

- `prompt_system_level_beginner.md` (~358 симв.)
- `prompt_system_level_intermediate.md` (~348 симв.)
- `prompt_system_level_advanced.md` (~405 симв.)

Также в веб-админке могут быть UI-элементы для этих уровней.
Неизвестно применяются ли они в pipeline. Блок 0 должен был это
определить — используй значение `LEVELS_USED` из PRD_TASKS_v0.6.0.md.

### 3.1 Сценарий A: уровни НЕ применяются (LEVELS_USED = no)

```
[ ] 3.1a Удалить файлы промптов уровней:
         rm bot_agent/prompt_system_level_beginner.md
         rm bot_agent/prompt_system_level_intermediate.md
         rm bot_agent/prompt_system_level_advanced.md

[ ] 3.2a В admin_routes.py найти и удалить:
         - Эндпоинты типа POST /api/admin/user-level
         - Pydantic-модели UserLevelRequest или аналоги
         - Импорты связанные с уровнями

[ ] 3.3a В bot_agent/__init__.py и других модулях удалить импорты:
         grep -rn "level_beginner\|level_intermediate\|level_advanced\
           \|prompt_system_level" --include="*.py" bot_psychologist/
         Удалить все найденные импорты и вызовы.

[ ] 3.4a В web_ui/ найти и удалить UI-элементы уровней:
         grep -rn "beginner\|intermediate\|advanced\|user.level\
           \|уровень сложности" web_ui/
         Удалить все найденные элементы (переключатель уровня,
         dropdown, labels).

[ ] 3.5a Добавить комментарий в местах удаления:
         # REMOVED v0.6.0: user complexity levels (beginner/intermediate/
         # advanced) — not used in v0.5+ pipeline.
         # SD-level adaptation is handled via LLM prompt (sd_classifier.py)

[ ] 3.6a Проверить что sd_classifier.py НЕ затронут (он нужен!):
         sd_classifier.py определяет SD-уровень по Спиральной Динамике
         и используется для передачи в LLM-промпт. Это ДРУГАЯ система.
         НЕ удалять.
```


### 3.2 Сценарий B: уровни применяются (LEVELS_USED = yes)

```
[ ] 3.1b Определить точно где и как применяются:
         Найти место в answer_adaptive.py или llm_answerer.py где
         выбирается prompt_system_level_*.md

[ ] 3.2b Определить как уровень назначается пользователю:
         Откуда берётся user_level? Из сессии / из admin API /
         из классификатора?

[ ] 3.3b Задокументировать механизм в README.md:
         ## Уровни сложности пользователя
         Описание: как назначается, где используется, как менять через UI

[ ] 3.4b Убедиться что в UI есть понятный элемент управления уровнем

[ ] 3.5b В Config Snapshot трейса сделать видимым активный уровень:
         "user_complexity_level": "intermediate"

[ ] 3.6b Добавить в CHANGELOG.md:
         - Documented user complexity levels (beginner/intermediate/advanced)
           — confirmed active in pipeline
```


### 3.3 Очистка трейса от мёртвых полей (оба сценария)

```
[ ] 3.7  В api/models.py найти модель TraceData (или аналог)
         Удалить поля:
         - SD_CONFIDENCE_THRESHOLD (если undefined)
         - stage_filter_* (удалён в v0.5.0)
         - complexity_cap (удалён в v0.5.0)
         - Любые поля с None/undefined в Config Snapshot

[ ] 3.8  Проверить в трейсе через UI:
         В Config Snapshot нет полей с undefined или null значениями
         Все отображаемые поля реально используются в pipeline

[ ] 3.9  Коммит:
         git commit -m "refactor(admin): remove/document user complexity
           levels, clean trace undefined fields [БЛОК 3]"
```


---

## БЛОК 4 — Трейс 2.0: вкладка «Полотно LLM»

### Цель

Добавить в панель трейса новую секцию **«Полотно LLM»** в конце
развёрнутого трейса. Она показывает всё что реально ушло в OpenAI при
данном запросе. Это главный инструмент отладки качества ответов.

**Важно:** перед началом реализации агент должен знать:

- `FRONTEND_STACK` из Блока 0 — писать компонент под нужный стек
- `TRACE_STORAGE` из Блока 0 — знать откуда читать трейс


### 4.1 Бэкенд — модель данных

```
[ ] 4.1  В api/models.py добавить новые модели:

         from typing import List, Optional
         from pydantic import BaseModel

         class RetrievedBlockTrace(BaseModel):
             block_id: str
             score: float
             text: str
             sd_tag: Optional[str] = None

         class LLMPayloadTrace(BaseModel):
             system_prompt: str           # полный финальный system prompt
             sd_level: str                # "GREEN", "BLUE", etc.
             sd_prompt: str               # содержимое активного SD-промпта
             retrieved_blocks: List[RetrievedBlockTrace]
             history_turns: List[dict]    # последние N turns как в messages[]
             final_user_message: str      # точный текст user-сообщения
             messages_raw: List[dict]     # полный messages[] для OpenAI
             model: str
             timestamp: str
             # Мета для фронтенда
             system_prompt_chars: int
             sd_prompt_chars: int
             retrieved_blocks_count: int
             history_turns_count: int

[ ] 4.2  В существующую модель TraceData (или аналог) добавить поле:
         llm_payload: Optional[LLMPayloadTrace] = None
```


### 4.2 Бэкенд — перехват payload

```
[ ] 4.3  В bot_agent/llm_answerer.py перед вызовом
         client.chat.completions.create(...) добавить захват:

         from datetime import datetime, timezone

         # Перед вызовом OpenAI:
         if trace_enabled and current_trace is not None:
             current_trace.llm_payload = LLMPayloadTrace(
                 system_prompt=system_message_content,
                 sd_level=sd_level or "UNKNOWN",
                 sd_prompt=sd_prompt_content or "",
                 retrieved_blocks=[
                     RetrievedBlockTrace(
                         block_id=b.get("id", ""),
                         score=b.get("score", 0.0),
                         text=b.get("text", ""),
                         sd_tag=b.get("sd_tag")
                     ) for b in retrieved_blocks
                 ],
                 history_turns=history_turns,
                 final_user_message=user_query,
                 messages_raw=messages,
                 model=model_name,
                 timestamp=datetime.now(timezone.utc).isoformat(),
                 system_prompt_chars=len(system_message_content),
                 sd_prompt_chars=len(sd_prompt_content or ""),
                 retrieved_blocks_count=len(retrieved_blocks),
                 history_turns_count=len(history_turns),
             )

[ ] 4.4  Убедиться что llm_answerer.py имеет доступ к объекту current_trace.
         Если передаётся через параметр — добавить параметр trace=None.
         Если через глобальный контекст — проверить thread-safety.

[ ] 4.5  В answer_adaptive.py убедиться что retrieved_blocks, sd_level,
         sd_prompt_content, history_turns доступны в месте вызова
         llm_answerer и передаются в него.
```


### 4.3 Бэкенд — новый endpoint

```
[ ] 4.6  В api/debug_routes.py добавить endpoint:

         @router.get(
             "/api/debug/session/{session_id}/llm-payload",
             response_model=Optional[LLMPayloadTrace]
         )
         async def get_llm_payload(session_id: str):
             """
             Возвращает полный LLM payload последнего запроса сессии.
             Используется для вкладки Полотно LLM в трейсе.
             """
             trace = get_trace_by_session(session_id)
             if trace is None:
                 raise HTTPException(status_code=404,
                                     detail="Session not found")
             if trace.llm_payload is None:
                 raise HTTPException(status_code=404,
                                     detail="No LLM payload for this session")
             return trace.llm_payload

[ ] 4.7  Убедиться что функция get_trace_by_session существует и корректна.
         Если трейс хранится in-memory (словарь session_id → TraceData) —
         добавить TTL очистки через asyncio или простой LRU cache (maxsize=100)
         чтобы избежать утечки памяти.

[ ] 4.8  Добавить endpoint в роутер в api/main.py если он там не подключён.
```


### 4.4 Фронтенд — компонент «Полотно LLM»

```
[ ] 4.9  Перед написанием кода — определить используемый стек
         (из FRONTEND_STACK в PRD_TASKS_v0.6.0.md):

         Если React — создать web_ui/src/components/LLMPayloadPanel.jsx
         Если Vue — создать web_ui/src/components/LLMPayloadPanel.vue
         Если Vanilla JS / Jinja2 — создать web_ui/static/js/llm_payload.js
           и шаблон web_ui/templates/components/llm_payload.html

[ ] 4.10 Реализовать компонент согласно структуре:

         ┌─────────────────────────────────────────────────┐
         │ ▼ Полотно LLM                  [Скопировать всё]│
         ├─────────────────────────────────────────────────┤
         │  ▶ System Prompt         (2113 симв.)           │
         │  ▶ SD Промпт: GREEN       (549 симв.)           │
         │  ▶ Retrieved Blocks      (5 блоков)             │
         │  ▶ История диалога       (2 turn)               │
         │  ▶ Финальный вопрос                             │
         │  ▶ Итоговый messages[]   (raw JSON)             │
         └─────────────────────────────────────────────────┘

         Требования к каждой секции:
         - Каждая подсекция раскрывается/сворачивается по клику (треугольник)
         - По умолчанию ВСЕ подсекции свёрнуты
         - Текст — чистый, читаемый, без JSON-эскейпинга
         - «Retrieved Blocks»: для каждого блока показывать
           block_id | score | sd_tag | полный текст
         - «Итоговый messages[]»: моноширинный шрифт,
           подсветка синтаксиса JSON (можно через CSS-класс или
           библиотеку highlight.js / Prism.js если уже подключена)
         - Кнопка «Скопировать всё» копирует весь payload как plain text

[ ] 4.11 Реализовать lazy load:
         - Компонент делает GET /api/debug/session/{id}/llm-payload
           ТОЛЬКО при первом раскрытии секции «Полотно LLM»
         - До раскрытия — показывать только заголовок с треугольником
         - При загрузке — показывать spinner
         - При ошибке — показывать сообщение "Payload недоступен"

[ ] 4.12 Подключить LLMPayloadPanel в конец существующего компонента
         трейса (TracePanel или аналог), после Config Snapshot.
         session_id должен быть доступен в пропсах / данных трейса.
```


### 4.5 Тест блока

```
[ ] 4.13 Написать тест api: tests/test_llm_payload_endpoint.py:

         def test_llm_payload_exists_after_question(client):
             # Отправить вопрос
             r = client.post("/api/v1/questions/adaptive",
                             json={"query": "что такое самосознание",
                                   "session_id": "test-session-001"})
             assert r.status_code == 200

             # Получить payload
             r = client.get(
                 "/api/debug/session/test-session-001/llm-payload")
             assert r.status_code == 200
             payload = r.json()

             assert "messages_raw" in payload
             assert len(payload["messages_raw"]) > 0
             assert payload["retrieved_blocks_count"] > 0
             assert payload["sd_level"] in [
                 "BEIGE","PURPLE","RED","BLUE",
                 "ORANGE","GREEN","YELLOW","UNKNOWN"
             ]
             # system_prompt не должен быть пустым
             assert len(payload["system_prompt"]) > 100

[ ] 4.14 Smoke-тест в UI:
         - Отправить вопрос через интерфейс
         - Открыть трейс
         - В конце трейса появилась секция «Полотно LLM»
         - Раскрыть «Retrieved Blocks» — видны 5 блоков с текстом
         - Раскрыть «Итоговый messages[]» — виден JSON с system/user ролями
         - Кнопка «Скопировать всё» работает

[ ] 4.15 Коммит:
         git commit -m "feat(trace): add LLM Payload panel with 6
           collapsible sections, lazy load, copy button [БЛОК 4]"
```


---

## БЛОК 5 — Очистка наследия: граф, логи, warmup

### 5.1 Условная инициализация KnowledgeGraphClient

```
[ ] 5.1  В bot_agent/data_loader.py найти вызов KnowledgeGraphClient.
         Обернуть в условие:

         ENABLE_KNOWLEDGE_GRAPH = os.getenv(
             "ENABLE_KNOWLEDGE_GRAPH", "false").lower() == "true"

         if ENABLE_KNOWLEDGE_GRAPH:
             graph_client = KnowledgeGraphClient(...)
             logger.info("[GRAPH] KnowledgeGraphClient initialized")
         else:
             graph_client = None
             logger.info(
                 "[GRAPH] KnowledgeGraphClient disabled "
                 "(ENABLE_KNOWLEDGE_GRAPH=false)"
             )

[ ] 5.2  В bot_agent/path_builder.py добавить guard в начало функции:

         def build_path(query, graph_client, ...):
             if graph_client is None or not graph_client.has_data():
                 logger.debug(
                     "[PATH] graph_client skipped — not initialized or no data"
                 )
                 return default_path
             # ... остальная логика

[ ] 5.3  В .env.example добавить:
         # Knowledge Graph (отключён по умолчанию)
         # Включить только если загружены graph-данные в Bot_data_base
         ENABLE_KNOWLEDGE_GRAPH=false
```


### 5.2 Устранение дублирования логирования блоков

```
[ ] 5.4  В bot_agent/answer_adaptive.py найти двойное логирование блоков.
         Признак дублирования: одни и те же 5 block_id логируются дважды,
         например:
         [RETRIEVAL] Final blocks to LLM: [block_1, block_2, ...]
         ...несколько строк позже...
         [SOURCES] block_1 | score=0.92 | ...

[ ] 5.5  Оставить только одно логирование — SOURCES после получения
         ответа от LLM (это более информативно — рядом с результатом):
         logger.info(f"[SOURCES] Блоки переданные в LLM: "
                     f"{[b['id'] for b in retrieved_blocks]}")

[ ] 5.6  Удалить строку "Final blocks to LLM" или аналогичную,
         которая дублирует SOURCES.
```


### 5.3 Обновление версии

```
[ ] 5.7  В bot_agent/__init__.py найти строку инициализации:
         # Было (пример):
         logger.info("Bot Agent v0.4.0 initialized Phase 1 Phase 2 ...")
         # Стало:
         logger.info(
             "Bot Agent v0.6.0 initialized | "
             "pipeline: semantic→rerank→top5→llm | "
             f"graph: {'enabled' if ENABLE_KNOWLEDGE_GRAPH else 'disabled'}"
         )
```


### 5.4 Warmup embedding-модели

```
[ ] 5.8  В bot_agent/semantic_memory.py найти место lazy-загрузки модели.
         Это может выглядеть как:
         def _ensure_model_loaded(self):
             if self._model is None:
                 self._model = SentenceTransformer(...)  # 7 секунд

[ ] 5.9  В api/main.py найти секцию [WARMUP] (startup event).
         Если её нет — создать:

         from contextlib import asynccontextmanager

         @asynccontextmanager
         async def lifespan(app: FastAPI):
             # === WARMUP ===
             logger.info("[WARMUP] Starting warmup...")
             try:
                 from bot_agent.semantic_memory import semantic_memory
                 semantic_memory._load_model()
                 logger.info("[WARMUP] Embedding model loaded ✓")
             except Exception as e:
                 logger.warning(f"[WARMUP] Embedding model load failed: {e}")
             yield
             # === SHUTDOWN ===
             logger.info("[SHUTDOWN] Bot stopped")

         app = FastAPI(lifespan=lifespan)

[ ] 5.10 Проверить в логах при старте:
         [WARMUP] Embedding model loaded ✓
         После первого запроса пользователя НЕТ строки типа:
         [SEMANTIC] loading model sentence-transformers/...
```


### 5.5 Тест и финальный коммит блока

```
[ ] 5.11 Проверить логи при старте: [GRAPH] KnowledgeGraphClient disabled
[ ] 5.12 Проверить что warmup отрабатывает при старте (не при запросе)
[ ] 5.13 Отправить первый запрос после старта — замерить время ответа.
         Должно быть <= 30 сек (без 7 сек на загрузку модели)

[ ] 5.14 Коммит:
         git commit -m "chore(cleanup): disable graph_client by default,
           fix embedding warmup, dedup logs, bump version v0.6.0 [БЛОК 5]"
```


---

## БЛОК 6 — Финальная проверка и релиз

### 6.1 Полный прогон тестов

```
[ ] 6.1  python -m pytest tests/ -v --tb=short > tests_v060_after.txt 2>&1
[ ] 6.2  diff tests_v060_before.txt tests_v060_after.txt
[ ] 6.3  Все тесты зелёные ИЛИ помечены @pytest.mark.xfail(reason="...")
         с объяснением почему xfail допустим
[ ] 6.4  Новых FAILED тестов не должно быть
```


### 6.2 Сквозной smoke-тест (живой UI)

```
[ ] 6.5  Запустить Bot_data_base:
         cd Bot_data_base && python -m uvicorn api.main:app --port 8003

[ ] 6.6  Запустить бота:
         cd bot_psychologist && python -m uvicorn api.main:app --port 8000

[ ] 6.7  Открыть localhost:3000 (или порт веб-UI)

[ ] 6.8  Тест 1 — Приветствие:
         Отправить: "Привет!"
         Ожидать: FAST_PATH, CHUNKS: 0, ответ не начинается с "Я слышу"

[ ] 6.9  Тест 2 — Содержательный вопрос:
         Отправить: "Хочу понять свой паттерн избегания ответственности"
         Ожидать:
         - CHUNKS: 5 (не 0, не 10)
         - Нет строк STAGE_FILTER, SD_FILTER в трейсе
         - SD-уровень виден в SYSTEM PROMPT (PREVIEW) в LLM Calls
         - Ответ начинается с содержательного текста (не с зеркала)

[ ] 6.10 Тест 3 — Трейс Полотно LLM:
         Отправить: "что такое Самосознание в НейроСталкинге"
         Открыть трейс → в конце появился блок «Полотно LLM»
         Раскрыть каждую из 6 подсекций — все раскрываются
         В «Retrieved Blocks» видны 5 блоков с текстом
         В «Итоговый messages[]» виден system prompt и вопрос

[ ] 6.11 Тест 4 — Конфиг из админки:
         В админке установить TOP-K: 7
         Отправить вопрос
         В трейсе Config Snapshot: SEMANTIC_SEARCH_TOP_K = 7
         Вернуть TOP-K: 5

[ ] 6.12 Проверить Pipeline Timeline в трейсе:
         ✅ Классификатор состояния
         ✅ SD классификатор
         ✅ Retrieval
         ❌ SD фильтр — НЕТ (удалён в v0.5.0)
         ❌ Stage фильтр — НЕТ (удалён в v0.5.0)
         ✅ Rerank
         ✅ LLM
         ✅ Полотно LLM (новое)
         ✅ Форматирование
```


### 6.3 Обновление документации

```
[ ] 6.13 Обновить README.md:
         - Убрать упоминания Stage-фильтра и SD-фильтра как фильтров блоков
         - Добавить/обновить раздел "Архитектура ретривала":
           Запрос → Semantic Search → Voyage Reranker → TOP-5 → LLM
         - Добавить раздел "Отладка: Полотно LLM" с описанием новой вкладки

[ ] 6.14 Обновить CHANGELOG.md:
         ## [0.6.0] — 2026-03-25
         ### Added
         - Трейс 2.0: вкладка «Полотно LLM» с 6 сворачиваемыми секциями
         - Hot-reload конфига из веб-админки без перезапуска бота
         - Персистентность конфига в config_override.json
         - Warmup embedding-модели при старте (устраняет +7 сек)
         ### Fixed
         - Бот больше не начинает ответы с перефразирования вопроса
         - Конфиг из веб-админки теперь применяется к runtime (top_k=5)
         ### Removed
         - Промпты уровней beginner/intermediate/advanced (мёртвый код)
         - KnowledgeGraphClient инициализируется только при
           ENABLE_KNOWLEDGE_GRAPH=true
         - Дублирование логирования retrieved blocks
         ### Changed
         - Дефолтные значения: RETRIEVAL_TOP_K=5, VOYAGE_TOP_K=5

[ ] 6.15 Финальный коммит:
         git add -A
         git commit -m "chore(release): v0.6.0 — cleanup, trace 2.0,
           behavior fixes, hot-reload config"

[ ] 6.16 Создать PR: fix/v0.6.0-cleanup-trace-behavior → main
         В описании PR указать:
         - Что удалено (уровни, граф, дубли)
         - Что исправлено (зеркало, конфиг, warmup)
         - Что добавлено (Полотно LLM, hot-reload)
         - Ссылка на PRD_TASKS_v0.6.0.md
```


---

## Критерии приёмки (Definition of Done)

| \# | Критерий | Как проверить |
| :-- | :-- | :-- |
| 1.1 | Конфиг из админки применяется к runtime | Config Snapshot = значения из UI |
| 1.2 | TOP-K дефолт = 5 (не 10) | Логи при запросе без изменений |
| 1.3 | Конфиг сохраняется после рестарта | config_override.json существует |
| 2.1 | Бот не начинает с зеркала (все 7 SD-уровней) | test_prompt_behavior.py |
| 3.1 | Нет undefined полей в Config Snapshot | Визуально в трейсе |
| 4.1 | Вкладка «Полотно LLM» отображается | localhost:3000 |
| 4.2 | Все 6 подсекций сворачиваются | Клик на треугольник |
| 4.3 | messages[] совпадает с реальным вызовом | OpenAI dashboard |
| 4.4 | Lazy load — нет лишних запросов до открытия | DevTools Network |
| 5.1 | graph_client не инициализируется при false | Логи при старте |
| 5.4 | Модель грузится при warmup, не при запросе | Нет [SEMANTIC] loading... |
| 6.1 | Все тесты зелёные | pytest tests/ |
| 6.2 | Время ответа ≤ 30 сек | Замер первого запроса |


---

## Риски и митигации

| Риск | Вероятность | Митигация |
| :-- | :-- | :-- |
| Фронтенд не React — код компонента не подходит | Средняя | Блок 0 определяет стек до написания кода |
| Конфиг in-memory — при рестарте сбрасывается | Высокая | config_override.json (Блок 1.3) |
| Трейс хранится без TTL — утечка памяти | Средняя | LRU cache maxsize=100 (Блок 4.3) |
| SD-зеркало в нескольких промптах — тест проходит, баг остаётся | Средняя | Параметризованный тест по всем 7 SD-уровням |
| Bot_data_base 503 при интеграционных тестах | Высокая | Тесты мокируют API или запускаются с поднятой базой |
| Voyage API недоступен без VPN | Средняя | TF-IDF fallback сохранён, тест сценария fallback |


---

## Порядок коммитов

```bash
git commit -m "checkpoint: before v0.6.0 — state before cleanup"
git commit -m "feat(config): fix admin hot-reload, RuntimeConfig singleton,
  persist overrides [БЛОК 1]"
git commit -m "fix(prompt): remove mirror-question instruction,
  parametrized tests all SD levels [БЛОК 2]"
git commit -m "refactor(admin): remove/document user complexity levels,
  clean trace undefined fields [БЛОК 3]"
git commit -m "feat(trace): add LLM Payload panel 6 collapsible sections,
  lazy load, copy button [БЛОК 4]"
git commit -m "chore(cleanup): disable graph_client by default,
  fix embedding warmup, dedup logs, bump version v0.6.0 [БЛОК 5]"
git commit -m "chore(release): v0.6.0 — cleanup, trace 2.0,
  behavior fixes, hot-reload config"
```


---

## Сводная карта файлов

```
bot_psychologist/
├── api/
│   ├── admin_routes.py        # БЛОК 1 — hot-reload, RuntimeConfig
│   ├── debug_routes.py        # БЛОК 4 — /llm-payload endpoint
│   ├── models.py              # БЛОК 3, 4 — TraceData + LLMPayloadTrace
│   └── main.py                # БЛОК 5 — lifespan warmup
├── bot_agent/
│   ├── runtime_config.py      # БЛОК 1 — новый файл (singleton)
│   ├── answer_adaptive.py     # БЛОК 1, 4, 5 — RuntimeConfig + payload + деdup
│   ├── llm_answerer.py        # БЛОК 4 — перехват messages[]
│   ├── data_loader.py         # БЛОК 5 — guard graph_client
│   ├── path_builder.py        # БЛОК 5 — guard graph_client
│   ├── semantic_memory.py     # БЛОК 5 — warmup загрузка модели
│   ├── __init__.py            # БЛОК 5 — версия v0.6.0
│   ├── prompt_system_base.md  # БЛОК 2 — убрать инструкцию-зеркало
│   ├── prompt_sd_*.md         # БЛОК 2 — проверить все 7 SD-промптов
│   └── prompt_system_level_*.md  # БЛОК 3 — удалить (если не применяются)
├── web_ui/
│   └── .../LLMPayloadPanel.*  # БЛОК 4 — новый компонент
├── tests/
│   ├── test_admin_config.py   # БЛОК 1 — новый
│   ├── test_prompt_behavior.py # БЛОК 2 — новый, 7 SD-уровней
│   └── test_llm_payload_endpoint.py  # БЛОК 4 — новый
├── config_override.json       # БЛОК 1 — создаётся runtime (в .gitignore)
├── .env.example               # БЛОК 1, 5 — дефолты + ENABLE_KNOWLEDGE_GRAPH
├── README.md                  # БЛОК 6 — обновить архитектуру
└── CHANGELOG.md               # БЛОК 6 — v0.6.0
```


---

*Агент: после прочтения этого PRD — первым действием создай
`PRD_TASKS_v0.6.0.md` с полным чеклистом. Затем выполняй Блок 0.
Без Блока 0 не начинать Блоки 1–4: там критически важны
FRONTEND_STACK, CONFIG_SOURCE, TRACE_STORAGE, LEVELS_USED.*

```
```

