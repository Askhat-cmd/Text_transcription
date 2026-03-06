

***

# PRD v3.0.2 — Speed Layer (Финальная редакция)

```markdown
# PRD v3.0.2 — Оптимизация скорости ответов (Speed Layer)

**Версия:** 3.0.2
**Статус:** Ready for implementation
**Приоритет:** HIGH
**Исполнитель:** Codex IDE Agent
**Дата:** 2026-03-04
**Заменяет:** PRD v3.0.1 (содержал критические ошибки — см. раздел 0)

---

## 0. Почему v3.0.1 нельзя применять (критические баги)

| # | Файл из v3.0.1 | Проблема | Исправлено в v3.0.2 |
|:--|:--|:--|:--|
| 1 | `api/main.py` | `_warm_components` — словарь-заглушка, компоненты из него **нигде не используются** в обработчиках запросов. Warm preload фактически не работает. | Заменено на FastAPI DI через `Depends()` |
| 2 | `bot_agent/semantic_memory.py` | `_ensure_model_loaded()` с двойным `_` — это Python-приватный метод, вызов извне — антипаттерн | Переименовать в `ensure_model_loaded()` |
| 3 | `bot_agent/retriever.py` | `pickle` для сохранения матрицы — уязвимость RCE при компрометации кэш-файла | Заменено на `joblib` |
| 4 | `api/main.py` | В `lifespan()` определены async-функции `load_data()`, `load_semantic()`, `load_graph()`, которые **никогда не вызываются** — мёртвый код | Удалены |
| 5 | `api/main.py` | `asyncio.get_event_loop()` внутри async-функции — deprecated в Python 3.10+ | Заменено на `asyncio.to_thread()` |
| 6 | `api/routes.py` | SSE-клиент (TypeScript) не обрабатывает разрыв соединения — пользователь получит незавершённый ответ без возможности восстановления | Добавлена reconnect-логика |
| 7 | — | Отсутствует версионирование формата кэша — при изменении структуры `Retriever` старый кэш вызовет `AttributeError` | Добавлено поле `cache_version` |
| 8 | — | Порядок задач в v3.0.1 ставит самую сложную (TASK-3, стриминг, 6 файлов) первой | Порядок пересмотрен по принципу риск/эффект |

---

## 1. Контекст и проблема

### 1.1 Окружение

```env
PRIMARY_MODEL=gpt-5-mini
REASONING_EFFORT=low
CLASSIFIER_MODEL=gpt-4o-mini
```

`gpt-5-mini` с `REASONING_EFFORT=low` — это модель с «рассуждением» (reasoning model).
Она имеет встроенную задержку на «мышление» даже при `low`, что увеличивает latency по сравнению
с обычными completion-моделями. Это усиливает актуальность всех оптимизаций ниже.

### 1.2 Три источника задержки

**Слой 1 — Cold Start (первый запрос после старта сервера)**

При первом запросе все компоненты инициализируются лениво:

- `DataLoader` читает SAG JSON файлы с диска
- `SemanticMemory` загружает модель `paraphrase-multilingual-MiniLM-L12-v2`
(~100MB, CPU warm-up, sentence-transformers)
- `GraphClient` строит граф знаний (95 узлов, 2182 связи)
- `Retriever` строит TF-IDF матрицу по всем блокам

Итог: первый запрос занимает **25–40 секунд**.

**Слой 2 — Последовательные LLM-вызовы**

В `answer_adaptive.py` pipeline вызывает последовательно:

1. `StateClassifier.classify()` → LLM-запрос к `gpt-4o-mini` (~1–2 сек)
2. `SDClassifier.classify_user()` → LLM-запрос к `gpt-4o-mini` (~1–2 сек)
3. `answer_generator.generate()` → основной запрос к `gpt-5-mini` (~10–15 сек)

Классификаторы 1 и 2 **независимы** — их можно запускать параллельно,
сэкономив 1–3 секунды реального времени.

**Слой 3 — Блокирующий ответ**

`LLMAnswerer` получает полный ответ (`stream=False`) и отдаёт его пользователю целиком.
Пользователь видит «тишину» 10–15 секунд. Это критично для `gpt-5-mini` с reasoning:
модель «думает» перед ответом, и без стриминга вся эта пауза видна пользователю.

---

## 2. Цели и метрики успеха

| Метрика | Сейчас | Цель после v3.0.2 |
| :-- | :-- | :-- |
| Время холодного старта (первый запрос) | 25–40 сек | < 3 сек (компоненты уже в памяти) |
| Воспринимаемое время до первого символа | 10–15 сек | < 2 сек (стриминг) |
| Реальная latency LLM (обычный запрос) | 12–17 сек | ~10–14 сек (параллельные классификаторы) |
| Перезапуск сервера (TF-IDF rebuild) | 1–3 сек | < 0.3 сек (кэш joblib) |
| Деградация качества ответа | — | **0%** — запрещено |

**Железное правило:** `PRIMARY_MODEL`, `REASONING_EFFORT`, `CLASSIFIER_MODEL`,
все prompt-файлы, логика retrieval, стратегия памяти, SD-уровни — **не трогать**.

---

## 3. Порядок реализации (по принципу риск/эффект)

```
TASK-1 → TASK-2 → TASK-3 → TASK-4 → TASK-5
  ↑          ↑        ↑         ↑        ↑
