# 📋 Детальное ТЗ для Phase 1: Семантический QA по лекциям

## Часть 1: Обзор и входные данные

### 1.1 Что такое Phase 1?

**Цель:** Создать **базовый QA-бот**, который:

- Принимает вопрос пользователя на русском.
- Находит релевантные блоки из лекций.
- Формирует ответ через LLM, опираясь на найденные блоки.
- Возвращает ответ с ссылками на видео и таймкоды.

**Результат:** Python-модуль, который можно вызвать как:

```python
result = answer_question_basic("Как работает осознавание?")
# Вернет:
# {
#   "answer": "Осознавание — это...",
#   "sources": [
#     {"block_id": "...", "title": "...", "youtube_link": "..."},
#     ...
#   ]
# }
```


***

### 1.2 Входные данные (из voice_bot_pipeline)

Предполагаем, что у нас есть набор обработанных лекций:

```
data/sag_final/2024/03/
├── 2024-03-15_HndVzdJuAz0_Процесс_исцеления.for_vector.json
├── 2024-03-20_WQnmT1vqFUs_Работа_с_паттернами.for_vector.json
└── ...

data/sag_final/2024/04/
├── 2024-04-10_Rxoj94WQpsQ_Трансформация_сознания.for_vector.json
└── ...
```

**Каждый `.for_vector.json` содержит:**

```json
{
  "document_title": "Лекция Сарсекенова: Rxoj94WQpsQ",
  "document_metadata": {
    "video_id": "Rxoj94WQpsQ",
    "source_url": "https://youtube.com/watch?v=Rxoj94WQpsQ",
    "total_blocks": 6
  },
  "blocks": [
    {
      "block_id": "Rxoj94WQpsQ_001",
      "video_id": "Rxoj94WQpsQ",
      "start": "00:00:00",
      "end": "00:08:45",
      "youtube_link": "https://youtube.com/watch?v=Rxoj94WQpsQ&t=0s",
      "title": "Процесс исцеления через самопознание",
      "summary": "Обсуждается важность подлинного исцеления...",
      "keywords": ["исцеление", "самопознание", "осознавание"],
      "content": "Прямо сейчас уникальный момент исцеления..."
    },
    ...
  ]
}
```


***

## Часть 2: Архитектура Phase 1

### 2.1 Компоненты

```
┌─────────────────────────────────────────┐
│         Пользователь (запрос)           │
└──────────────────┬──────────────────────┘
                   │
        ┌──────────▼──────────┐
        │  QUERY NORMALIZER   │  (опционально)
        └──────────┬──────────┘
                   │
        ┌──────────▼──────────────────┐
        │  DATA LOADER (кэш)          │
        │  ├─ загрузить все JSON      │
        │  ├─ индексировать блоки     │
        └──────────┬──────────────────┘
                   │
        ┌──────────▼──────────────────┐
        │  RETRIEVER (поиск)          │
        │  ├─ BM25 / простой поиск    │
        │  ├─ или ChromaDB (если есть)│
        └──────────┬──────────────────┘
                   │
        ┌──────────▼──────────────────┐
        │  LLM ANSWER GENERATOR       │
        │  (OpenAI API + промпт)      │
        └──────────┬──────────────────┘
                   │
        ┌──────────▼──────────────────┐
        │  RESPONSE FORMATTER         │
        │  ├─ структурированный JSON  │
        │  ├─ ссылки на видео         │
        └──────────┬──────────────────┘
                   │
        ┌──────────▼──────────────────┐
        │  Итоговый результат         │
        └─────────────────────────────┘
```


***

### 2.2 Модули (файлы)

Создаем в репозитории следующую структуру:

```
voice_bot_pipeline/bot_agent/
├── __init__.py
├── config.py                      # пути, параметры
├── data_loader.py                 # загрузка и кэширование JSON
├── retriever.py                   # поиск релевантных блоков
├── llm_answerer.py                # формирование ответа через LLM
└── answer_basic.py                # главная функция Phase 1
```


***

## Часть 3: Подробная спецификация каждого модуля

### 3.1 `config.py`

**Назначение:** Централизованное управление всеми параметрами.

**Содержимое:**

