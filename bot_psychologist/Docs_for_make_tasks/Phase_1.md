
# 🚀 Начало реализации Phase 1 в Cursor IDE

Переходим в боевой режим. Создаю пошаговый план для агента Cursor с конкретными командами и файлами.

***

## Шаг 1: Инициализация проекта

### 1.1 Создать структуру папок

```bash
# В корне voice_bot_pipeline/
mkdir -p bot_agent
mkdir -p logs/bot_agent
touch bot_agent/__init__.py
```


### 1.2 Обновить `.env` (если нужно)

```bash
# Проверить наличие в .env:
# OPENAI_API_KEY=sk-proj-...
# PRIMARY_MODEL=gpt-4o-mini
# DATA_ROOT=data  (если не указано, по умолчанию "data")
```


### 1.3 Создать `requirements_bot.txt` (дополнительные зависимости)

```
openai>=1.3.0
scikit-learn>=1.3.0
numpy>=1.24.0
python-dotenv>=1.0.0
```

**Установка:**

```bash
pip install -r requirements_bot.txt
```


***

## Шаг 2: Создание файлов (в порядке зависимостей)

### Файл 1️⃣: `bot_agent/config.py`

Создай файл `voice_bot_pipeline/bot_agent/config.py`:

```python
# bot_agent/config.py

import os
from pathlib import Path
from typing import Optional

class Config:
    """Конфигурация для Phase 1 QA-бота"""
    
    # === Пути к данным (из voice_bot_pipeline) ===
    PROJECT_ROOT = Path(__file__).parent.parent  # voice_bot_pipeline/
    DATA_ROOT = Path(os.getenv("DATA_ROOT", "data"))
    SAG_FINAL_DIR = DATA_ROOT / "sag_final"  # где лежат обработанные JSON
    
    # === Параметры поиска ===
    TOP_K_BLOCKS = 5  # сколько релевантных блоков брать
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
    
    @classmethod
    def validate(cls):
        """Проверить что все нужное есть"""
        if not cls.OPENAI_API_KEY:
            raise ValueError("❌ OPENAI_API_KEY не установлен в .env")
        if not cls.SAG_FINAL_DIR.exists():
            raise ValueError(f"❌ Директория не найдена: {cls.SAG_FINAL_DIR}")


# Глобальный инстанс конфига
config = Config()
```


***

### Файл 2️⃣: `bot_agent/data_loader.py`

Создай файл `voice_bot_pipeline/bot_agent/data_loader.py`:

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
        text = self.content[:max_len] if len(self.content) > max_len else self.content
        return text + "..." if len(self.content) > max_len else text


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
            logger.error(f"❌ Директория не найдена: {config.SAG_FINAL_DIR}")
            return
        
        json_files = list(config.SAG_FINAL_DIR.glob("**/*.for_vector.json"))
        logger.info(f"🔍 Найдено {len(json_files)} файлов")
        
        if not json_files:
            logger.warning(f"⚠️ Не найдено *.for_vector.json файлов в {config.SAG_FINAL_DIR}")
            return
        
        for json_path in json_files:
            try:
                self._load_single_document(json_path)
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки {json_path.name}: {e}")
        
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
        
        logger.debug(f"✓ Загружено: {document_title} ({len(blocks)} блоков)")
    
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


***

### Файл 3️⃣: `bot_agent/retriever.py`

Создай файл `voice_bot_pipeline/bot_agent/retriever.py`:

```python
# bot_agent/retriever.py

import logging
from typing import List, Tuple, Optional
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
        self.vectorizer: Optional[object] = None
        self.tfidf_matrix = None
        self.blocks: List[Block] = []
        self._is_built = False
    
    def build_index(self) -> None:
        """Построить индекс на основе всех блоков"""
        if self._is_built:
            logger.info("✓ Индекс уже построен")
            return
        
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
        except ImportError:
            logger.error("❌ scikit-learn не установлен. Установите: pip install scikit-learn")
            raise
        
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
        
        from sklearn.metrics.pairwise import cosine_similarity
        
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
        
        logger.debug(f"🔍 Найдено {len(results)} релевантных блоков для: '{query}'")
        return results


def get_retriever(use_chromadb: bool = False) -> SimpleRetriever:
    """Получить экземпляр retriever'а"""
    # На Phase 1 всегда используем SimpleRetriever
    logger.debug("📦 Инициализирую SimpleRetriever")
    return SimpleRetriever()
```


***

### Файл 4️⃣: `bot_agent/llm_answerer.py`

Создай файл `voice_bot_pipeline/bot_agent/llm_answerer.py`:

```python
# bot_agent/llm_answerer.py

import logging
from typing import List, Dict, Optional

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
            logger.info("✓ OpenAI клиент инициализирован")
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
3. Если пользователь спрашивает что-то за пределами материала, скажи: "В доступных материалах это не освещается, но я могу предложить..."
4. Всегда старайся найти практическое применение концепции для жизни пользователя.
5. Избегай медицинских/психиатрических диагнозов. Если пользователь упоминает серьезное состояние (суицидальные мысли, панические атаки), добавь дисклеймер о необходимости обращения к специалисту.

ТОНУС:
- Спокойный, но не безличный.
- "Предлагаю исследовать..." вместо "Ты должен...".
- Поддерживающий, но честный.

СТРУКТУРА ОТВЕТА:
1. Прямо ответить на вопрос.
2. Привести примеры из материалов.
3. Предложить практическое применение (если уместно).
4. Упомянуть, откуда взята информация."""
    
    def build_context_prompt(self, blocks: List[Block], user_question: str) -> str:
        """
        Формирует контекст для LLM: найденные блоки + вопрос.
        """
        context = "МАТЕРИАЛ ИЗ ЛЕКЦИЙ:\n\n"
        
        for i, block in enumerate(blocks, 1):
            context += f"--- БЛОК {i} ---\n"
            context += f"Лекция: {block.document_title}\n"
            context += f"Тема: {block.title}\n"
            context += f"Таймкод: {block.start} — {block.end}\n"
            context += f"Ссылка: {block.youtube_link}\n"
            context += f"Краткое описание: {block.summary}\n"
            context += f"Полный текст:\n{block.content}\n\n"
        
        context += f"ВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{user_question}\n\n"
        context += "Сформируй ответ, опираясь на материал выше. Не забудь упомянуть источники и таймкоды."
        
        return context
    
    def generate_answer(
        self,
        user_question: str,
        blocks: List[Block],
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict:
        """
        Формирует ответ через OpenAI API.
        
        Возвращает:
            {
                "answer": str,                 # готовый ответ
                "model_used": str,             # какую модель использовали
                "tokens_used": int,            # количество токенов
                "error": Optional[str]         # если была ошибка
            }
        """
        if not blocks:
            logger.warning("⚠️ Нет блоков для контекста!")
            return {
                "answer": "К сожалению, я не нашел релевантного материала для этого вопроса. Попробуйте переформулировать.",
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
                "answer": f"Ошибка при формировании ответа: {str(e)}",
                "model_used": model,
                "tokens_used": 0,
                "error": str(e)
            }
```


***

### Файл 5️⃣: `bot_agent/answer_basic.py`