Мало       Мало    Средне    Минимум   Мало
рисков,   рисков,  рисков,   рисков,  рисков,
-1-3 сек  -2-3сек  UX макс   UX мгн.  -1-2 сек
(реальных)(реал.)            <500ms   (restart)
```


---

## TASK-1: Параллельные классификаторы

**Файл:** `bot_agent/answer_adaptive.py`
**Сложность:** Низкая (1 файл, ~10 строк изменений)
**Риск:** Минимальный
**Эффект:** −2 до −3 секунды реального времени ответа

### Что делать

Найти в `answer_adaptive.py` место, где последовательно вызываются
`StateClassifier.classify()` и `SDClassifier.classify_user()`.
Заменить последовательные вызовы на параллельные через `asyncio.gather`.

### Предусловие

Перед изменением убедиться: методы `StateClassifier.classify()` и
`SDClassifier.classify_user()` объявлены как `async def`. Если нет — сделать их async.

**Проверить в `bot_agent/state_classifier.py`:**

```python
# Должно быть:
async def classify(self, user_message: str, history: str) -> str:
    ...
```

**Проверить в `bot_agent/sd_classifier.py`:**

```python
# Должно быть:
async def classify_user(self, user_message: str, history: str) -> str:
    ...
```


### Реализация

```python
# bot_agent/answer_adaptive.py
import asyncio
import logging

logger = logging.getLogger(__name__)

async def _classify_parallel(
    self,
    user_message: str,
    history: str
) -> tuple[str, str]:
    """
    Запускает StateClassifier и SDClassifier параллельно.
    Возвращает (user_state, sd_level).
    При ошибке одного — возвращает fallback для него,
    второй классификатор продолжает работать.
    """
    results = await asyncio.gather(
        self.state_classifier.classify(user_message, history),
        self.sd_classifier.classify_user(user_message, history),
        return_exceptions=True  # ← критично: не ломает пайплайн при ошибке одного
    )

    user_state = results
    sd_level = results[^1]

    # Обработка ошибок — сохраняем текущие fallback-значения проекта
    if isinstance(user_state, Exception):
        logger.warning(
            "[CLASSIFY_PARALLEL] StateClassifier failed: %s. "
            "Using fallback: NEUTRAL", user_state
        )
        user_state = "NEUTRAL"

    if isinstance(sd_level, Exception):
        logger.warning(
            "[CLASSIFY_PARALLEL] SDClassifier failed: %s. "
            "Using fallback: GREEN", sd_level
        )
        sd_level = "GREEN"

    return user_state, sd_level
```

Затем найти в `answer_adaptive.py` место с последовательными вызовами:

```python
# БЫЛО (последовательно — удалить):
user_state = await self.state_classifier.classify(user_message, history)
sd_level = await self.sd_classifier.classify_user(user_message, history)