```python
# bot_agent/config.py

import os
from pathlib import Path
from typing import Optional

class Config:
    """Конфигурация для Phase 1 QA-бота"""
    
    # === Пути к данным (из voice_bot_pipeline) ===
    DATA_ROOT = Path(os.getenv("DATA_ROOT", "data"))
    SAG_FINAL_DIR = DATA_ROOT / "sag_final"  # где лежат обработанные JSON
    
    # === Параметры поиска ===
    TOP_K_BLOCKS = 5  # сколько релевантных блоков брать (настраивается)
    MIN_RELEVANCE_SCORE = 0.3  # минимальный порог релевантности (0-1)
    
    # === LLM параметры ===
    LLM_MODEL = os.getenv("PRIMARY_MODEL", "gpt-4o-mini")
    LLM_TEMPERATURE = 0.7  # 0-1, для стабильности ответов
    LLM_MAX_TOKENS = 1500  # максимальная длина ответа
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    
    # === Язык ===
    RESPONSE_LANGUAGE = "russian"
    
    # === Кэширование ===
    ENABLE_CACHING = True
    CACHE_DIR = Path(".cache_bot_agent")
    
    # === Отладка ===
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"


# Инстанс конфига (синглтон)
config = Config()
```

**Ключевые моменты:**

- Все "магические" значения — в конфиге.
- Агенту Cursor будет просто менять значения.
- Пути относительные (от корня репозитория).

***

### 3.2 `data_loader.py`

**Назначение:** Загрузить все JSON-файлы из `sag_final/` и предоставить удобный доступ.

**Содержимое:**

```python
# bot_agent/data_loader.py

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime

from config import config

logger = logging.getLogger(__name__)


@dataclass
class Block:
    """Представление одного блока лекции"""
    block_id: str
    video_id: str
    start: str
    end: str
    title: str
    summary: str
    content: str
    keywords: List[str]
    youtube_link: str
    document_title: str  # из какой лекции
    
    def get_preview(self, max_len: int = 200) -> str:
        """Вернуть краткое содержание"""
        return self.content[:max_len] + "..." if len(self.content) > max_len else self.content


@dataclass
class Document:
    """Представление одной лекции"""
    video_id: str
    source_url: str
    title: str
    blocks: List[Block]
    metadata: Dict  # полные document_metadata из JSON
    
    def get_all_text(self) -> str:
        """Вернуть весь текст документа"""
        return " ".join([b.content for b in self.blocks])


class DataLoader:
    """
    Загружает и кэширует все SAG v2.0 JSON файлы.
    """
    
    def __init__(self):
        self.documents: List[Document] = []
        self.all_blocks: List[Block] = []
        self._video_id_to_doc: Dict[str, Document] = {}
        self._block_id_to_block: Dict[str, Block] = {}
        
        self.loaded_at: Optional[datetime] = None
        self._is_loaded = False
    
    def load_all_data(self) -> None:
        """
        Рекурсивно загрузить все *.for_vector.json из sag_final/
        """
        if self._is_loaded:
            logger.info("✓ Данные уже загружены, используем кэш")
            return
        
        logger.info(f"📂 Начинаю загрузку SAG v2.0 данных из {config.SAG_FINAL_DIR}")
        
        if not config.SAG_FINAL_DIR.exists():
            logger.warning(f"⚠️ Директория не найдена: {config.SAG_FINAL_DIR}")
            return
        
        json_files = list(config.SAG_FINAL_DIR.glob("**/*.for_vector.json"))
        logger.info(f"🔍 Найдено {len(json_files)} файлов")
        
        for json_path in json_files:
            try:
                self._load_single_document(json_path)
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки {json_path}: {e}")
        
        self._is_loaded = True
        self.loaded_at = datetime.now()
        logger.info(f"✅ Загружено: {len(self.documents)} документов, {len(self.all_blocks)} блоков")
    
    def _load_single_document(self, json_path: Path) -> None:
        """Загрузить один JSON файл и парсить его"""
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        document_title = data.get("document_title", "Unknown")
        video_id = data["document_metadata"]["video_id"]
        source_url = data["document_metadata"]["source_url"]
        
        blocks = []
        for block_data in data.get("blocks", []):
            block = Block(
                block_id=block_data["block_id"],
                video_id=block_data["video_id"],
                start=block_data["start"],
                end=block_data["end"],
                title=block_data["title"],
                summary=block_data.get("summary", ""),
                content=block_data["content"],
                keywords=block_data.get("keywords", []),
                youtube_link=block_data["youtube_link"],
                document_title=document_title
            )
            blocks.append(block)
            self._block_id_to_block[block.block_id] = block
            self.all_blocks.append(block)
        
        doc = Document(
            video_id=video_id,
            source_url=source_url,
            title=document_title,
            blocks=blocks,
            metadata=data.get("document_metadata", {})
        )
        
        self.documents.append(doc)
        self._video_id_to_doc[video_id] = doc
        
        logger.debug(f"✓ Загруженo: {document_title} ({len(blocks)} блоков)")
    
    def get_all_blocks(self) -> List[Block]:
        """Вернуть все блоки"""
        if not self._is_loaded:
            self.load_all_data()
        return self.all_blocks
    
    def get_document_by_video_id(self, video_id: str) -> Optional[Document]:
        """Получить документ по video_id"""
        if not self._is_loaded:
            self.load_all_data()
        return self._video_id_to_doc.get(video_id)
    
    def get_block_by_id(self, block_id: str) -> Optional[Block]:
        """Получить блок по block_id"""
        if not self._is_loaded:
            self.load_all_data()
        return self._block_id_to_block.get(block_id)
    
    def get_all_documents(self) -> List[Document]:
        """Вернуть все документы"""
        if not self._is_loaded:
            self.load_all_data()
        return self.documents
    
    def get_blocks_by_video_id(self, video_id: str) -> List[Block]:
        """Вернуть все блоки документа"""
        doc = self.get_document_by_video_id(video_id)
        return doc.blocks if doc else []


# Глобальный инстанс (синглтон)
data_loader = DataLoader()
```

