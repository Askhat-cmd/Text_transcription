# 🚀 Начало реализации Phase 2 в Cursor IDE

## Обзор Phase 2

**Phase 2** добавляет осознание SAG v2.0 структуры:

- Учет уровня пользователя (beginner/intermediate/advanced)
- Использование граф-сущностей (`graph_entities`)
- Встраивание семантических отношений в ответ
- Адаптация глубины ответа
- Метаинформация о концептах

**Результат:** Ответы становятся умнее и адаптивнее.

***

## Шаг 1: Расширение `data_loader.py`

Обнови файл `bot_agent/data_loader.py` — добавь поддержку новых полей SAG v2.0:

```python
# bot_agent/data_loader.py (добавить в Block класс)

from typing import List, Dict

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
    document_title: str
    
    # === НОВЫЕ ПОЛЯ SAG v2.0 ===
    block_type: str = None          # monologue, dialogue, practice, theory
    emotional_tone: str = None      # contemplative, explanatory, intense, light
    conceptual_depth: str = None    # low, medium, high
    complexity_score: float = None  # 1.0-10.0
    graph_entities: List[str] = None  # до 30 сущностей
    
    def __post_init__(self):
        """Инициализация опциональных полей"""
        if self.graph_entities is None:
            self.graph_entities = []
    
    def get_preview(self, max_len: int = 200) -> str:
        """Вернуть краткое содержание"""
        text = self.content[:max_len] if len(self.content) > max_len else self.content
        return text + "..." if len(self.content) > max_len else text


# Обнови _load_single_document в DataLoader:
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
            document_title=document_title,
            # === НОВЫЕ ПОЛЯ ===
            block_type=block_data.get("block_type", "theory"),
            emotional_tone=block_data.get("emotional_tone", "explanatory"),
            conceptual_depth=block_data.get("conceptual_depth", "medium"),
            complexity_score=float(block_data.get("complexity_score", 5.0)),
            graph_entities=block_data.get("graph_entities", [])
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
```


***

## Шаг 2: Создание `bot_agent/user_level_adapter.py`

Новый модуль для адаптации ответов под уровень пользователя:

```python
# bot_agent/user_level_adapter.py

import logging
from typing import List, Optional
from enum import Enum

from data_loader import Block

logger = logging.getLogger(__name__)


class UserLevel(Enum):
    """Уровни подготовки пользователя"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class UserLevelAdapter:
    """
    Адаптирует ответы и выбор блоков в зависимости от уровня пользователя.
    """
    
    def __init__(self, user_level: str = "beginner"):
        try:
            self.level = UserLevel(user_level.lower())
        except ValueError:
            logger.warning(f"⚠️ Неизвестный уровень {user_level}, используем beginner")
            self.level = UserLevel.BEGINNER
    
    def filter_blocks_by_level(self, blocks: List[Block]) -> List[Block]:
        """
        Отфильтровать блоки по сложности в зависимости от уровня.
        """
        if self.level == UserLevel.BEGINNER:
            # Для начинающих: простые, низкая сложность, низкая глубина
            filtered = [
                b for b in blocks
                if b.complexity_score <= 5.0
                and b.conceptual_depth in ["low", "medium"]
                and b.block_type in ["theory", "practice"]
            ]
            logger.debug(f"🎯 BEGINNER: отфильтровано {len(filtered)}/{len(blocks)} блоков")
            return filtered if filtered else blocks[:3]  # fallback
        
        elif self.level == UserLevel.INTERMEDIATE:
            # Для промежуточных: средняя сложность, диалоги и практики
            filtered = [
                b for b in blocks
                if b.complexity_score <= 7.5
                and b.conceptual_depth in ["medium", "high"]
            ]
            logger.debug(f"🎯 INTERMEDIATE: отфильтровано {len(filtered)}/{len(blocks)} блоков")
            return filtered if filtered else blocks[:5]
        
        else:  # ADVANCED
            # Для продвинутых: всё, включая сложное
            logger.debug(f"🎯 ADVANCED: используем все {len(blocks)} блоков")
            return blocks
    
    def adapt_system_prompt(self, base_prompt: str) -> str:
        """
        Адаптировать системный промпт под уровень.
        """
        if self.level == UserLevel.BEGINNER:
            addition = """
ДОПОЛНИТЕЛЬНО ДЛЯ BEGINNER:
- Избегай сложной терминологии, объясняй простыми словами.
- Используй аналогии из повседневной жизни.
- Сосредоточься на практическом применении, а не теории.
- Предлагай конкретные шаги, которые пользователь может начать прямо сейчас."""
        
        elif self.level == UserLevel.INTERMEDIATE:
            addition = """
ДОПОЛНИТЕЛЬНО ДЛЯ INTERMEDIATE:
- Используй правильную терминологию, но объясняй новые термины.
- Показывай связи между концептами.
- Балансируй между теорией и практикой."""
        
        else:  # ADVANCED
            addition = """
ДОПОЛНИТЕЛЬНО ДЛЯ ADVANCED:
- Можешь использовать сложную терминологию и концепции.
- Углубляйся в философские и теоретические основы.
- Показывай взаимосвязи на уровне всей системы учения."""
        
        return base_prompt + addition
    
    def extract_key_concepts(self, blocks: List[Block]) -> List[str]:
        """
        Извлечь ключевые концепты из блоков.
        """
        concepts_freq = {}
        
        for block in blocks:
            for entity in block.graph_entities:
                concepts_freq[entity] = concepts_freq.get(entity, 0) + 1
        
        # Сортируем по частоте
        sorted_concepts = sorted(
            concepts_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Возвращаем top концепты в зависимости от уровня
        if self.level == UserLevel.BEGINNER:
            return [c[0] for c in sorted_concepts[:3]]
        elif self.level == UserLevel.INTERMEDIATE:
            return [c[0] for c in sorted_concepts[:5]]
        else:  # ADVANCED
            return [c[0] for c in sorted_concepts[:10]]
    
    def get_answer_length_guidance(self) -> str:
        """
        Подсказка для LLM о длине ответа.
        """
        if self.level == UserLevel.BEGINNER:
            return "Напиши краткий ответ (2-3 абзаца). Избегай излишних деталей."
        elif self.level == UserLevel.INTERMEDIATE:
            return "Напиши подробный ответ (4-5 абзацев) с примерами."
        else:  # ADVANCED
            return "Напиши развернутый ответ (6+ абзацев) со всеми деталями и связями."
    
    def format_concepts_for_output(self, concepts: List[str]) -> str:
        """
        Форматирование концептов для включения в ответ.
        """
        if not concepts:
            return ""
        
        if self.level == UserLevel.BEGINNER:
            return f"\n\n🔑 **Ключевые термины:** {', '.join(concepts)}"
        
        elif self.level == UserLevel.INTERMEDIATE:
            return f"\n\n🔑 **Задействованные концепты:** {', '.join(concepts)}"
        
        else:  # ADVANCED
            return f"\n\n🧠 **Концептуальная основа:** {', '.join(concepts)}"
```


***

## Шаг 3: Создание `bot_agent/semantic_analyzer.py`

Модуль для анализа семантических отношений:

```python
# bot_agent/semantic_analyzer.py

import logging
from typing import List, Dict
from collections import defaultdict

from data_loader import Block

logger = logging.getLogger(__name__)


class SemanticAnalyzer:
    """
    Анализирует семантические отношения между концептами в найденных блоках.
    """
    
    def analyze_relations(self, blocks: List[Block]) -> Dict:
        """
        Анализирует и возвращает структурированные отношения.
        
        Возвращает:
            {
                "primary_concepts": List[str],
                "related_concepts": Dict[str, List[str]],
                "conceptual_links": List[Dict],
                "analysis_summary": str
            }
        """
        # Собираем все концепты и их частоту
        concept_freq = defaultdict(int)
        block_concepts = []
        
        for block in blocks:
            block_concepts.append({
                "block_id": block.block_id,
                "entities": block.graph_entities,
                "depth": block.conceptual_depth
            })
            for entity in block.graph_entities:
                concept_freq[entity] += 1
        
        # Основные концепты (с наибольшей частотой)
        primary_concepts = sorted(
            concept_freq.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        primary_concept_names = [c[0] for c in primary_concepts]
        
        # Анализируем связи между концептами через блоки
        related_concepts = self._find_related_concepts(
            block_concepts,
            primary_concept_names
        )
        
        # Формируем отношения
        conceptual_links = self._extract_conceptual_links(
            blocks,
            primary_concept_names
        )
        
        analysis_summary = self._generate_analysis_summary(
            primary_concept_names,
            len(blocks),
            concept_freq
        )
        
        return {
            "primary_concepts": primary_concept_names,
            "related_concepts": related_concepts,
            "conceptual_links": conceptual_links,
            "analysis_summary": analysis_summary
        }
    
    def _find_related_concepts(
        self,
        block_concepts: List[Dict],
        primary_concepts: List[str]
    ) -> Dict[str, List[str]]:
        """
        Находит концепты, связанные с основными.
        """
        related = {}
        
        for primary in primary_concepts:
            related_set = set()
            
            for block_data in block_concepts:
                if primary in block_data["entities"]:
                    # Добавляем все остальные концепты из этого блока
                    for other in block_data["entities"]:
                        if other != primary:
                            related_set.add(other)
            
            related[primary] = list(related_set)[:5]  # топ 5 связанных
        
        return related
    
    def _extract_conceptual_links(
        self,
        blocks: List[Block],
        primary_concepts: List[str]
    ) -> List[Dict]:
        """
        Извлекает связи между концептами.
        """
        links = []
        
        for block in blocks:
            # Ищем блоки, содержащие несколько основных концептов
            main_in_block = [c for c in primary_concepts if c in block.graph_entities]
            
            if len(main_in_block) >= 2:
                for i, concept1 in enumerate(main_in_block):
                    for concept2 in main_in_block[i+1:]:
                        links.append({
                            "from": concept1,
                            "to": concept2,
                            "type": "co-occurs",
                            "source_block": block.block_id,
                            "context": block.title
                        })
        
        return links[:10]  # ограничиваем количество ссылок
    
    def _generate_analysis_summary(
        self,
        primary_concepts: List[str],
        block_count: int,
        concept_freq: Dict[str, int]
    ) -> str:
        """
        Генерирует текстовое резюме анализа.
        """
        if not primary_concepts:
            return "Анализ не выполнен."
        
        freq_str = " → ".join(primary_concepts)
        avg_complexity = sum(concept_freq.values()) / len(concept_freq) if concept_freq else 0
        
        return f"Найдено {block_count} релевантных блоков. Основные темы: {freq_str}."
```


***

## Шаг 4: Создание `bot_agent/answer_sag_aware.py`

Новая функция для ответов с учетом SAG v2.0:

```python
# bot_agent/answer_sag_aware.py

import logging
from typing import Dict, Optional
from datetime import datetime

from data_loader import data_loader, Block
from retriever import get_retriever
from llm_answerer import LLMAnswerer
from user_level_adapter import UserLevelAdapter, UserLevel
from semantic_analyzer import SemanticAnalyzer
from config import config

logger = logging.getLogger(__name__)


def answer_question_sag_aware(
    query: str,
    user_level: str = "beginner",
    top_k: Optional[int] = None,
    debug: bool = False
) -> Dict:
    """
    Phase 2: QA с использованием SAG v2.0 структуры.
    
    Аргументы:
        query (str): Вопрос пользователя.
        user_level (str): Уровень пользователя (beginner/intermediate/advanced).
        top_k (int, optional): Количество блоков.
        debug (bool): Возвращать ли отладочную информацию.
    
    Возвращает:
        Dict с расширенными полями:
            - "status": "success" | "error" | "partial"
            - "answer": str
            - "sources": List[Dict]
            - "concepts": List[str] — задействованные концепты
            - "relations": List[Dict] — важные связи между концептами
            - "user_level": str
            - "metadata": Dict — дополнительная информация
            - "debug": Optional[Dict]
    """
    
    logger.info(f"📋 Обработка запроса (Phase 2): '{query}' [Level: {user_level}]")
    
    top_k = top_k or config.TOP_K_BLOCKS
    start_time = datetime.now()
    debug_info = {} if debug else None
    
    try:
        # === ЭТАП 1: Инициализация компонентов ===
        logger.debug("🔧 Этап 1: Инициализация компонентов...")
        
        data_loader.load_all_data()
        level_adapter = UserLevelAdapter(user_level)
        semantic_analyzer = SemanticAnalyzer()
        
        if debug_info is not None:
            debug_info["user_level"] = user_level
        
        # === ЭТАП 2: Поиск блоков ===
        logger.debug("🔍 Этап 2: Поиск релевантных блоков...")
        retriever = get_retriever(use_chromadb=False)
        retrieved_blocks = retriever.retrieve(query, top_k=top_k)
        
        if not retrieved_blocks:
            return {
                "status": "partial",
                "answer": "К сожалению, я не нашел релевантного материала.",
                "sources": [],
                "concepts": [],
                "relations": [],
                "user_level": user_level,
                "metadata": {},
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
                "debug": debug_info
            }
        
        blocks = [block for block, score in retrieved_blocks]
        
        # === ЭТАП 3: Адаптация по уровню ===
        logger.debug("🎯 Этап 3: Адаптация по уровню пользователя...")
        adapted_blocks = level_adapter.filter_blocks_by_level(blocks)
        
        # === ЭТАП 4: Семантический анализ ===
        logger.debug("🧠 Этап 4: Семантический анализ...")
        semantic_data = semantic_analyzer.analyze_relations(adapted_blocks)
        
        if debug_info is not None:
            debug_info["semantic_analysis"] = {
                "primary_concepts": semantic_data["primary_concepts"],
                "relations_found": len(semantic_data["conceptual_links"])
            }
        
        # === ЭТАП 5: Формирование ответа через LLM ===
        logger.debug("🤖 Этап 5: Формирование ответа...")
        
        answerer = LLMAnswerer()
        base_system_prompt = answerer.build_system_prompt()
        adapted_system_prompt = level_adapter.adapt_system_prompt(base_system_prompt)
        length_guidance = level_adapter.get_answer_length_guidance()
        
        # Расширенный контекст с семантическими отношениями
        context = answerer.build_context_prompt(adapted_blocks, query)
        context += f"\n\n{length_guidance}"
        
        if semantic_data["primary_concepts"]:
            context += f"\n\n🔑 Основные концепты для этого ответа: {', '.join(semantic_data['primary_concepts'])}"
        
        llm_result = answerer.generate_answer(
            query,
            adapted_blocks,
            model=config.LLM_MODEL,
            temperature=config.LLM_TEMPERATURE,
            max_tokens=config.LLM_MAX_TOKENS
        )
        
        if llm_result.get("error"):
            logger.error(f"❌ Ошибка LLM: {llm_result['error']}")
            return {
                "status": "error",
                "answer": llm_result.get("answer"),
                "sources": [],
                "concepts": semantic_data["primary_concepts"],
                "relations": [],
                "user_level": user_level,
                "metadata": {"error": llm_result.get("error")},
                "timestamp": datetime.now().isoformat(),
                "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
                "debug": debug_info
            }
        
        # === ЭТАП 6: Форматирование вывода ===
        logger.debug("📝 Этап 6: Форматирование вывода...")
        
        answer = llm_result["answer"]
        
        # Добавляем концепты в конец ответа
        concepts_section = level_adapter.format_concepts_for_output(
            semantic_data["primary_concepts"]
        )
        if concepts_section:
            answer += concepts_section
        
        # Формируем источники
        sources = [
            {
                "block_id": b.block_id,
                "title": b.title,
                "summary": b.summary,
                "document_title": b.document_title,
                "youtube_link": b.youtube_link,
                "start": b.start,
                "end": b.end,
                "video_id": b.video_id,
                # SAG v2.0 поля
                "block_type": b.block_type,
                "emotional_tone": b.emotional_tone,
                "complexity_score": b.complexity_score,
                "conceptual_depth": b.conceptual_depth
            }
            for b in adapted_blocks
        ]
        
        elapsed_time = (datetime.now() - start_time).total_seconds()
        
        result = {
            "status": "success",
            "answer": answer,
            "sources": sources,
            "concepts": semantic_data["primary_concepts"],
            "relations": semantic_data["conceptual_links"],
            "user_level": user_level,
            "metadata": {
                "analysis_summary": semantic_data["analysis_summary"],
                "blocks_used": len(adapted_blocks),
                "semantic_links": len(semantic_data["conceptual_links"])
            },
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": round(elapsed_time, 2)
        }
        
        if debug_info is not None:
            debug_info["total_time"] = elapsed_time
            result["debug"] = debug_info
        
        logger.info(f"✅ Запрос обработан за {elapsed_time:.2f}с (Level: {user_level})")
        
        return result
    
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}", exc_info=True)
        return {
            "status": "error",
            "answer": f"Произошла ошибка: {str(e)}",
            "sources": [],
            "concepts": [],
            "relations": [],
            "user_level": user_level,
            "metadata": {"error": str(e)},
            "timestamp": datetime.now().isoformat(),
            "processing_time_seconds": (datetime.now() - start_time).total_seconds(),
            "debug": debug_info
        }
```