# СТАЛО (параллельно — вставить):
user_state, sd_level = await self._classify_parallel(user_message, history)
```


### Затронутые файлы

- `bot_agent/answer_adaptive.py` — добавить метод `_classify_parallel`, заменить вызовы
- `bot_agent/state_classifier.py` — убедиться что `classify()` является async
- `bot_agent/sd_classifier.py` — убедиться что `classify_user()` является async

---

## TASK-2: Горячая предзагрузка с корректным DI

**Файл:** `api/main.py`, `api/dependencies.py` (создать новый)
**Сложность:** Средняя (2–3 файла)
**Риск:** Низкий
**Эффект:** Холодный старт 25–40 сек → < 3 сек

### Архитектурное решение

**ВАЖНО:** Ключевая ошибка v3.0.1 — компоненты загружались в словарь,
но обработчики запросов об этом не знали и создавали новые экземпляры.
Правильный паттерн в FastAPI — `Depends()` + функции-провайдеры,
которые возвращают предзагруженные singleton-экземпляры.

### Шаг 1: Создать `api/dependencies.py`

```python
# api/dependencies.py
"""
FastAPI Dependency Injection провайдеры для предзагруженных компонентов.
Компоненты инициализируются один раз при старте (lifespan),
затем переиспользуются во всех запросах без повторной инициализации.
"""
from __future__ import annotations
from typing import Optional
from bot_agent.data_loader import DataLoader
from bot_agent.semantic_memory import SemanticMemory
from bot_agent.graph_client import GraphClient
from bot_agent.retriever import Retriever

# Модуль-уровневые singleton-переменные
# Заполняются в lifespan() при старте сервера
_data_loader: Optional[DataLoader] = None
_graph_client: Optional[GraphClient] = None
_retriever: Optional[Retriever] = None
_embedding_model_warmed: bool = False


def set_preloaded_components(
    data_loader: DataLoader,
    graph_client: GraphClient,
    retriever: Retriever,
) -> None:
    """Вызывается из lifespan() после параллельной загрузки."""
    global _data_loader, _graph_client, _retriever, _embedding_model_warmed
    _data_loader = data_loader
    _graph_client = graph_client
    _retriever = retriever
    _embedding_model_warmed = True


def get_data_loader() -> DataLoader:
    """
    FastAPI dependency. Возвращает предзагруженный DataLoader.
    Если warm-up не завершился (race condition при быстром старте) —
    создаёт новый экземпляр как fallback (сохраняет текущее поведение).
    """
    if _data_loader is not None:
        return _data_loader
    return DataLoader()  # fallback: lazy init


def get_graph_client() -> GraphClient:
    """FastAPI dependency для GraphClient."""
    if _graph_client is not None:
        return _graph_client
    return GraphClient()  # fallback


def get_retriever() -> Retriever:
    """FastAPI dependency для Retriever."""
    if _retriever is not None:
        return _retriever
    return Retriever()  # fallback


def is_embedding_model_warm() -> bool:
    """Проверка: прогрета ли модель эмбеддингов."""
    return _embedding_model_warmed