**Ключевые моменты:**

- Загружается ВСЕ при первом вызове, потом кэшируется.
- `Block` и `Document` — dataclasses для удобства.
- Методы поиска: по video_id, block_id, все блоки.
- Логирование на каждом шаге.

***

### 3.3 `retriever.py`

**Назначение:** Найти релевантные блоки по запросу пользователя.

**Содержимое:**

```python
# bot_agent/retriever.py

import logging
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from data_loader import data_loader, Block
from config import config

logger = logging.getLogger(__name__)


class SimpleRetriever:
    """
    Простой retriever на основе TF-IDF + косинусного сходства.
    Используется если нет ChromaDB.
    """
    
    def __init__(self):
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self.blocks: List[Block] = []
        self._is_built = False
    
    def build_index(self) -> None:
        """Построить индекс на основе всех блоков"""
        if self._is_built:
            logger.info("✓ Индекс уже построен")
            return
        
        logger.info("🔨 Строю TF-IDF индекс...")
        self.blocks = data_loader.get_all_blocks()
        
        if not self.blocks:
            logger.warning("⚠️ Нет блоков для индексирования!")
            return
        
        # Объединяем текст для каждого блока: title + keywords + summary
        texts = [
            f"{b.title} {' '.join(b.keywords)} {b.summary}"
            for b in self.blocks
        ]
        
        self.vectorizer = TfidfVectorizer(
            analyzer='char',  # символьный анализ (лучше для русского)
            ngram_range=(2, 3),
            max_features=5000,
            stop_words='russian'
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(texts)
        self._is_built = True
        logger.info(f"✅ Индекс построен для {len(self.blocks)} блоков")
    
    def retrieve(self, query: str, top_k: int = None) -> List[Tuple[Block, float]]:
        """
        Найти top_k релевантных блоков.
        Возвращает список (Block, score).
        """
        if top_k is None:
            top_k = config.TOP_K_BLOCKS
        
        if not self._is_built:
            self.build_index()
        
        if not self.blocks or self.tfidf_matrix is None:
            logger.warning("⚠️ Индекс пуст!")
            return []
        
        # Трансформируем запрос
        query_vec = self.vectorizer.transform([query])
        
        # Считаем косинусное сходство
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        
        # Берем top_k с фильтром по минимальному порогу
        top_indices = np.argsort(-similarities)[:top_k]
        
        results = []
        for idx in top_indices:
            score = float(similarities[idx])
            if score >= config.MIN_RELEVANCE_SCORE:
                results.append((self.blocks[idx], score))
        
        logger.debug(f"🔍 Найдено {len(results)} релевантных блоков для запроса: '{query}'")
        return results


class ChromaDBRetriever:
    """
    Более продвинутый retriever с использованием ChromaDB.
    Используется если ChromaDB уже настроена в пайплайне.
    """
    
    def __init__(self, use_chromadb: bool = False):
        self.use_chromadb = use_chromadb
        self.chroma_client = None
        
        if use_chromadb:
            try:
                import chromadb
                self.chroma_client = chromadb.Client()
                logger.info("✓ ChromaDB инициализирован")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось загрузить ChromaDB: {e}")
                self.use_chromadb = False
    
    def retrieve(self, query: str, top_k: int = None) -> List[Tuple[Block, float]]:
        """
        Поиск через ChromaDB (если доступен), иначе fallback на SimpleRetriever.
        """
        if top_k is None:
            top_k = config.TOP_K_BLOCKS
        
        # TODO: реализовать ChromaDB поиск, когда он будет готов
        # Пока что используем SimpleRetriever
        logger.debug("ChromaDB еще не готов, используем SimpleRetriever")
        
        simple_retriever = SimpleRetriever()
        return simple_retriever.retrieve(query, top_k)


# Создаем глобальный retriever (выбор между Simple и ChromaDB)
def get_retriever(use_chromadb: bool = False) -> SimpleRetriever:
    """Получить экземпляр retriever'а"""
    if use_chromadb:
        return ChromaDBRetriever(use_chromadb=True)
    else:
        return SimpleRetriever()
```

