
## Микро-ПРД: Подключить `bot_psychologist` к `Bot_data_base` через HTTP API

**Цель:** `data_loader.py` должен получать блоки через `db_api_client.py` вместо прямого чтения JSON с диска.

***

### Контекст

В репозитории [Askhat-cmd/Text_transcription](https://github.com/Askhat-cmd/Text_transcription) в папке `bot_psychologist/bot_agent/` уже есть файл [`db_api_client.py`](https://github.com/Askhat-cmd/Text_transcription/blob/568f4c554c331eaab62db016521dc96c5930fa1f/bot_psychologist/bot_agent/db_api_client.py) — HTTP-клиент к сервису `Bot_data_base`. Но [`data_loader.py`](https://github.com/Askhat-cmd/Text_transcription/blob/568f4c554c331eaab62db016521dc96c5930fa1f/bot_psychologist/bot_agent/data_loader.py) его не использует — читает `all_blocks_merged.json` напрямую с диска.

***

### Задача агенту

**1. Открой файл** `bot_psychologist/bot_agent/data_loader.py`

**2. Найди** блок, где задаётся `KNOWLEDGE_SOURCE` и где происходит загрузка из `chromadb` (строки с `all_blocks_merged.json`)

**3. Добавь новый режим** `KNOWLEDGE_SOURCE=api` в `data_loader.py`:

- Если `KNOWLEDGE_SOURCE == "api"` → вызывать `db_api_client.py` для получения блоков
- Если `KNOWLEDGE_SOURCE == "chromadb"` → оставить текущую логику (не ломать)

**4. Открой файл** `bot_psychologist/bot_agent/db_api_client.py`

- Убедись что там есть метод для поиска блоков по запросу
- Если метода `search(query, top_k)` нет — добавь его: `POST http://127.0.0.1:8003/api/query/` с телом `{"query": query, "top_k": top_k}`

**5. Открой** `bot_psychologist/.env.example`

- Добавь строку: `KNOWLEDGE_SOURCE=api` с комментарием `# "chromadb" = local file, "api" = Bot_data_base HTTP`

**6. В `retriever.py`** — убедись что при `source=api` вызов идёт через `db_api_client`, а не через `chroma_loader`

***

### Критерии готовности

- [ ] `KNOWLEDGE_SOURCE=api` в `.env` переключает бота на HTTP-режим
- [ ] `KNOWLEDGE_SOURCE=chromadb` оставляет текущее поведение без изменений (обратная совместимость)
- [ ] В логах при старте появляется: `KNOWLEDGE_SOURCE=api` и `DB API url=http://127.0.0.1:8003`
- [ ] Если `Bot_data_base` недоступен — бот логирует WARNING и падает с понятным сообщением, не молча

***

### Файлы для изменения

| Файл | Действие |
| :-- | :-- |
| `bot_agent/data_loader.py` | Добавить ветку `if source == "api"` |
| `bot_agent/db_api_client.py` | Проверить/добавить метод `search(query, top_k)` |
| `.env.example` | Добавить `KNOWLEDGE_SOURCE=api` |

**Файлы НЕ трогать:** `chroma_loader.py`, `retrieval/voyagereranker.py`, `answer_adaptive.py`