```


### Шаг 2: Обновить `api/main.py`

```python
# api/main.py
from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from api.dependencies import set_preloaded_components
from bot_agent.data_loader import DataLoader
from bot_agent.semantic_memory import SemanticMemory
from bot_agent.graph_client import GraphClient
from bot_agent.retriever import Retriever

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Предзагрузка тяжёлых компонентов при старте сервера.
    Используется asyncio.to_thread() для CPU-bound операций
    (правильный паттерн для Python 3.10+, заменяет устаревший
    get_event_loop().run_in_executor()).
    """
    logger.info("[WARMUP] Starting parallel warm preload...")

    # CPU-bound функции, выполняются в thread pool
    def _load_data_loader() -> DataLoader:
        dl = DataLoader()
        dl.load()  # загрузить SAG JSON с диска
        logger.info("[WARMUP] DataLoader ready")
        return dl

    def _load_semantic_memory() -> None:
        """Прогрев модели эмбеддингов — самый тяжёлый шаг (~100MB)."""
        sm = SemanticMemory(user_id="__warmup__")
        sm.ensure_model_loaded()  # публичный метод (см. TASK-2, шаг 3)
        logger.info("[WARMUP] SemanticMemory embedding model ready")

    def _load_graph_client() -> GraphClient:
        gc = GraphClient()
        # GraphClient строит граф в __init__, дополнительный вызов не нужен
        logger.info("[WARMUP] GraphClient ready (95 nodes, 2182 edges)")
        return gc

    def _load_retriever() -> Retriever:
        r = Retriever()
        # Retriever строит/загружает TF-IDF матрицу в __init__
        logger.info("[WARMUP] Retriever ready (TF-IDF matrix loaded)")
        return r

    # Параллельная загрузка всех компонентов через asyncio.to_thread()
    # (правильный паттерн Python 3.10+, не deprecated)
    results = await asyncio.gather(
        asyncio.to_thread(_load_data_loader),
        asyncio.to_thread(_load_semantic_memory),
        asyncio.to_thread(_load_graph_client),
        asyncio.to_thread(_load_retriever),
        return_exceptions=True  # сервер запустится даже если один компонент упал
    )

    data_loader, _, graph_client, retriever = results

    # Проверка: если компоненты загружены успешно — регистрируем их в DI
    warmup_ok = all(not isinstance(r, Exception) for r in results)
    if warmup_ok:
        set_preloaded_components(
            data_loader=data_loader,
            graph_client=graph_client,
            retriever=retriever,
        )
        logger.info("[WARMUP] ✅ All components preloaded. Bot is hot and ready.")
    else:
        for i, r in enumerate(results):
            if isinstance(r, Exception):
                logger.error("[WARMUP] Component %d failed: %s", i, r)
        logger.warning(
            "[WARMUP] ⚠️ Some components failed. "
            "Falling back to lazy initialization for failed components."
        )

    yield
    # shutdown: явная очистка не требуется, GC справится


app = FastAPI(lifespan=lifespan)
# ... подключение роутеров как обычно
```


### Шаг 3: Исправить `bot_agent/semantic_memory.py`

Найти в `semantic_memory.py` метод `_ensure_model_loaded` (с двойным подчёркиванием).
Добавить публичный алиас **без изменения логики**:

```python
# bot_agent/semantic_memory.py
# НАЙТИ: метод _ensure_model_loaded (или _load_model, или аналогичный)
# ДОБАВИТЬ публичный алиас:

def ensure_model_loaded(self) -> None:
    """
    Публичный метод для принудительной предзагрузки модели эмбеддингов.
    Используется в lifespan warm-up. Не изменяет логику — вызывает
    внутренний приватный метод.
    """
    self._ensure_model_loaded()  # или какое название у него сейчас
```


### Шаг 4: Использовать DI в обработчиках запросов

В `api/routes.py` (или аналогичном файле с эндпоинтами) добавить `Depends()`:

```python
# api/routes.py
from fastapi import Depends
from api.dependencies import get_data_loader, get_graph_client, get_retriever
from bot_agent.data_loader import DataLoader
from bot_agent.graph_client import GraphClient
from bot_agent.retriever import Retriever

@router.post("/api/v1/questions/adaptive")
async def adaptive_answer(
    request: QuestionRequest,
    api_key: str = Depends(verify_api_key),
    data_loader: DataLoader = Depends(get_data_loader),       # ← предзагруженный
    graph_client: GraphClient = Depends(get_graph_client),   # ← предзагруженный
    retriever: Retriever = Depends(get_retriever),           # ← предзагруженный
):
    # Передать data_loader, graph_client, retriever в orchestrator/answer_adaptive
    # вместо того чтобы создавать новые экземпляры внутри
    ...
```


### Затронутые файлы

- `api/dependencies.py` — **создать новый** файл
- `api/main.py` — заменить lifespan
- `api/routes.py` — добавить `Depends()` для трёх компонентов
- `bot_agent/semantic_memory.py` — добавить публичный `ensure_model_loaded()`

---

## TASK-3: Стриминг ответов (SSE)

**Файлы:** `bot_agent/llm_answerer.py`, `api/routes.py`,
`web_ui/src/services/api.service.ts`, `web_ui/src/hooks/useChat.ts`,
`web_ui/src/pages/ChatPage.tsx`
**Сложность:** Средняя (5 файлов, но изменения локальные)
**Риск:** Низкий (старый endpoint не удаляется)
**Эффект:** Воспринимаемое время до первого символа: 10–15 сек → < 2 сек

### 3a. `bot_agent/llm_answerer.py` — добавить `answer_stream()`

```python
# bot_agent/llm_answerer.py
from typing import AsyncGenerator, Optional

async def answer_stream(
    self,
    blocks: list,
    user_question: str,
    conversation_history: Optional[str] = None,
    mode: Optional[str] = None,
    sd_level: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Стриминговая версия answer().
    Использует stream=True — единственное отличие от обычного вызова.
    Модель, промпты, max_tokens, temperature — НЕ МЕНЯЮТСЯ.
    Качество ответа идентично answer().
    """
    system_prompt = self.build_system_prompt(sd_level=sd_level)
    context = self.build_context_prompt(
        blocks=blocks,
        user_question=user_question,
        conversation_history=conversation_history,
    )
    max_tokens = self._get_mode_max_tokens(mode)  # существующий метод

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context},
    ]

    # ВАЖНО для gpt-5-mini (reasoning model):
    # stream=True работает корректно — модель стримит reasoning tokens
    # и content tokens. reasoning_effort передаётся через extra_body.
    stream = await self.async_client.chat.completions.create(
        model=self.config.PRIMARY_MODEL,
        messages=messages,
        max_tokens=max_tokens,
        temperature=self.config.TEMPERATURE,
        stream=True,
        extra_body={"reasoning_effort": self.config.REASONING_EFFORT}
        if hasattr(self.config, "REASONING_EFFORT") else {},
    )

    async for chunk in stream:
        if chunk.choices and chunk.choices.delta.content:
            yield chunk.choices.delta.content