**Ключевые моменты:**

- `SimpleRetriever`: TF-IDF + косинусное сходство (не требует доп. зависимостей, кроме scikit-learn).
- `ChromaDBRetriever`: заглушка на будущее, когда ChromaDB будет полностью интегрирована.
- Возвращает список (Block, score) с фильтром по минимальному порогу.
- Поиск по title + keywords + summary каждого блока.

***

### 3.4 `llm_answerer.py`

**Назначение:** Сформировать ответ через LLM, опираясь на найденные блоки.

**Содержимое:**

```python
# bot_agent/llm_answerer.py

import logging
from typing import List, Dict, Optional
from dataclasses import asdict
import os

from data_loader import Block
from config import config

logger = logging.getLogger(__name__)


class LLMAnswerer:
    """
    Формирует ответ на основе найденных блоков, используя OpenAI API.
    """
    
    def __init__(self):
        self.api_key = config.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("❌ OPENAI_API_KEY не установлен в .env")
        
        # Инициализируем OpenAI клиент
        try:
            import openai
            self.client = openai.OpenAI(api_key=self.api_key)
        except ImportError:
            logger.error("❌ openai пакет не установлен. Установите: pip install openai")
            raise
    
    def build_system_prompt(self) -> str:
        """
        Системный промпт для бота-психолога.
        Определяет его поведение и ограничения.
        """
        return """Ты — спокойный и поддерживающий гид, специализирующийся на учении Саламата Сарсекенова о нейросталкинге и трансформации сознания.

ТВОЕ ПОВЕДЕНИЕ:
1. Отвечай спокойно, уважительно, без суждений.
2. Используй информацию из предоставленных материалов лекций.
3. Если пользователь спрашивает что-то за пределами материала, скажи: "В доступных материалах это не освещается, но я могу..."
4. Всегда старайся найти практическое применение концепции для жизни пользователя.
5. Избегай медицинских/психиатрических диагнозов. Если пользователь упоминает серьезное состояние (суицидальные мысли, неконтролируемые панические атаки), добавь в ответ дисклеймер о необходимости обращения к специалисту.

ТОНУС:
- Спокойный, но не безличный.
- "Предлагаю исследовать..." вместо "Ты должен...".
- Поддерживающий, но честный.
- Без религиозных суждений, научное и практическое объяснение.

СТРУКТУРА ОТВЕТА:
1. Прямо ответить на вопрос пользователя.
2. Привести примеры/уточнения из материалов.
3. Предложить практическое применение (если уместно).
4. Предложить глубже исследовать тему или практиковать."""
    
    def build_context_prompt(self, blocks: List[Block], user_question: str) -> str:
        """
        Формирует контекст для LLM: найденные блоки + вопрос.
        """
        context = "МАТЕРИАЛ ИЗ ЛЕКЦИЙ:\n\n"
        
        for i, block in enumerate(blocks, 1):
            context += f"--- БЛОК {i} ---\n"
            context += f"Из лекции: {block.document_title}\n"
            context += f"Тема: {block.title}\n"
            context += f"Видео (таймкод {block.start} — {block.end}): {block.youtube_link}\n"
            context += f"Резюме: {block.summary}\n"
            context += f"Полный текст:\n{block.content}\n\n"
        
        context += f"\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_question}"
        
        return context
    
    def generate_answer(
        self,
        user_question: str,
        blocks: List[Block],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, any]:
        """
        Формирует ответ через OpenAI API.
        
        Возвращает:
            {
                "answer": str,                 # готовый ответ
                "model_used": str,             # какую модель использовали
                "tokens_used": int,            # примерное количество токенов
                "error": Optional[str]         # если была ошибка
            }
        """
        if not blocks:
            logger.warning("⚠️ Нет блоков для контекста!")
            return {
                "answer": "К сожалению, я не нашел релевантного материала для ответа на ваш вопрос. Попробуйте переформулировать вопрос.",
                "model_used": None,
                "tokens_used": 0,
                "error": "no_blocks"
            }
        
        model = model or config.LLM_MODEL
        temperature = temperature if temperature is not None else config.LLM_TEMPERATURE
        max_tokens = max_tokens or config.LLM_MAX_TOKENS
        
        system_prompt = self.build_system_prompt()
        context = self.build_context_prompt(blocks, user_question)
        
        logger.debug(f"📤 Отправляю запрос к {model}...")
        
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context}
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            
            answer = response.choices[0].message.content
            tokens = response.usage.total_tokens
            
            logger.debug(f"✅ Ответ получен ({tokens} токенов)")
            
            return {
                "answer": answer,
                "model_used": model,
                "tokens_used": tokens,
                "error": None
            }
        
        except Exception as e:
            logger.error(f"❌ Ошибка при вызове OpenAI API: {e}")
            return {
                "answer": f"Извините, произошла ошибка при формировании ответа: {str(e)}",
                "model_used": model,
                "tokens_used": 0,
                "error": str(e)
            }
```

