# bot_agent/data_loader.py
"""
Data Loader for SAG v2.0 JSON files
===================================

Загрузка и кэширование данных из voice_bot_pipeline.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime

from .config import config

logger = logging.getLogger(__name__)


def _detect_block_type(title: str, content: str) -> str:
    """
    Автоматически определяет тип блока по заголовку и контенту.
    Используется для блоков из Bot_data_base, где block_type отсутствует.

    Returns:
        "practice"   — если блок содержит упражнение/практику
        "case_study" — если блок содержит кейс/диалог/пример из жизни
        "quote"      — если блок состоит преимущественно из цитат
        "theory"     — всё остальное (по умолчанию)
    """
    title_lower = title.lower()
    content_lower = content.lower()

    # Паттерны для практик
    practice_keywords = [
        "практика", "упражнение", "задание", "техника",
        "practice", "exercise", "попробуй", "сделай",
        "шаг 1", "шаг 2", "время:", "цель:"
    ]
    if any(kw in title_lower for kw in practice_keywords):
        return "practice"
    # Контент-паттерны практик (инструкции)
    if content_lower.count("**") >= 4 and any(
        kw in content_lower for kw in ["цель:", "время:", "минут"]
    ):
        return "practice"

    # Паттерны для кейсов
    case_keywords = ["кейс", "случай", "пример", "история", "case"]
    dialogue_markers = ["— ", "– ", "> —", "> –"]
    if any(kw in title_lower for kw in case_keywords):
        return "case_study"
    if sum(content.count(m) for m in dialogue_markers) >= 3:
        return "case_study"

    # Паттерны для цитат
    if content.count('«') >= 3 or content.count('"') >= 4:
        return "quote"

    return "theory"


@dataclass
class Block:
    """
    Универсальный блок знаний. Поддерживает два источника:
      - SAG v2.0 (YouTube-лекции): все поля заполнены, шкала complexity 1-10
      - Bot_data_base v1.0 (книги/документы): video_id/start/end/youtube_link пустые,
        complexity нормализована из 0-1 в 1-10 при парсинге

    ВАЖНО: поле complexity_score всегда в шкале 1-10.
    """
    # --- Обязательные поля (общие для обоих форматов) ---
    block_id: str
    title: str
    content: str

    # --- Общие опциональные ---
    summary: str = ""
    document_title: str = ""

    # --- YouTube-специфичные (пустые для книг) ---
    video_id: str = ""
    start: str = "00:00:00"
    end: str = "00:00:00"
    youtube_link: str = ""
    keywords: List[str] = field(default_factory=list)

    # --- SAG v2.0 аналитические поля ---
    block_type: Optional[str] = None        # "theory"|"practice"|"case_study"|"quote"
    emotional_tone: Optional[str] = None    # "explanatory"|"inspirational"|"challenging"
    conceptual_depth: Optional[str] = None  # "low"|"medium"|"high"
    complexity_score: Optional[float] = None  # ВСЕГДА шкала 1-10
    graph_entities: Optional[List[str]] = None

    # --- SD-разметка ---
    sd_level: Optional[str] = None
    sd_secondary: Optional[str] = None
    sd_confidence: Optional[float] = None   # из bot_data_base (0.0–1.0)

    # --- Метаданные источника ---
    source_type: str = "book"               # "book" | "youtube"
    author: str = ""
    author_id: str = ""
    chunk_index: int = 0
    language: str = "ru"

    def __post_init__(self):
        if self.graph_entities is None:
            self.graph_entities = []
        if self.block_type is None:
            self.block_type = "theory"
        if self.emotional_tone is None:
            self.emotional_tone = "explanatory"
        if self.conceptual_depth is None:
            self.conceptual_depth = "medium"
        if self.complexity_score is None:
            self.complexity_score = 5.0
        # Если summary пустое — используем title как fallback
        if not self.summary and self.title:
            self.summary = self.title

    def get_preview(self, max_len: int = 200) -> str:
        text = self.content[:max_len] if len(self.content) > max_len else self.content
        return text + "..." if len(self.content) > max_len else text

    def get_search_text(self) -> str:
        """
        Текст для TF-IDF индексирования.
        Для YouTube-блоков: title + keywords + summary + content[:300]
        Для книжных блоков: title + summary + content[:500] (keywords пустые)
        """
        keywords_str = " ".join(self.keywords) if self.keywords else ""
        # Для книг keywords пустые — берём больше контента
        content_preview = self.content[:500] if not self.keywords else self.content[:300]
        return f"{self.title} {keywords_str} {self.summary} {content_preview}".strip()

    def get_entities_text(self) -> str:
        return " ".join(self.graph_entities) if self.graph_entities else ""

    def is_practice(self) -> bool:
        """True если блок содержит практику (для practices_recommender)."""
        return self.block_type == "practice"

    def has_graph_data(self) -> bool:
        """True если блок содержит граф-сущности (для graph_client)."""
        return bool(self.graph_entities)


@dataclass
class Document:
    """
    Представление одной лекции (документа).
    
    Документ содержит метаданные и список блоков.
    """
    video_id: str
    source_url: str
    title: str
    blocks: List[Block] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    
    def get_all_text(self) -> str:
        """Вернуть весь текст документа"""
        return " ".join([b.content for b in self.blocks])
    
    def get_block_count(self) -> int:
        """Количество блоков в документе"""
        return len(self.blocks)


class DataLoader:
    """
    Загружает и кэширует все SAG v2.0 JSON файлы.
    
    Синглтон: используйте глобальный `data_loader` вместо создания новых инстансов.
    
    Usage:
        >>> from data_loader import data_loader
        >>> data_loader.load_all_data()
        >>> blocks = data_loader.get_all_blocks()
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
        Загрузить данные из настроенного источника знаний.

        Поддерживаемые режимы (KNOWLEDGE_SOURCE):
          - "json"     → SAG v2.0 JSON (voice_bot_pipeline/sag_final) — legacy
          - "db_json"  → Bot_data_base exported JSON (без сервера)
          - "chromadb" → Bot_data_base через HTTP API

        Данные кэшируются в памяти. Повторный вызов не перезагружает данные.
        """
        if self._is_loaded:
            logger.info("✓ Данные уже загружены, используем кэш")
            return

        source = config.KNOWLEDGE_SOURCE
        logger.info(f"📂 KNOWLEDGE_SOURCE={source}")

        if source == "chromadb":
            self._load_from_chromadb()
        elif source == "db_json":
            self._load_from_db_json()
        else:
            self._load_from_sag_json()  # legacy

        self._is_loaded = True
        self.loaded_at = datetime.now()
        logger.info(
            f"✅ Загружено: {len(self.documents)} документов, "
            f"{len(self.all_blocks)} блоков "
            f"[source={source}]"
        )
    
    def _load_single_document(self, json_path: Path) -> None:
        """
        Загрузить один JSON файл и распарсить его.
        
        Phase 2: Добавлена поддержка полей SAG v2.0.
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        document_title = data.get("document_title", "Unknown")
        doc_metadata = data.get("document_metadata", {})
        video_id = doc_metadata.get("video_id", json_path.stem)
        source_url = doc_metadata.get("source_url", "")
        
        blocks = []
        for block_data in data.get("blocks", []):
            # Парсим complexity_score с валидацией типа
            raw_complexity = block_data.get("complexity_score")
            complexity_score = None
            if raw_complexity is not None:
                try:
                    complexity_score = float(raw_complexity)
                except (ValueError, TypeError):
                    complexity_score = None
            
            # === ПАРСИНГ SD-МЕТАДАННЫХ ===
            sd_meta = block_data.get("sd_metadata", {}) or {}
            
            block = Block(
                block_id=block_data.get("block_id", ""),
                video_id=block_data.get("video_id", video_id),
                start=block_data.get("start", "00:00:00"),
                end=block_data.get("end", "00:00:00"),
                title=block_data.get("title", ""),
                summary=block_data.get("summary", ""),
                content=block_data.get("content", ""),
                keywords=block_data.get("keywords", []),
                youtube_link=block_data.get("youtube_link", ""),
                document_title=document_title,
                # === НОВЫЕ ПОЛЯ SAG v2.0 (Phase 2) ===
                block_type=block_data.get("block_type"),
                emotional_tone=block_data.get("emotional_tone"),
                conceptual_depth=block_data.get("conceptual_depth"),
                complexity_score=complexity_score,
                graph_entities=block_data.get("graph_entities"),
                # === SD-РАЗМЕТКА ===
                sd_level=sd_meta.get("sd_level"),
                sd_secondary=sd_meta.get("sd_secondary")
            )
            blocks.append(block)
            self._block_id_to_block[block.block_id] = block
            self.all_blocks.append(block)
        
        doc = Document(
            video_id=video_id,
            source_url=source_url,
            title=document_title,
            blocks=blocks,
            metadata=doc_metadata
        )
        
        self.documents.append(doc)
        self._video_id_to_doc[video_id] = doc
        
        logger.debug(f"✓ Загружено: {document_title} ({len(blocks)} блоков)")
    
    def get_all_blocks(self) -> List[Block]:
        """
        Вернуть все блоки из всех документов.
        
        Автоматически загружает данные если они ещё не загружены.
        """
        if not self._is_loaded:
            self.load_all_data()
        return self.all_blocks
    
    def get_all_documents(self) -> List[Document]:
        """Вернуть все документы"""
        if not self._is_loaded:
            self.load_all_data()
        return self.documents
    
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
    
    def get_blocks_by_video_id(self, video_id: str) -> List[Block]:
        """Вернуть все блоки документа"""
        doc = self.get_document_by_video_id(video_id)
        return doc.blocks if doc else []

    def _load_from_sag_json(self) -> None:
        """
        ИСХОДНАЯ логика load_all_data() — без изменений логики,
        только переименована. SAG v2.0 YouTube-формат.
        Добавляет source_type="youtube" к каждому блоку.
        """
        logger.info(f"📂 Загрузка SAG v2.0 данных из {config.SAG_FINAL_DIR}")

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

    def _load_from_db_json(self) -> None:
        """
        Загрузка из exported Bot_data_base JSON-файлов (без запущенного сервера).
        Поддерживает:
          - одиночные файлы (*_blocks.json)
          - merged JSON (список источников в одном файле)
        """
        db_export_file = Path(config.DB_EXPORT_FILE) if config.DB_EXPORT_FILE else None
        db_json_dir = Path(config.DB_JSON_DIR) if config.DB_JSON_DIR else None

        if db_export_file and db_export_file.exists():
            logger.info(f"📖 DB_JSON: загрузка из файла {db_export_file}")
            self._parse_db_json_file(db_export_file)
            return

        if db_json_dir and db_json_dir.exists():
            json_files = sorted(db_json_dir.glob("**/*_blocks.json"))
            logger.info(f"📖 DB_JSON: найдено {len(json_files)} файлов в {db_json_dir}")
            for json_path in json_files:
                try:
                    self._parse_db_json_file(json_path)
                except Exception as e:
                    logger.error(f"❌ Ошибка загрузки {json_path.name}: {e}")
            return

        logger.error("❌ DB_JSON mode: ни DB_JSON_DIR, ни DB_EXPORT_FILE не настроены")

    def _parse_db_json_file(self, json_path: Path) -> None:
        """
        Парсит один bot_data_base_v1.0 JSON файл.

        КРИТИЧЕСКИЕ ТРАНСФОРМАЦИИ:
          1. complexity (0-1) → complexity_score (1-10): умножаем на 10
          2. summary пустое → используем title как fallback (в __post_init__ Block)
          3. block_type → авто-определяем через _detect_block_type()
          4. sd_level читается напрямую (не через sd_metadata как в SAG)
        """
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Поддержка merged формата (список) и одиночного (dict)
        sources = data if isinstance(data, list) else [data]

        for source_data in sources:
            source_id = source_data.get("source_id", json_path.stem)
            source_type = source_data.get("source_type", "book")
            blocks = []

            for bd in source_data.get("blocks", []):
                meta = bd.get("metadata", {})

                # ВАЖНО: нормализация complexity 0-1 → 1-10
                raw_complexity = bd.get("complexity")
                try:
                    raw_val = float(raw_complexity) if raw_complexity is not None else 0.5
                    # Если значение в диапазоне 0-1, нормализуем в 1-10
                    if 0.0 <= raw_val <= 1.0:
                        complexity = round(raw_val * 10, 1)
                    else:
                        complexity = round(raw_val, 1)
                except (ValueError, TypeError):
                    complexity = 5.0

                title = bd.get("title", "")
                text_content = bd.get("text", "")

                # Авто-определение block_type для книжных блоков
                block_type = _detect_block_type(title, text_content)

                block = Block(
                    block_id=bd.get("id", ""),
                    title=title,
                    content=text_content,
                    summary=bd.get("summary", ""),
                    document_title=meta.get("source_title", source_id),
                    sd_level=bd.get("sd_level"),
                    sd_secondary=None,
                    sd_confidence=bd.get("sd_confidence"),
                    complexity_score=complexity,
                    block_type=block_type,
                    source_type=meta.get("source_type", source_type),
                    author=meta.get("author", ""),
                    author_id=meta.get("author_id", ""),
                    chunk_index=meta.get("chunk_index", 0),
                    language=meta.get("language", "ru"),
                    # YouTube-поля пусты для книг
                    video_id="",
                    start="00:00:00",
                    end="00:00:00",
                    youtube_link="",
                    keywords=[],
                    graph_entities=[],
                )
                blocks.append(block)
                self._block_id_to_block[block.block_id] = block
                self.all_blocks.append(block)

            doc = Document(
                video_id=source_id,
                source_url="",
                title=source_id,
                blocks=blocks,
                metadata={
                    "schema_version": source_data.get("schema_version", ""),
                    "source_type": source_type,
                },
            )
            self.documents.append(doc)
            self._video_id_to_doc[source_id] = doc
            logger.debug(f"✓ DB_JSON: {source_id} ({len(blocks)} блоков)")

    def _load_from_chromadb(self) -> None:
        """
        В режиме chromadb: загружает ВСЕ блоки из ChromaLoader для построения
        TF-IDF индекса. Семантический поиск выполняется напрямую в retriever.py.
        """
        try:
            from .chroma_loader import chroma_loader
            blocks = chroma_loader.get_all_blocks()

            if not blocks:
                logger.warning(
                    "[CHROMADB] Не удалось загрузить блоки. "
                    f"Проверьте что Bot_data_base запущен на {config.CHROMA_API_URL}"
                )
                return

            self.all_blocks = blocks
            self._block_id_to_block = {b.block_id: b for b in blocks}

            # Группируем блоки в Document-объекты по document_title
            docs_map: Dict[str, List[Block]] = {}
            for b in blocks:
                key = b.document_title or b.video_id or "unknown"
                docs_map.setdefault(key, []).append(b)

            for title, doc_blocks in docs_map.items():
                doc_blocks_sorted = sorted(doc_blocks, key=lambda b: b.chunk_index)
                doc = Document(
                    video_id=title,
                    source_url="",
                    title=title,
                    blocks=doc_blocks_sorted,
                )
                self.documents.append(doc)
                self._video_id_to_doc[title] = doc

            logger.info(
                f"✅ ChromaDB: {len(blocks)} блоков из "
                f"{len(self.documents)} источников загружено"
            )
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки из ChromaDB: {e}", exc_info=True)

    def get_stats(self) -> Dict:
        """Вернуть статистику по загруженным данным"""
        if not self._is_loaded:
            self.load_all_data()

        # Подсчёт SD-распределения
        sd_distribution: Dict[str, int] = {}
        source_type_counts: Dict[str, int] = {}
        practice_count = 0

        for b in self.all_blocks:
            if b.sd_level:
                sd_distribution[b.sd_level] = sd_distribution.get(b.sd_level, 0) + 1
            source_type_counts[b.source_type] = (
                source_type_counts.get(b.source_type, 0) + 1
            )
            if b.is_practice():
                practice_count += 1

        return {
            "total_documents": len(self.documents),
            "total_blocks": len(self.all_blocks),
            "practice_blocks": practice_count,
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "knowledge_source": config.KNOWLEDGE_SOURCE,
            "sd_distribution": sd_distribution,
            "source_type_counts": source_type_counts,
        }


# Глобальный инстанс (синглтон)
data_loader = DataLoader()