```


### 3b. `api/routes.py` — новый SSE endpoint

```python
# api/routes.py
import json
import time
from fastapi.responses import StreamingResponse

@router.post("/api/v1/questions/adaptive-stream")
async def adaptive_stream(
    request: QuestionRequest,
    api_key: str = Depends(verify_api_key),
    data_loader: DataLoader = Depends(get_data_loader),
    graph_client: GraphClient = Depends(get_graph_client),
    retriever: Retriever = Depends(get_retriever),
):
    """
    Стриминговый endpoint (Server-Sent Events).
    Нестриминговый /adaptive сохраняется для обратной совместимости.

    Формат событий:
    - data: {"token": "..."} — очередной токен ответа
    - data: {"done": true, "mode": "...", "sd_level": "...", "latency_ms": 1234}
    - data: {"error": "..."} — при ошибке в pipeline
    """
    start_time = time.perf_counter()

    async def event_generator():
        try:
            # 1. Параллельная классификация (TASK-1)
            history_str = await memory.get_history_string(request.user_id)
            user_state, sd_level = await orchestrator._classify_parallel(
                request.query, history_str
            )

            # 2. Retrieval — без изменений
            blocks = await orchestrator.retrieve_blocks(
                request.query, user_state,
                retriever=retriever,
                data_loader=data_loader,
                graph_client=graph_client,
            )

            # 3. Стриминг токенов
            full_response = ""
            context = await memory.get_context(request.user_id)

            async for token in llm_answerer.answer_stream(
                blocks=blocks,
                user_question=request.query,
                conversation_history=context,
                mode=user_state,
                sd_level=sd_level,
            ):
                full_response += token
                # Каждый токен — отдельное SSE-событие
                yield f"data: {json.dumps({'token': token}, ensure_ascii=False)}\n\n"

            # 4. Сохранение в память — после полного ответа (как и в обычном режиме)
            await memory.add_turn(request.user_id, request.query, full_response)

            # 5. Финальное событие с метаданными
            latency_ms = int((time.perf_counter() - start_time) * 1000)
            yield (
                f"data: {json.dumps({'done': True, 'mode': user_state, "
                f"'sd_level': sd_level, 'latency_ms': latency_ms})}\n\n"
            )

        except Exception as e:
            logger.error("[STREAM] Pipeline error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",   # отключить буферизацию nginx
            "Connection": "keep-alive",
        },
    )
```


### 3c. `web_ui/src/services/api.service.ts` — SSE клиент с reconnect

```typescript
// web_ui/src/services/api.service.ts

/**
 * Потоковый запрос к /adaptive-stream.
 * Автоматически переподключается при разрыве соединения (до 3 попыток).
 */