Создай файл `voice_bot_pipeline/bot_agent/answer_basic.py`:

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
        use_chromadb (bool): Использовать ChromaDB для поиска.
        debug (bool): Если True, возвращает отладочную информацию.
    
    Возвращает:
        Dict с ключами:
            - "status": "success" или "error"
            - "answer": str — готовый ответ пользователю
            - "sources": List[Dict] — источники (блоки с ссылками)
            - "blocks_used": int — сколько блоков использовано
            - "timestamp": str — когда был сформирован ответ
            - "processing_time_seconds": float
            - "debug": Optional[Dict] — отладочная информация (если debug=True)
    """
    
    logger.info(f"📋 Обработка запроса: '{query}'")
    
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
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": 0.0,
                "debug": {"error_detail": "data_loader returned empty blocks"} if debug else None
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
                "answer": "К сожалению, я не нашел четко релевантного материала для этого вопроса. Попробуйте переформулировать вопрос или спросить что-то более конкретное.",
                "sources": [],
                "blocks_used": 0,
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
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
            logger.error(f"❌ Ошибка LLM: {llm_result['error']}")
            return {
                "status": "error",
                "answer": llm_result.get("answer", "Произошла ошибка при формировании ответа."),
                "sources": [],
                "blocks_used": 0,
                "error": llm_result.get("error"),
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
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
        
        logger.info(f"✅ Запрос обработан за {elapsed_time:.2f}с")
        
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
            "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
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
    
    if verbose and result.get("sources"):
        print(f"\n[DEBUG 📚] Источники ({len(result['sources'])} блоков):")
        for src in result['sources']:
            print(f"  • {src['document_title']} ({src['start']}—{src['end']})")
            print(f"    → {src['youtube_link']}")
    
    return result["answer"]
```


***

### Файл 6️⃣: `bot_agent/__init__.py`

Создай файл `voice_bot_pipeline/bot_agent/__init__.py`:

```python
# bot_agent/__init__.py

import logging
from pathlib import Path
import sys

# Добавляем родительскую папку в путь
sys.path.insert(0, str(Path(__file__).parent))

# Создаем папку для логов
LOG_DIR = Path(__file__).parent.parent / "logs" / "bot_agent"
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

# Импортируем основные функции
from answer_basic import answer_question_basic, ask

__all__ = ["answer_question_basic", "ask"]

logger.info("🚀 Bot Agent инициализирован (Phase 1)")
```


***

## Шаг 3: Создание тестового скрипта

Создай файл `voice_bot_pipeline/test_phase1.py`:

```python
# test_phase1.py
"""
Тестирование Phase 1 бота
"""

import sys
from pathlib import Path

# Добавляем bot_agent в путь
sys.path.insert(0, str(Path(__file__).parent / "bot_agent"))

from answer_basic import answer_question_basic, ask

print("=" * 70)
print("🧪 ТЕСТИРОВАНИЕ PHASE 1 - QA БОТ")
print("=" * 70)

# Тестовые вопросы
test_queries = [
    "Что такое осознавание?",
    "Как развить осознавание в повседневной жизни?",
    "Какова связь между исцелением и разотождествлением?",
    "Какие практики рекомендуются для начинающих?",
]

print("\n[INFO] Загружаю данные из sag_final/...")

for i, query in enumerate(test_queries, 1):
    print(f"\n{'='*70}")
    print(f"ТЕСТ {i}/{len(test_queries)}")
    print(f"{'='*70}")
    print(f"\n📋 Вопрос: {query}\n")
    
    try:
        result = answer_question_basic(query, debug=True)
        
        print(f"Status: {result['status']}")
        print(f"Processing time: {result['processing_time_seconds']}s")
        print(f"Blocks used: {result['blocks_used']}")
        
        print(f"\n💬 ОТВЕТ:\n{result['answer']}")
        
        if result.get('sources'):
            print(f"\n📚 ИСТОЧНИКИ ({len(result['sources'])} блоков):")
            for src in result['sources']:
                print(f"  • {src['title']}")
                print(f"    Лекция: {src['document_title']}")
                print(f"    Таймкод: {src['start']}—{src['end']}")
                print(f"    Ссылка: {src['youtube_link']}\n")
        
        if result.get('debug'):
            print(f"\n🔧 DEBUG INFO:")
            import json
            print(json.dumps(result['debug'], indent=2, ensure_ascii=False))
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 70)
print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
print("=" * 70)
```


***

## Шаг 4: Запуск тестов

```bash
# Перейти в корень проекта
cd voice_bot_pipeline

# Установить зависимости
pip install -r requirements_bot.txt

# Запустить тест
python test_phase1.py
```


***

## Шаг 5: Проверка работоспособности

### Что должно произойти:

```
🧪 ТЕСТИРОВАНИЕ PHASE 1 - QA БОТ
======================================================================

[INFO] Загружаю данные из sag_final/...

======================================================================
ТЕСТ 1/4
======================================================================

📋 Вопрос: Что такое осознавание?

Status: success
Processing time: 4.87s
Blocks used: 5

💬 ОТВЕТ:
[Здесь будет развернутый ответ от LLM]

📚 ИСТОЧНИКИ (5 блоков):
  • Осознавание как инструмент трансформации
    Лекция: Лекция Сарсекенова: Rxoj94WQpsQ
    Таймкод: 00:12:30—00:20:15
    Ссылка: https://youtube.com/watch?v=Rxoj94WQpsQ&t=750s
...
```


***

## 🎯 Чек-лист выполнения

- [ ] Создана папка `bot_agent/`
- [ ] Созданы все 6 файлов Python (config, data_loader, retriever, llm_answerer, answer_basic, __init__)
- [ ] Установлены зависимости (`pip install -r requirements_bot.txt`)
- [ ] Создан тестовый скрипт `test_phase1.py`
- [ ] Запущен тест и получены ответы от LLM
- [ ] Все ссылки на видео содержат правильные таймкоды
- [ ] Логирование работает (файл `logs/bot_agent/bot_agent.log`)

***

## ⚡ Возможные проблемы и решения

### Проблема 1: `ModuleNotFoundError: No module named 'openai'`

**Решение:**

```bash
pip install openai>=1.3.0
```


### Проблема 2: `EnvironmentError: OPENAI_API_KEY not set`

**Решение:**

- Проверить файл `.env`:

```env
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
```


### Проблема 3: `FileNotFoundError: [Errno 2] No such file or directory: 'data/sag_final'`

**Решение:**

- Убедитесь, что пайплайн обработал хотя бы одно видео
- Проверьте наличие файлов: `ls -la data/sag_final/`


### Проблема 4: `ImportError: No module named 'sklearn'`

**Решение:**

```bash
pip install scikit-learn
```


***

## 📞 Готово! 🎉

Phase 1 готова к запуску. Следующие шаги:

1. ✅ Запустить тесты
2. ✅ Проверить качество ответов
3. ✅ Адаптировать промпты если нужно
4. ➡️ Переходим на Phase 2 (SAG v2.0 aware ответы)