**Ключевые моменты:**

- Системный промпт определяет поведение бота.
- Контекст включает все найденные блоки + youtube_link + таймкоды.
- Ошибка обрабатывается gracefully.
- Возвращает структурированный результат.

***

### 3.5 `answer_basic.py`

**Назначение:** Главная функция Phase 1. Орхестрирует все компоненты.

**Содержимое:**

```python
# bot_agent/answer_basic.py

import logging
from typing import Dict, List, Optional
from datetime import datetime

from data_loader import data_loader, Block
from retriever import get_retriever
from llm_answerer import LLMAnswerer
from config import config

logger = logging.getLogger(__name__)


def answer_question_basic(
    query: str,
    top_k: Optional[int] = None,
    use_chromadb: bool = False,
    debug: bool = False
) -> Dict:
    """
    Основная функция Phase 1: QA по лекциям.
    
    Аргументы:
        query (str): Вопрос пользователя на русском.
        top_k (int, optional): Сколько релевантных блоков использовать.
                              По умолчанию из config.TOP_K_BLOCKS.
        use_chromadb (bool): Использовать ChromaDB для поиска.
                            По умолчанию False.
        debug (bool): Если True, возвращает отладочную информацию.
    
    Возвращает:
        Dict с ключами:
            - "status": "success" или "error"
            - "answer": str — готовый ответ пользователю
            - "sources": List[Dict] — источники (block_id, title, youtube_link, start, end)
            - "blocks_used": int — сколько блоков использовано
            - "timestamp": str — когда был сформирован ответ
            - "debug": Optional[Dict] — отладочная информация
    
    Пример использования:
        >>> result = answer_question_basic("Как работает осознавание?")
        >>> print(result["answer"])
        >>> print(result["sources"])
    """
    
    logger.info(f"📋 Начинаю обработку запроса: '{query}'")
    
    top_k = top_k or config.TOP_K_BLOCKS
    start_time = datetime.now()
    debug_info = {} if debug else None
    
    try:
        # === ЭТАП 1: Загрузка данных ===
        logger.debug("📂 Этап 1: Загрузка данных...")
        data_loader.load_all_data()
        
        if not data_loader.get_all_blocks():
            return {
                "status": "error",
                "answer": "❌ Не удалось загрузить данные лекций. Проверьте наличие файлов в data/sag_final/",
                "sources": [],
                "blocks_used": 0,
                "error": "no_data",
                "debug": {"error_detail": "data_loader returned empty blocks"}
            }
        
        if debug_info is not None:
            debug_info["data_loaded"] = {
                "total_documents": len(data_loader.get_all_documents()),
                "total_blocks": len(data_loader.get_all_blocks())
            }
        
        # === ЭТАП 2: Поиск релевантных блоков ===
        logger.debug("🔍 Этап 2: Поиск релевантных блоков...")
        retriever = get_retriever(use_chromadb=use_chromadb)
        retrieved_blocks = retriever.retrieve(query, top_k=top_k)
        
        if not retrieved_blocks:
            logger.warning(f"⚠️ Не найдено релевантных блоков для: '{query}'")
            return {
                "status": "partial",
                "answer": "К сожалению, я не нашел четко релевантного материала для этого вопроса. Попробуйте переформулировать или спросить что-то более конкретное.",
                "sources": [],
                "blocks_used": 0,
                "timestamp": datetime.now().isoformat(),
                "debug": debug_info
            }
        
        blocks = [block for block, score in retrieved_blocks]
        
        if debug_info is not None:
            debug_info["retrieval"] = {
                "query": query,
                "blocks_found": len(blocks),
                "scores": [float(score) for block, score in retrieved_blocks]
            }
        
        logger.info(f"✅ Найдено {len(blocks)} релевантных блоков")
        
        # === ЭТАП 3: Формирование ответа через LLM ===
        logger.debug("🤖 Этап 3: Формирование ответа через LLM...")
        answerer = LLMAnswerer()
        llm_result = answerer.generate_answer(query, blocks)
        
        if llm_result.get("error"):
            logger.error(f"❌ Ошибка при формировании ответа: {llm_result['error']}")
            return {
                "status": "error",
                "answer": llm_result.get("answer", "Произошла ошибка при формировании ответа."),
                "sources": [],
                "blocks_used": 0,
                "error": llm_result.get("error"),
                "timestamp": datetime.now().isoformat(),
                "debug": debug_info
            }
        
        if debug_info is not None:
            debug_info["llm"] = {
                "model": llm_result.get("model_used"),
                "tokens_used": llm_result.get("tokens_used")
            }
        
        # === ЭТАП 4: Формирование источников ===
        logger.debug("📝 Этап 4: Формирование информации об источниках...")
        sources = [
            {
                "block_id": b.block_id,
                "title": b.title,
                "summary": b.summary,
                "document_title": b.document_title,
                "youtube_link": b.youtube_link,
                "start": b.start,
                "end": b.end,
                "video_id": b.video_id
            }
            for b in blocks
        ]
        
        # === ФИНАЛЬНЫЙ РЕЗУЛЬТАТ ===
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            "status": "success",
            "answer": llm_result["answer"],
            "sources": sources,
            "blocks_used": len(blocks),
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(elapsed_time, 2)
        }
        
        if debug_info is not None:
            debug_info["total_time"] = elapsed_time
            result["debug"] = debug_info
        
        logger.info(f"✅ Запрос обработан успешно за {elapsed_time:.2f}с")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Непредвиденная ошибка: {e}", exc_info=True)
        return {
            "status": "error",
            "answer": f"❌ Произошла непредвиденная ошибка: {str(e)}",
            "sources": [],
            "blocks_used": 0,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
            "debug": debug_info
        }


# === ПРОСТОЙ ИНТЕРФЕЙС ДЛЯ БЫСТРОГО ИСПОЛЬЗОВАНИЯ ===

def ask(query: str, verbose: bool = False) -> str:
    """
    Простой интерфейс: вопрос -> ответ (только текст).
    
    Используется если нужен только текст ответа:
        >>> print(ask("Что такое разотождествление?"))
    """
    result = answer_question_basic(query, debug=verbose)
    
    if verbose:
        print(f"\n[DEBUG] Sources: {len(result['sources'])} блоков")
        for src in result['sources']:
            print(f"  - {src['document_title']} ({src['start']}): {src['youtube_link']}")
    
    return result["answer"]
```