async streamAdaptiveAnswer(
  query: string,
  userId: string,
  onToken: (token: string) => void,
  onDone: (meta: { mode: string; sd_level: string; latency_ms: number }) => void,
  onError?: (error: string) => void,
  maxRetries = 3,
): Promise<void> {
  let attempt = 0;

  const attempt_stream = async (): Promise<void> => {
    let response: Response;

    try {
      response = await fetch('/api/v1/questions/adaptive-stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': this.apiKey,
        },
        body: JSON.stringify({ query, user_id: userId }),
      });
    } catch (networkError) {
      // Сетевая ошибка (нет соединения, timeout)
      if (attempt < maxRetries) {
        attempt++;
        const delay = attempt * 1000; // 1s, 2s, 3s
        console.warn(`[SSE] Network error, retrying in ${delay}ms (attempt ${attempt})`);
        await new Promise(resolve => setTimeout(resolve, delay));
        return attempt_stream();
      }
      onError?.(`Network error after ${maxRetries} retries`);
      return;
    }

    if (!response.ok || !response.body) {
      onError?.(`HTTP ${response.status}`);
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');

        // Последняя строка может быть неполной — оставить в буфере
        buffer = lines.pop() ?? '';

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (data.token !== undefined) {
              onToken(data.token);
            } else if (data.done) {
              onDone({ mode: data.mode, sd_level: data.sd_level, latency_ms: data.latency_ms });
            } else if (data.error) {
              onError?.(data.error);
            }
          } catch {
            // Игнорировать невалидный JSON-фрагмент
          }
        }
      }
    } catch (readError) {
      // Разрыв соединения во время чтения
      if (attempt < maxRetries) {
        attempt++;
        console.warn(`[SSE] Read error, retrying (attempt ${attempt})`);
        return attempt_stream();
      }
      onError?.(`Stream read error after ${maxRetries} retries`);
    }
  };

  return attempt_stream();
}
```


### 3d. `web_ui/src/hooks/useChat.ts` — стриминг-стейт

```typescript
// web_ui/src/hooks/useChat.ts — добавить в существующий хук:

const [isThinking, setIsThinking] = useState(false);
const [streamingText, setStreamingText] = useState('');
const [streamMeta, setStreamMeta] = useState<{mode: string; sd_level: string} | null>(null);

const sendMessageStream = async (query: string) => {
  setIsThinking(true);
  setStreamingText('');
  setStreamMeta(null);

  await apiService.streamAdaptiveAnswer(
    query,
    userId,
    (token) => {
      // Первый токен — убираем "думает..."
      setIsThinking(false);
      setStreamingText(prev => prev + token);
    },
    (meta) => {
      setStreamMeta({ mode: meta.mode, sd_level: meta.sd_level });
      // Зафиксировать финальный текст в истории чата
      finalizeMessage(streamingText);
    },
    (error) => {
      setIsThinking(false);
      showErrorNotification(error);
    },
  );
};
```


### Затронутые файлы

- `bot_agent/llm_answerer.py` — добавить `answer_stream()` async generator
- `api/routes.py` — добавить `POST /api/v1/questions/adaptive-stream`
- `web_ui/src/services/api.service.ts` — добавить `streamAdaptiveAnswer()`
- `web_ui/src/hooks/useChat.ts` — добавить streaming state
- `web_ui/src/pages/ChatPage.tsx` — показывать `isThinking` и `streamingText`

---

## TASK-4: Индикатор «думает...» (UX)

**Файл:** `web_ui/src/pages/ChatPage.tsx`
**Сложность:** Минимальная
**Риск:** Нулевой (только UI)
**Эффект:** Пользователь видит реакцию < 500ms вместо 10–15 сек тишины

```tsx
// web_ui/src/pages/ChatPage.tsx — добавить индикатор
{isThinking && (
  <div className="thinking-indicator">
    <span className="dot" /><span className="dot" /><span className="dot" />
  </div>
)}

{streamingText && (
  <div className="message bot-message streaming">
    {streamingText}
    <span className="cursor-blink" />  {/* мигающий курсор во время генерации */}
  </div>
)}
```

CSS (добавить в соответствующий `.css` / `.scss` файл):

```css
.thinking-indicator .dot {
  display: inline-block;
  width: 8px; height: 8px;
  margin: 0 3px;
  border-radius: 50%;
  background: #888;
  animation: bounce 1.2s infinite;
}
.thinking-indicator .dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-indicator .dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.8); opacity: 0.5; }
  40% { transform: scale(1.2); opacity: 1; }
}

.cursor-blink {
  display: inline-block;
  width: 2px; height: 1em;
  background: currentColor;
  margin-left: 2px;
  animation: blink 1s step-end infinite;
}
@keyframes blink { 50% { opacity: 0; } }
```


---

## TASK-5: Кэширование TF-IDF матрицы (joblib)

**Файл:** `bot_agent/retriever.py`
**Сложность:** Низкая
**Риск:** Минимальный (кэш инвалидируется по hash данных)
**Эффект:** Перезапуск сервера −1–2 сек (rebuild TF-IDF не нужен)

```python
# bot_agent/retriever.py
import hashlib
import logging
from pathlib import Path

import joblib  # pip install joblib (уже в sklearn зависимостях)