***

## Шаг 5: Обновить `bot_agent/__init__.py`

```python
# bot_agent/__init__.py

import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

LOG_DIR = Path(__file__).parent.parent / "logs" / "bot_agent"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "bot_agent.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("bot_agent")

# Phase 1
from answer_basic import answer_question_basic, ask

# Phase 2
from answer_sag_aware import answer_question_sag_aware

__all__ = [
    "answer_question_basic",
    "ask",
    "answer_question_sag_aware"
]

logger.info("🚀 Bot Agent инициализирован (Phase 1 + Phase 2)")
```


***

## Шаг 6: Создание тестового скрипта `test_phase2.py`

```python
# test_phase2.py
"""
Тестирование Phase 2 - SAG v2.0 aware ответы
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "bot_agent"))

from answer_sag_aware import answer_question_sag_aware

print("=" * 80)
print("🧪 ТЕСТИРОВАНИЕ PHASE 2 - SAG v2.0 AWARE QA БОТ")
print("=" * 80)

# Тестовые комбинации (вопрос, уровень)
test_cases = [
    ("Что такое осознавание?", "beginner"),
    ("Как работает разотождествление?", "intermediate"),
    ("Как связаны паттерны с сознанием?", "advanced"),
    ("Какие практики развивают осознавание?", "beginner"),
]

for i, (query, level) in enumerate(test_cases, 1):
    print(f"\n{'='*80}")
    print(f"ТЕСТ {i}/{len(test_cases)}")
    print(f"{'='*80}")
    print(f"\n📋 Вопрос: {query}")
    print(f"📊 Уровень: {level}\n")
    
    try:
        result = answer_question_sag_aware(query, user_level=level, debug=True)
        
        print(f"Status: {result['status']}")
        print(f"Processing time: {result['processing_time_seconds']}s")
        print(f"User level: {result['user_level']}")
        print(f"Blocks used: {result['metadata']['blocks_used']}")
        
        print(f"\n💬 ОТВЕТ:\n{result['answer']}")
        
        if result.get('concepts'):
            print(f"\n🔑 КОНЦЕПТЫ ({len(result['concepts'])}):")
            for concept in result['concepts']:
                print(f"  • {concept}")
        
        if result.get('relations'):
            print(f"\n🔗 СВЯЗИ ({len(result['relations'])}):")
            for rel in result['relations'][:3]:
                print(f"  • {rel['from']} → {rel['to']} ({rel['type']})")
        
        if result.get('sources'):
            print(f"\n📚 ИСТОЧНИКИ ({len(result['sources'])} блоков):")
            for src in result['sources'][:2]:
                print(f"  • {src['title']} (сложность: {src['complexity_score']}, тип: {src['block_type']})")
                print(f"    {src['youtube_link']}\n")
        
        if result.get('debug'):
            print(f"\n🔧 DEBUG: {result['debug']}")
    
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "=" * 80)
print("✅ ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
print("=" * 80)
```


***

## Шаг 7: Запуск Phase 2

```bash
# Убедись, что Phase 1 работает
python test_phase1.py

# Запусти Phase 2
python test_phase2.py
```


***

## 🎯 Чек-лист Phase 2

- [ ] Обновлен `data_loader.py` с полями SAG v2.0
- [ ] Создан `user_level_adapter.py`
- [ ] Создан `semantic_analyzer.py`
- [ ] Создан `answer_sag_aware.py`
- [ ] Обновлен `__init__.py`
- [ ] Создан `test_phase2.py`
- [ ] Все тесты проходят успешно
- [ ] Ответы адаптируются под уровень пользователя
- [ ] Концепты правильно извлекаются и отображаются

***

## ✅ Результат Phase 2

✅ Ответы адаптируются под уровень (beginner/intermediate/advanced)
✅ Включаются концепты и их связи
✅ Блоки фильтруются по сложности
✅ Система промптов адаптируется
✅ Возвращается семантический анализ

**Следующий шаг:** Phase 3 — Knowledge Graph 🧠