**Ключевые моменты:**

- Главная функция `answer_question_basic()`.
- Простой интерфейс `ask()` для быстрого использования.
- Возвращает структурированный результат с метаданными.
- Полное логирование каждого этапа.
- Обработка ошибок на каждом уровне.

***

## Часть 4: Примеры промптов для LLM

### 4.1 Системный промпт (в `llm_answerer.py`)

```
Ты — спокойный и поддерживающий гид, специализирующийся на учении Саламата Сарсекенова о нейросталкинге и трансформации сознания.

ТВОЕ ПОВЕДЕНИЕ:
1. Отвечай спокойно, уважительно, без суждений.
2. Используй информацию из предоставленных материалов лекций.
3. Если пользователь спрашивает что-то за пределами материала, скажи: "В доступных материалах это не освещается, но я могу..."
4. Всегда старайся найти практическое применение концепции для жизни пользователя.
5. Избегай медицинских/психиатрических диагнозов. Если пользователь упоминает серьезное состояние (суицидальные мысли, неконтролируемые панические атаки), добавь в ответ дисклеймер о необходимости обращения к специалисту.

ТОНУС:
- Спокойный, но не безличный.
- "Предлагаю исследовать..." вместо "Ты должен...".
- Поддерживающий, но честный.
- Без религиозных суждений, научное и практическое объяснение.

СТРУКТУРА ОТВЕТА:
1. Прямо ответить на вопрос пользователя.
2. Привести примеры/уточнения из материалов.
3. Предложить практическое применение (если уместно).
4. Предложить глубже исследовать тему или практиковать.
```


### 4.2 Примеры User-Prompts (контекст + вопрос)

#### Пример 1: Базовый вопрос

```
МАТЕРИАЛ ИЗ ЛЕКЦИЙ:

--- БЛОК 1 ---
Из лекции: Лекция Сарсекенова: Rxoj94WQpsQ
Тема: Процесс исцеления через самопознание
Видео (таймкод 00:00:00 — 00:08:45): https://youtube.com/watch?v=Rxoj94WQpsQ&t=0s
Резюме: Обсуждается важность подлинного исцеления без позерства и героизма.
Полный текст:
Прямо сейчас уникальный момент исцеления, но без того я, позёра, без его присутствия в этом моменте. Потому что то, что мы называем обычно исцелением, это как раз позёрство. Это просто перекраска той же самости. Исцеление — это не изменение того, что было, это полное разотождествление от того, что было.

--- БЛОК 2 ---
Из лекции: Лекция Сарсекенова: HndVzdJuAz0
Тема: Осознавание как инструмент
Видео (таймкод 00:12:30 — 00:20:15): https://youtube.com/watch?v=HndVzdJuAz0&t=750s
Резюме: Подробное объяснение того, как осознавание работает в процессе трансформации.
Полный текст:
Осознавание — это не знание в смысле информации. Осознавание — это прямое восприятие того, что происходит. Когда у тебя есть прямое восприятие, ты видишь как паттерны работают, как они создаются, как они держат тебя в определённом состоянии...

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
Как работает осознавание? Это что-то духовное или имеет практический смысл?
```