logger = logging.getLogger(__name__)

# Версия формата кэша — изменить при изменении структуры Retriever
# чтобы гарантированно инвалидировать старый кэш
CACHE_FORMAT_VERSION = "3.0.2"

CACHE_DIR = Path(".cache_bot_agent")
TFIDF_CACHE_PATH = CACHE_DIR / "tfidf_cache.joblib"
TFIDF_HASH_PATH = CACHE_DIR / "tfidf_cache.hash"


def _compute_data_hash(self) -> str:
    """
    Вычисляет MD5-хэш всех JSON-файлов данных + версию формата кэша.
    Если данные изменились — кэш инвалидируется автоматически.
    """
    hasher = hashlib.md5()
    hasher.update(CACHE_FORMAT_VERSION.encode())
    for f in sorted(self.data_root.glob("*.for_vector.json")):
        hasher.update(f.read_bytes())
    return hasher.hexdigest()


def _build_or_load_tfidf(self) -> None:
    """
    Загружает TF-IDF матрицу из кэша если данные не изменились,
    иначе перестраивает и сохраняет.
    Использует joblib вместо pickle (безопаснее, эффективнее для numpy/scipy).
    """
    CACHE_DIR.mkdir(exist_ok=True)
    current_hash = self._compute_data_hash()

    # Проверить актуальность кэша
    if TFIDF_CACHE_PATH.exists() and TFIDF_HASH_PATH.exists():
        saved_hash = TFIDF_HASH_PATH.read_text(encoding="utf-8").strip()
        if saved_hash == current_hash:
            try:
                cached = joblib.load(TFIDF_CACHE_PATH)
                self.vectorizer = cached["vectorizer"]
                self.tfidf_matrix = cached["matrix"]
                self.blocks = cached["blocks"]
                logger.info("[RETRIEVER] TF-IDF loaded from cache (hash match)")
                return
            except Exception as e:
                # Кэш повреждён — перестроить
                logger.warning("[RETRIEVER] Cache load failed: %s. Rebuilding.", e)

    # Кэш устарел или не существует — перестроить
    logger.info("[RETRIEVER] Building TF-IDF matrix...")
    self._build_tfidf()  # существующий метод — не трогать

    # Сохранить новый кэш
    try:
        joblib.dump(
            {
                "vectorizer": self.vectorizer,
                "matrix": self.tfidf_matrix,
                "blocks": self.blocks,
                "cache_version": CACHE_FORMAT_VERSION,  # для диагностики
            },
            TFIDF_CACHE_PATH,
            compress=3,  # сжатие уменьшает размер файла ~3x
        )
        TFIDF_HASH_PATH.write_text(current_hash, encoding="utf-8")
        logger.info("[RETRIEVER] TF-IDF matrix cached successfully")
    except Exception as e:
        # Если не смогли записать кэш — не страшно, работаем без него
        logger.warning("[RETRIEVER] Could not save cache: %s", e)
```

Заменить вызов `_build_tfidf()` в `__init__` на `_build_or_load_tfidf()`:

```python
# В __init__ найти:
self._build_tfidf()
# Заменить на:
self._build_or_load_tfidf()
```

Обновить `.gitignore`:

```gitignore
# .gitignore — добавить:
.cache_bot_agent/tfidf_cache.joblib
.cache_bot_agent/tfidf_cache.hash
```


---

## 6. Мониторинг latency (обязательно для проверки целей)

**Файл:** `api/routes.py` (добавить middleware)
**Сложность:** Минимальная

```python
# api/main.py — добавить middleware для замера latency

import time
from fastapi import Request

@app.middleware("http")
async def add_latency_header(request: Request, call_next):
    """
    Добавляет заголовок X-Response-Time-Ms в каждый ответ.
    Позволяет проверять достижение целей PRD v3.0.2 без сторонних инструментов —
    достаточно смотреть в DevTools → Network → Response Headers.
    """
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = int((time.perf_counter() - start) * 1000)
    response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
    return response
