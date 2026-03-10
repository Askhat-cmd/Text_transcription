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


@dataclass
class Block:
    """
    Представление одного блока лекции.
    
    Блок — это семантическая единица контента с таймкодами.
    
    Phase 2: Добавлены поля SAG v2.0 для адаптации ответов.
    """
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
    
    # === НОВЫЕ ПОЛЯ SAG v2.0 (Phase 2) ===
    block_type: Optional[str] = None          # monologue, dialogue, practice, theory
    emotional_tone: Optional[str] = None      # contemplative, explanatory, intense, light
    conceptual_depth: Optional[str] = None    # low, medium, high
    complexity_score: Optional[float] = None  # 1.0-10.0
    graph_entities: Optional[List[str]] = None  # до 30 сущностей

    # === SD-РАЗМЕТКА (Spiral Dynamics) ===
    sd_level: Optional[str] = None            # BEIGE, PURPLE, RED, BLUE, ORANGE, GREEN, YELLOW, TURQUOISE
    sd_secondary: Optional[str] = None        # вторичный SD-уровень

    def __post_init__(self):
        """Инициализация опциональных полей SAG v2.0"""
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
    
    def get_preview(self, max_len: int = 200) -> str:
        """Вернуть краткое содержание блока"""
        text = self.content[:max_len] if len(self.content) > max_len else self.content
        return text + "..." if len(self.content) > max_len else text
    
    def get_search_text(self) -> str:
        """Вернуть текст для поиска (title + keywords + summary)"""
        keywords_str = " ".join(self.keywords) if self.keywords else ""
        return f"{self.title} {keywords_str} {self.summary}"
    
    def get_entities_text(self) -> str:
        """Вернуть текст сущностей для семантического анализа (Phase 2)"""
        return " ".join(self.graph_entities) if self.graph_entities else ""


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
        Рекурсивно загрузить все *.for_vector.json из sag_final/
        
        Данные кэшируются в памяти. Повторный вызов не перезагружает данные.
        """
        if self._is_loaded:
            logger.info("✓ Данные уже загружены, используем кэш")
            return
        
        logger.info(f"📂 Загрузка SAG v2.0 данных из {config.SAG_FINAL_DIR}")
        
        if not config.SAG_FINAL_DIR.exists():
            logger.error(f"❌ Директория не найдена: {config.SAG_FINAL_DIR}")
            return
        
        # Ищем все .for_vector.json файлы рекурсивно
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
    
    def get_stats(self) -> Dict:
        """Вернуть статистику по загруженным данным"""
        if not self._is_loaded:
            self.load_all_data()
        
        return {
            "total_documents": len(self.documents),
            "total_blocks": len(self.all_blocks),
            "loaded_at": self.loaded_at.isoformat() if self.loaded_at else None,
            "sag_final_dir": str(config.SAG_FINAL_DIR)
        }


# Глобальный инстанс (синглтон)
data_loader = DataLoader()