**Ожидаемый ответ LLM:**

```
Осознавание — это совсем не духовное или мистическое явление, хотя часто его так преподносят. По словам Сарсекенова, это **прямое восприятие того, что происходит** внутри нас и вокруг нас.

Практический смысл очень конкретный: когда у тебя есть осознавание, ты начинаешь видеть, как твои паттерны работают, как они создаются, и самое главное — как они держат тебя в определённом состоянии. Это не информация, которую ты можешь прочитать, — это직接 восприятие в моменте.

Это напрямую связано с процессом исцеления. Истинное исцеление происходит не через "переделку" себя, а через **полное разотождествление от того, что было** — и осознавание как раз позволяет это сделать. Когда ты видишь паттерн, ты можешь от него отделиться, вместо того чтобы оставаться его частью.

Вот почему это так практично: осознавание — это инструмент, который ты можешь развивать и использовать в реальной жизни, чтобы разобраться в себе и изменить свои реакции.

Материалы говорят об этом в лекции (смотри 00:12:30-00:20:15), где объясняется механизм подробнее.
```


***

#### Пример 2: Вопрос про практику

```
МАТЕРИАЛ ИЗ ЛЕКЦИЙ:

--- БЛОК 1 ---
Из лекции: Лекция Сарсекенова: ABC123
Тема: Практика метанаблюдения
Видео (таймкод 00:45:00 — 00:52:30): https://youtube.com/watch?v=ABC123&t=2700s
Резюме: Пошаговое объяснение практики метанаблюдения для развития осознавания.
Полный текст:
Метанаблюдение — это наблюдение за наблюдателем. Проще всего начать с дыхания. Ты не просто дышишь и не просто наблюдаешь дыхание. Ты наблюдаешь себя, который наблюдает дыхание. Это создает слой сепарации между тобой и твоими процессами. Начни с 5 минут в день, это уже включает механизм осознавания.

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
Как начать практиковать? Это сложно?
```

**Ожидаемый ответ LLM:**

```
Нет, это не сложно, но требует любопытства. Одна из базовых практик — метанаблюдение.

Вот как это работает:

1. **Сядь удобно** и просто начни наблюдать свое дыхание.
2. **Но не просто наблюдай** — наблюдай себя, который наблюдает дыхание. Это создает очень важную "сепарацию" между тобой и твоими процессами.
3. **Начни с 5 минут в день**. Этого достаточно, чтобы включить механизм осознавания.

Почему это работает? Обычно мы полностью отождествлены со своими мыслями и дыханием. Метанаблюдение создает расстояние — ты становишься наблюдателем, а не полным участником. Это включает совершенно другой уровень восприятия.

Попробуй начать завтра утром с 5 минут. Не нужно много, главное регулярность.

Практика подробно объясняется в лекции (00:45:00-00:52:30).
```


***

#### Пример 3: Вопрос, где ответа нет в материалах

```
МАТЕРИАЛ ИЗ ЛЕКЦИЙ:
[не найдено релевантных блоков]

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
Как это связано с квантовой физикой?
```

**Ожидаемый ответ LLM:**

```
В доступных материалах лекций Сарсекенова связь с квантовой физикой напрямую не обсуждается.

Однако я могу предложить: учение фокусируется на практическом восприятии и трансформации сознания через осознавание — это работает независимо от физических теорий. Скорее всего, Сарсекенов предпочитает конкретный практический опыт вместо теоретических моделей.

Если тебе интересна тема измерения/наблюдателя в квантовой физике — это философски интересно, но для трансформации сознания в первую очередь стоит экспериментировать с практиками осознавания.

Может быть, твой вопрос про что-то конкретное? Я помогу разобраться в рамках доступных материалов.
```


***

## Часть 5: Логирование и отладка

### 5.1 Настройка логирования

```python
# bot_agent/__init__.py

import logging
from pathlib import Path

# Создаем папку для логов
LOG_DIR = Path("logs/bot_agent")
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Настройка основного логера
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "bot_agent.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("bot_agent")
logger.info("🚀 Bot Agent инициализирован")
```


### 5.2 Примеры логов