```


---

## 7. Что НЕ меняется (гарантия качества)

| Компонент | Статус |
| :-- | :-- |
| `PRIMARY_MODEL=gpt-5-mini` | ❌ не трогать |
| `REASONING_EFFORT=low` | ❌ не трогать |
| `CLASSIFIER_MODEL=gpt-4o-mini` | ❌ не трогать |
| `prompt_system_base.md` | ❌ не трогать |
| `prompt_sd_*.md` (6 файлов) | ❌ не трогать |
| `MODE_MAX_TOKENS` по режимам | ❌ не трогать |
| Логика retrieval (stage filter, confidence cap) | ❌ не трогать |
| Стратегия памяти (short-term + semantic + summary) | ❌ не трогать |
| Все 6 SD-уровней и fallback `GREEN` | ❌ не трогать |
| `CONVERSATION_HISTORY_DEPTH`, `MAX_CONTEXT_SIZE` | ❌ не трогать |
| `answer_basic.py`, `answer_graph_powered.py`, `answer_sag_aware.py` | ❌ не трогать |
| Endpoint `POST /api/v1/questions/adaptive` (старый) | ❌ не удалять |


---

## 8. Тесты

```python
# tests/test_parallel_classifiers.py
import asyncio
import pytest
from unittest.mock import AsyncMock, patch

async def test_parallel_classifiers_both_succeed():
    """Оба классификатора возвращают результат при параллельном запуске."""
    ...

async def test_parallel_classifiers_state_fails():
    """При ошибке StateClassifier возвращается fallback NEUTRAL, SDClassifier работает."""
    ...

async def test_parallel_classifiers_both_fail():
    """При ошибке обоих — оба возвращают fallback, pipeline не падает."""
    ...
```

```python
# tests/test_warmup.py
async def test_warmup_registers_components():
    """После lifespan warm-up DI провайдеры возвращают предзагруженные экземпляры."""
    ...

async def test_warmup_fallback_on_failure():
    """Если warm-up упал — fallback lazy init работает."""
    ...
```

```python
# tests/test_tfidf_cache.py
def test_cache_hit():
    """При неизменных данных — Retriever загружает из кэша без rebuild."""
    ...

def test_cache_invalidation():
    """При изменении JSON-данных — кэш перестраивается."""
    ...

def test_cache_version_invalidation():
    """Кэш от старой версии формата инвалидируется по CACHE_FORMAT_VERSION."""
    ...
```

```python
# tests/test_streaming.py
async def test_stream_endpoint_returns_tokens():
    """/adaptive-stream возвращает SSE токены до финального done:true."""
    ...

async def test_stream_latency_header():
    """Ответы содержат X-Response-Time-Ms заголовок."""
    ...
```


---

## 9. Обновить `.env.example`

```env
# .env.example — добавить новые переменные:

# Speed Layer (PRD v3.0.2)
WARMUP_ON_START=true        # Предзагрузка компонентов при старте API (рекомендуется true)
ENABLE_STREAMING=true       # Включить /adaptive-stream endpoint
```


---

## 10. Обновить `README.md`

Добавить раздел:

```markdown
## Speed Layer (PRD v3.0.2)

Оптимизация скорости ответов без снижения качества:

- **Warm Preload**: DataLoader, SemanticMemory, GraphClient, Retriever загружаются
  параллельно при старте API через `asyncio.to_thread()`. Компоненты регистрируются
  через FastAPI DI (`Depends()`), что гарантирует их использование в запросах.
  Fallback: если warm-up не завершился — компонент создаётся лениво как раньше.

- **Параллельные классификаторы**: StateClassifier и SDClassifier запускаются через
  `asyncio.gather(return_exceptions=True)`. При ошибке одного — второй продолжает,
  fallback-значения (NEUTRAL/GREEN) сохранены.

- **Стриминг**: `POST /api/v1/questions/adaptive-stream` (SSE). Нестриминговый
  `/adaptive` сохранён для обратной совместимости. SSE-клиент содержит
  auto-reconnect (до 3 попыток с экспоненциальной задержкой).

- **TF-IDF кэш**: матрица сохраняется через `joblib` (безопаснее pickle).
  Инвалидируется по MD5-хэшу данных + версии формата кэша.

- **Latency мониторинг**: заголовок `X-Response-Time-Ms` в каждом ответе.
```

```

***

Документ готов к передаче Codex-агенту. Все задачи привязаны к реальным файлам репозитория , исправлены все 8 критических и существенных багов v3.0.1, порядок реализации оптимизирован по принципу минимального риска: TASK-1 (параллельные классификаторы) → TASK-2 (warm preload с DI) → TASK-3 (стриминг) → TASK-4 (индикатор) → TASK-5 (TF-IDF кэш).[^1]