```
2025-12-17 16:30:45,123 | bot_agent.answer_basic | INFO | 📋 Начинаю обработку запроса: 'Как работает осознавание?'
2025-12-17 16:30:45,234 | bot_agent.data_loader | DEBUG | 📂 Этап 1: Загрузка данных...
2025-12-17 16:30:46,100 | bot_agent.data_loader | INFO | ✅ Загружено: 12 документов, 85 блоков
2025-12-17 16:30:46,200 | bot_agent.retriever | DEBUG | 🔍 Этап 2: Поиск релевантных блоков...
2025-12-17 16:30:46,850 | bot_agent.retriever | DEBUG | 🔍 Найдено 3 релевантных блока для запроса: 'Как работает осознавание?'
2025-12-17 16:30:46,900 | bot_agent.llm_answerer | DEBUG | 🤖 Этап 3: Формирование ответа через LLM...
2025-12-17 16:30:48,500 | bot_agent.llm_answerer | DEBUG | 📤 Отправляю запрос к gpt-4o-mini...
2025-12-17 16:30:50,000 | bot_agent.llm_answerer | DEBUG | ✅ Ответ получен (342 токенов)
2025-12-17 16:30:50,100 | bot_agent.answer_basic | INFO | ✅ Запрос обработан успешно за 4.98с
```


***

## Часть 6: Примеры использования

### 6.1 Использование в коде

```python
# example_usage.py

from bot_agent.answer_basic import answer_question_basic, ask

# === ВАРИАНТ 1: Полный результат со всеми деталями ===
result = answer_question_basic("Как работает осознавание?", debug=True)

print("Status:", result["status"])
print("Answer:")
print(result["answer"])
print("\nSources:")
for src in result["sources"]:
    print(f"  - {src['title']}")
    print(f"    Video: {src['youtube_link']}")
    print(f"    Time: {src['start']} - {src['end']}")

# === ВАРИАНТ 2: Только текст ответа ===
answer = ask("Какие практики помогают развить осознавание?")
print(answer)

# === ВАРИАНТ 3: Быстрая проверка ===
result = answer_question_basic("Что такое разотождествление?")
if result["status"] == "success":
    print(f"✅ Ответ найден ({len(result['sources'])} источников)")
else:
    print(f"❌ Ошибка: {result.get('error')}")
```


### 6.2 Использование в API (FastAPI)

```python
# bot_agent/api.py (опционально для Phase 1)

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from answer_basic import answer_question_basic

app = FastAPI()

class QuestionRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    debug: Optional[bool] = False

class QuestionResponse(BaseModel):
    status: str
    answer: str
    sources: list
    blocks_used: int

@app.post("/api/v1/ask")
async def ask_question(request: QuestionRequest):
    """Endpoint для QA по лекциям"""
    result = answer_question_basic(
        query=request.query,
        top_k=request.top_k,
        debug=request.debug
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result.get("error"))
    
    return QuestionResponse(**{k: v for k, v in result.items() if k in QuestionResponse.__fields__})
```


***

## Часть 7: Чек-лист для агента Cursor

### Что нужно создать:

- [ ] **`bot_agent/__init__.py`** — инициализация пакета + логирование
- [ ] **`bot_agent/config.py`** — конфигурация (пути, параметры)
- [ ] **`bot_agent/data_loader.py`** — загрузка и кэширование JSON
- [ ] **`bot_agent/retriever.py`** — поиск релевантных блоков
- [ ] **`bot_agent/llm_answerer.py`** — формирование ответа через LLM
- [ ] **`bot_agent/answer_basic.py`** — главная функция Phase 1


### Зависимости:

```
openai>=1.0.0
scikit-learn>=1.0.0
python-dotenv>=1.0.0
```


### Тестирование:

- [ ] Проверить загрузку всех JSON файлов из `data/sag_final/`
- [ ] Проверить поиск релевантных блоков
- [ ] Проверить формирование ответа через OpenAI API
- [ ] Проверить, что все ссылки на видео содержат корректные таймкоды
- [ ] Проверить обработку ошибок (отсутствие файлов, API ошибки, пустые результаты)


### Примеры тестовых запросов:

```python
test_queries = [
    "Что такое нейросталкинг?",
    "Как развить осознавание?",
    "Чем отличается разотождествление от отрицания?",
    "Какие практики помогают при паттернах?",
    "Как связаны исцеление и осознавание?"
]
```


***

## Резюме

**Phase 1** — это **фундамент**. После его реализации будет:

✅ Работающий QA-бот, который находит релевантные блоки
✅ Ответы через LLM с правильным тоном
✅ Ссылки на видео с таймкодами
✅ Основа для Phase 2-4

Все остальное (State Recognition, Knowledge Graph, Path Building) строится на этом базисе.

Готов к следующему шагу? 🚀

