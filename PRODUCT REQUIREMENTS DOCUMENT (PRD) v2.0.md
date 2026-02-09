# 📋 PRODUCT REQUIREMENTS DOCUMENT (PRD) v2.0

## Внедрение умной памяти и Voyage AI в психологический бот

**Версия:** 2.0 (полная переработка с персистентностью)
**Дата:** 08.02.2026
**Проект:** voice_bot_pipeline / Психологический AI-бот
**Для:** Cursor AI IDE Agent

***

## 🎯 EXECUTIVE SUMMARY

### Цель проекта

Создать **процессного психологического AI-бота**, который:

- **НЕ** отвечает на каждое сообщение как FAQ
- **НЕ** работает как "умный советчик"
- **Сопровождает процесс мышления** человека
- Работает в **6 адаптивных режимах** с правильным ритмом
- Использует **гибридный поиск** (локальные embeddings + Voyage AI)
- Управляет поведением через **confidence scoring**
- Имеет **структурированную память** (short-term, semantic, working state, summary)
- **Сохраняет состояние каждого клиента** в персистентное хранилище


### Ключевая концепция

> **"Бот не отвечает на сообщения. Он сопровождает процесс мышления человека."**

***

## 🏗️ АРХИТЕКТУРА РЕШЕНИЯ

### Философия системы

```
ПОИСК ≠ ВЫБОР ≠ ОТВЕТ

Поиск   → математический, быстрый, локальный (ChromaDB)
Выбор   → семантический, смысловой (Voyage AI)
Ответ   → простой, человеческий (LLM с режимными промптами)
```


### Текущее состояние проекта

**Что уже есть:**

- ✅ ChromaDB + Sentence-Transformers
- ✅ SAG v2.0 обработка (442 узла + 259 связей)
- ✅ Система экстракторов знаний
- ✅ Профессиональная структура

**Что добавляем:**

- 🆕 Voyage AI re-ranking
- 🆕 Психологический бот с 6 режимами
- 🆕 Decision Layer с полной таблицей правил
- 🆕 Hybrid Query Builder (вопрос = якорь)
- 🆕 Confidence Scoring System (управление поведением)
- 🆕 Semantic Memory (поиск релевантных прошлых обменов)
- 🆕 Stage Awareness Filter
- 🆕 **SessionManager (персистентное хранилище для каждого клиента)**

***

## 📁 СТРУКТУРА ФАЙЛОВ

```
voice_bot_pipeline/
├── bot_psychologist/                    # 🆕 НОВЫЙ МОДУЛЬ
│   ├── __init__.py
│   ├── bot_core.py                      # Главный класс
│   │
│   ├── memory/                          # Система памяти
│   │   ├── __init__.py
│   │   ├── conversation_memory.py       # История диалога (адаптивная глубина)
│   │   ├── semantic_memory.py           # Семантический поиск прошлых обменов
│   │   ├── working_state.py             # Рабочее состояние (emotion, defense, phase)
│   │   └── summary_manager.py           # Резюме беседы
│   │
│   ├── storage/                         # 🆕 ПЕРСИСТЕНТНОСТЬ
│   │   ├── __init__.py
│   │   ├── session_manager.py           # SessionManager класс (SQLite)
│   │   └── migrations/                  # Миграции схемы БД
│   │
│   ├── decision/                        # Decision Layer
│   │   ├── __init__.py
│   │   ├── decision_gate.py             # Главный роутер режимов
│   │   ├── decision_table.py            # 🔥 ТАБЛИЦА ПРАВИЛ (10+ правил)
│   │   ├── signal_detector.py           # Детекторы сигналов (intervention, validation)
│   │   └── mode_handlers.py             # Обработчики для каждого режима
│   │
│   ├── retrieval/                       # Поиск и ранжирование
│   │   ├── __init__.py
│   │   ├── hybrid_query_builder.py      # 🔥 ГИБРИДНЫЙ ЗАПРОС (вопрос = якорь)
│   │   ├── local_search.py              # Локальный векторный поиск (ChromaDB)
│   │   ├── voyage_reranker.py           # Voyage AI re-ranking
│   │   ├── confidence_scorer.py         # 🔥 Расчет уверенности (управление поведением)
│   │   └── stage_filter.py              # 🔥 Фильтр по стадиям пользователя
│   │
│   ├── response/                        # Генерация ответов
│   │   ├── __init__.py
│   │   ├── response_generator.py        # LLM-генерация
│   │   ├── prompt_templates.py          # 🔥 АДАПТИВНЫЕ ПРОМПТЫ (6 режимов)
│   │   └── response_formatter.py        # Форматирование ответов
│   │
│   └── config/
│       ├── bot_config.yaml              # Основные настройки
│       ├── modes_config.yaml            # Конфигурация режимов
│       └── decision_rules.yaml          # 🔥 ПРАВИЛА МАРШРУТИЗАЦИИ
│
├── config/
│   └── config.yaml                      # Расширить
│
├── .env                                 # Расширить
│
├── data/
│   └── bot_sessions.db                  # 🆕 SQLite база сессий
│
├── scripts/
│   ├── setup_bot.ps1
│   ├── test_bot_dialogue.py             # Полный тест 7-ходового диалога
│   └── cleanup_old_sessions.py          # 🆕 Автоочистка старых сессий
│
└── tests/
    └── bot_psychologist/
        ├── test_memory.py
        ├── test_session_manager.py      # 🆕 Тесты персистентности
        ├── test_decision_table.py       # 🔥 Тесты таблицы правил
        ├── test_hybrid_query.py         # 🔥 Тесты гибридного запроса
        ├── test_confidence_scorer.py
        ├── test_semantic_memory.py      # 🔥 Тесты семантической памяти
        └── test_full_dialogue.py
```


***

## 📝 ДЕТАЛЬНЫЕ СПЕЦИФИКАЦИИ

### 1. CONVERSATION MEMORY (адаптивная глубина)

**Файл:** `bot_psychologist/memory/conversation_memory.py`

```python
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from datetime import datetime

@dataclass
class ConversationTurn:
    """Один ход диалога"""
    turn_number: int
    user_input: str
    bot_response: str
    timestamp: datetime
    mode: str  # PRESENCE, INTERVENTION, etc.
    working_state: Optional[Dict] = None
    chunks_used: List[str] = field(default_factory=list)
    confidence: Optional[float] = None
    reasoning: Optional[str] = None  # Почему выбран этот режим

class ConversationMemory:
    """
    Управление памятью с адаптивной глубиной
    
    Ключевой принцип: разные режимы = разная глубина контекста
    """
    
    def __init__(self, config: Dict):
        self.turns: List[ConversationTurn] = []
        self.summary: str = ""
        self.config = config
        
    def add_turn(self, turn: ConversationTurn):
        """Добавить ход и обновить summary при необходимости"""
        self.turns.append(turn)
        
        # Обновлять summary каждые N ходов
        if len(self.turns) % self.config['summary_update_interval'] == 0:
            self._update_summary()
    
    def get_context(
        self, 
        mode: str, 
        max_chars: Optional[int] = None
    ) -> str:
        """
        Получить контекст для режима
        
        ВАЖНО: Разная глубина для разных режимов!
        
        Глубины:
        - PRESENCE: 5 ходов (легкий режим)
        - CLARIFICATION: 5 ходов
        - VALIDATION: 5 ходов
        - THINKING: 10 ходов (нужен контекст)
        - INTERVENTION: 20 ходов (максимальный контекст)
        - INTEGRATION: 10 ходов
        """
        depth = self.config['context_depths'][mode]
        recent_turns = self.turns[-depth:]
        
        # Форматирование
        context_parts = []
        for turn in recent_turns:
            context_parts.append(
                f"[Ход {turn.turn_number}]\n"
                f"Пользователь: {turn.user_input}\n"
                f"Бот: {turn.bot_response}\n"
            )
        
        context = "\n".join(context_parts)
        
        # Обрезать по max_chars если указано
        if max_chars and len(context) > max_chars:
            context = context[-max_chars:]
        
        return context
    
    def get_last_intervention_turn(self) -> Optional[int]:
        """Найти номер последнего INTERVENTION хода"""
        for turn in reversed(self.turns):
            if turn.mode == "INTERVENTION":
                return turn.turn_number
        return None
    
    def _update_summary(self):
        """Обновить резюме через LLM (см. SummaryManager)"""
        pass
```

**Настройки в config.yaml:**

```yaml
bot_psychologist:
  memory:
    context_depths:
      PRESENCE: 5
      CLARIFICATION: 5
      VALIDATION: 5
      THINKING: 10
      INTERVENTION: 20
      INTEGRATION: 10
    summary_update_interval: 5
    summary_max_length: 500
    max_total_turns: 1000  # Максимум ходов в памяти
```


***

### 2. SEMANTIC MEMORY (поиск релевантных прошлых обменов)

**Файл:** `bot_psychologist/memory/semantic_memory.py`

```python
from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Tuple

class SemanticMemory:
    """
    Семантический поиск по прошлым обменам диалога
    
    Концепция: не только последние N ходов, но и РЕЛЕВАНТНЫЕ прошлые обмены
    """
    
    def __init__(self, model_name: str = "intfloat/multilingual-e5-large"):
        self.model = SentenceTransformer(model_name)
        self.embeddings_cache: List[np.ndarray] = []
        self.turns_cache: List[ConversationTurn] = []
    
    def add_turn(self, turn: ConversationTurn):
        """Добавить ход и векторизовать его"""
        # Объединяем user + bot для семантики
        combined_text = f"{turn.user_input} {turn.bot_response}"
        embedding = self.model.encode(combined_text)
        
        self.embeddings_cache.append(embedding)
        self.turns_cache.append(turn)
    
    def search_relevant_turns(
        self,
        current_message: str,
        top_k: int = 3,
        min_similarity: float = 0.7
    ) -> List[Tuple[ConversationTurn, float]]:
        """
        Найти релевантные прошлые обмены
        
        Args:
            current_message: Текущее сообщение пользователя
            top_k: Сколько вернуть
            min_similarity: Минимальная косинусная близость
            
        Returns:
            [(turn, similarity_score), ...]
        """
        if not self.embeddings_cache:
            return []
        
        # Векторизовать запрос
        query_embedding = self.model.encode(current_message)
        
        # Косинусное сходство
        similarities = []
        for i, emb in enumerate(self.embeddings_cache):
            sim = np.dot(query_embedding, emb) / (
                np.linalg.norm(query_embedding) * np.linalg.norm(emb)
            )
            if sim >= min_similarity:
                similarities.append((self.turns_cache[i], float(sim)))
        
        # Сортировка и top-K
        similarities.sort(key=lambda x: x[^1], reverse=True)
        return similarities[:top_k]
    
    def format_semantic_context(
        self,
        relevant_turns: List[Tuple[ConversationTurn, float]]
    ) -> str:
        """Форматировать найденные обмены для контекста"""
        if not relevant_turns:
            return ""
        
        parts = ["=== Релевантные прошлые обмены ===\n"]
        for turn, similarity in relevant_turns:
            parts.append(
                f"[Ход {turn.turn_number}, релевантность: {similarity:.2f}]\n"
                f"Пользователь: {turn.user_input}\n"
                f"Бот: {turn.bot_response}\n"
            )
        
        return "\n".join(parts)
```

**Настройки в .env:**

```env
# Semantic Memory
ENABLE_SEMANTIC_MEMORY=true
SEMANTIC_SEARCH_TOP_K=3
SEMANTIC_MIN_SIMILARITY=0.7
SEMANTIC_MAX_CHARS=1000
```


***

### 3. WORKING STATE (структурированное состояние)

**Файл:** `bot_psychologist/memory/working_state.py`

```python
from dataclasses import dataclass
from typing import Optional, Dict

@dataclass
class WorkingState:
    """
    Рабочее состояние пользователя
    
    Обновляется в режиме THINKING каждые N ходов
    """
    dominant_state: str  # "эмоциональное онемение", "тревога", "фрустрация"
    emotion: str         # "пустота", "страх", "злость", "вина"
    defense: Optional[str] = None  # "интеллектуализация", "проекция", "избегание"
    phase: str = "начало контакта"  # "начало", "осмысление", "работа", "интеграция"
    direction: str = "диагностика"  # "диагностика", "осмысление", "действие"
    
    # Метаданные
    last_updated_turn: int = 0
    confidence_level: str = "low"  # low/medium/high
    
    def to_dict(self) -> Dict:
        return {
            "dominant_state": self.dominant_state,
            "emotion": self.emotion,
            "defense": self.defense,
            "phase": self.phase,
            "direction": self.direction,
            "last_updated_turn": self.last_updated_turn,
            "confidence_level": self.confidence_level
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "WorkingState":
        return cls(**data)
    
    def get_user_stage(self) -> str:
        """
        Определить стадию пользователя для Stage Filter
        
        Стадии (по возрастанию глубины):
        1. "surface" - поверхностный контакт
        2. "awareness" - осознавание
        3. "exploration" - исследование
        4. "integration" - интеграция
        """
        stage_map = {
            "начало контакта": "surface",
            "осмысление": "awareness",
            "работа": "exploration",
            "интеграция": "integration"
        }
        return stage_map.get(self.phase, "surface")
```


***

### 🆕 4. SESSION MANAGER (Персистентность памяти)

**Файл:** `bot_psychologist/storage/session_manager.py`

**Назначение:** Сохранение и загрузка памяти каждого клиента в SQLite базе данных

**Проблема:** Без персистентности вся память теряется после перезапуска бота

**Решение:** SQLite база с 3 таблицами:

- `sessions` — метаданные сессий (session_id, user_id, working_state, summary)
- `conversation_turns` — все ходы диалога
- `semantic_embeddings` — векторные представления ходов (для semantic memory)


#### Структура БД

```sql
-- Таблица сессий
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,  -- telegram_id, phone, email
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_active TIMESTAMP,
    status TEXT DEFAULT 'active',  -- active/archived/deleted
    
    -- Сериализованные данные
    working_state TEXT,  -- JSON
    conversation_summary TEXT,
    metadata TEXT,  -- JSON
    
    INDEX idx_user_id (user_id),
    INDEX idx_last_active (last_active)
);

-- Таблица ходов диалога
CREATE TABLE conversation_turns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    user_input TEXT NOT NULL,
    bot_response TEXT NOT NULL,
    mode TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confidence REAL,
    chunks_used TEXT,  -- JSON
    reasoning TEXT,
    
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    INDEX idx_session (session_id)
);

-- Таблица эмбеддингов (для semantic memory)
CREATE TABLE semantic_embeddings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    embedding BLOB,  -- numpy array в pickle
    
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    INDEX idx_session (session_id)
);
```


#### Класс SessionManager

```python
import sqlite3
import json
import pickle
import numpy as np
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from pathlib import Path

class SessionManager:
    """
    Управление сессиями клиентов
    
    Функции:
    - Создание/загрузка сессии
    - Сохранение ходов + эмбеддингов
    - Обновление working_state и summary
    - Архивация старых сессий
    - Удаление данных (GDPR compliance)
    """
    
    def __init__(self, db_path: str = "data/bot_sessions.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Создать таблицы если их нет"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            user_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'active',
            working_state TEXT,
            conversation_summary TEXT,
            metadata TEXT
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversation_turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_number INTEGER NOT NULL,
            user_input TEXT NOT NULL,
            bot_response TEXT NOT NULL,
            mode TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            confidence REAL,
            chunks_used TEXT,
            reasoning TEXT,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS semantic_embeddings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            turn_number INTEGER NOT NULL,
            embedding BLOB,
            FOREIGN KEY (session_id) REFERENCES sessions(session_id)
        )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_id ON sessions(user_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_session_turns ON conversation_turns(session_id)")
        
        conn.commit()
        conn.close()
    
    def create_session(self, session_id: str, user_id: Optional[str] = None) -> Dict:
        """Создать новую сессию"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute("""
        INSERT INTO sessions (session_id, user_id, created_at, last_active)
        VALUES (?, ?, ?, ?)
        """, (session_id, user_id, now, now))
        
        conn.commit()
        conn.close()
        
        return {"session_id": session_id, "user_id": user_id, "created_at": now}
    
    def load_session(self, session_id: str) -> Optional[Dict]:
        """
        Загрузить сессию со всей историей
        
        Returns:
            {
                "session_info": {...},
                "conversation_turns": [...],
                "semantic_embeddings": [...],
                "working_state": {...},
                "summary": "..."
            }
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Session info
        cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
        session_row = cursor.fetchone()
        
        if not session_row:
            conn.close()
            return None
        
        # Turns
        cursor.execute("""
        SELECT * FROM conversation_turns 
        WHERE session_id = ? 
        ORDER BY turn_number
        """, (session_id,))
        turns = [dict(row) for row in cursor.fetchall()]
        
        for turn in turns:
            if turn['chunks_used']:
                turn['chunks_used'] = json.loads(turn['chunks_used'])
        
        # Embeddings
        cursor.execute("""
        SELECT turn_number, embedding FROM semantic_embeddings
        WHERE session_id = ?
        ORDER BY turn_number
        """, (session_id,))
        embeddings = [
            {"turn_number": row[^0], "embedding": pickle.loads(row[^1])}
            for row in cursor.fetchall()
        ]
        
        conn.close()
        
        return {
            "session_info": dict(session_row),
            "conversation_turns": turns,
            "semantic_embeddings": embeddings,
            "working_state": json.loads(session_row['working_state']) 
                             if session_row['working_state'] else None,
            "summary": session_row['conversation_summary']
        }
    
    def save_turn(
        self,
        session_id: str,
        turn: ConversationTurn,
        embedding: Optional[np.ndarray] = None
    ):
        """Сохранить ход диалога"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO conversation_turns (
            session_id, turn_number, user_input, bot_response,
            mode, confidence, chunks_used, reasoning
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, turn.turn_number, turn.user_input, turn.bot_response,
            turn.mode, turn.confidence, json.dumps(turn.chunks_used), turn.reasoning
        ))
        
        if embedding is not None:
            cursor.execute("""
            INSERT INTO semantic_embeddings (session_id, turn_number, embedding)
            VALUES (?, ?, ?)
            """, (session_id, turn.turn_number, pickle.dumps(embedding)))
        
        cursor.execute("""
        UPDATE sessions SET last_active = ? WHERE session_id = ?
        """, (datetime.now().isoformat(), session_id))
        
        conn.commit()
        conn.close()
    
    def update_working_state(self, session_id: str, working_state: WorkingState):
        """Обновить рабочее состояние"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE sessions 
        SET working_state = ?, last_active = ?
        WHERE session_id = ?
        """, (json.dumps(working_state.to_dict()), datetime.now().isoformat(), session_id))
        
        conn.commit()
        conn.close()
    
    def update_summary(self, session_id: str, summary: str):
        """Обновить резюме беседы"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE sessions 
        SET conversation_summary = ?, last_active = ?
        WHERE session_id = ?
        """, (summary, datetime.now().isoformat(), session_id))
        
        conn.commit()
        conn.close()
    
    def archive_old_sessions(self, days: int = 90) -> int:
        """Архивировать неактивные сессии"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        cursor.execute("""
        UPDATE sessions 
        SET status = 'archived'
        WHERE last_active < ? AND status = 'active'
        """, (cutoff,))
        
        count = cursor.rowcount
        conn.commit()
        conn.close()
        return count
    
    def delete_session(self, session_id: str):
        """Полностью удалить сессию (GDPR)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM semantic_embeddings WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM conversation_turns WHERE session_id = ?", (session_id,))
        cursor.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        
        conn.commit()
        conn.close()
    
    def get_user_sessions(self, user_id: str) -> List[Dict]:
        """Получить все сессии пользователя"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
        SELECT session_id, created_at, last_active, status
        FROM sessions
        WHERE user_id = ?
        ORDER BY last_active DESC
        """, (user_id,))
        
        sessions = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return sessions
```


#### Интеграция с Bot Core

**Обновить `bot_psychologist/bot_core.py`:**

```python
class PsychologistBot:
    def __init__(self, config_path: str):
        # ... существующий код ...
        
        # 🆕 Добавить SessionManager
        self.session_manager = SessionManager(
            db_path=os.getenv("BOT_DB_PATH", "data/bot_sessions.db")
        )
        self.current_session_id = None
    
    def start_session(self, session_id: str, user_id: Optional[str] = None):
        """
        Начать новую сессию или загрузить существующую
        
        Args:
            session_id: UUID сессии (генерируется клиентом)
            user_id: ID пользователя (telegram_id, phone)
        """
        session_data = self.session_manager.load_session(session_id)
        
        if session_data:
            logging.info(f"Loading existing session: {session_id}")
            self._restore_from_session(session_data)
        else:
            logging.info(f"Creating new session: {session_id}")
            self.session_manager.create_session(session_id, user_id)
        
        self.current_session_id = session_id
    
    def _restore_from_session(self, session_data: Dict):
        """Восстановить состояние из сессии"""
        # Восстановить ходы
        for turn_data in session_data['conversation_turns']:
            turn = ConversationTurn(
                turn_number=turn_data['turn_number'],
                user_input=turn_data['user_input'],
                bot_response=turn_data['bot_response'],
                timestamp=datetime.fromisoformat(turn_data['timestamp']),
                mode=turn_data['mode'],
                chunks_used=turn_data['chunks_used'] or [],
                confidence=turn_data['confidence'],
                reasoning=turn_data['reasoning']
            )
            self.memory.turns.append(turn)
        
        # Восстановить эмбеддинги
        for emb_data in session_data['semantic_embeddings']:
            self.semantic_memory.embeddings_cache.append(emb_data['embedding'])
        
        # Восстановить состояние
        if session_data['working_state']:
            self.working_state = WorkingState.from_dict(session_data['working_state'])
        
        # Восстановить summary
        self.memory.summary = session_data['summary'] or ""
        
        # Восстановить turn_number
        if self.memory.turns:
            self.turn_number = self.memory.turns[-1].turn_number
    
    def process_message(self, user_message: str) -> str:
        """Обработать сообщение (с автосохранением)"""
        
        if not self.current_session_id:
            raise RuntimeError("Session not started! Call start_session() first")
        
        # ... весь существующий код process_message ...
        
        # 🆕 Сохранить ход в БД
        self.session_manager.save_turn(
            session_id=self.current_session_id,
            turn=turn,
            embedding=self.semantic_memory.embeddings_cache[-1] 
                      if self.semantic_memory.embeddings_cache else None
        )
        
        # 🆕 Сохранить состояние если обновилось
        if mode == "THINKING":
            self.session_manager.update_working_state(
                self.current_session_id, self.working_state
            )
        
        # 🆕 Сохранить summary если обновился
        if len(self.memory.turns) % self.config['memory']['summary_update_interval'] == 0:
            self.session_manager.update_summary(
                self.current_session_id, self.memory.summary
            )
        
        return bot_response
```


#### Настройки

**`.env`:**

```env
# Storage
BOT_DB_PATH=data/bot_sessions.db
SESSION_RETENTION_DAYS=90
ARCHIVE_RETENTION_DAYS=365
AUTO_CLEANUP_ENABLED=true
```

**`config.yaml`:**

```yaml
bot_psychologist:
  storage:
    db_path: "data/bot_sessions.db"
    retention:
      active_days: 90       # Active → Archived после 90 дней неактивности
      archive_days: 365     # Archived → Deleted после 365 дней
      delete_after_days: 455  # Полное удаление
    cleanup:
      enabled: true
      run_daily: true
      time: "03:00"  # 3 AM
```


#### Пример использования (Telegram Bot)

```python
from uuid import uuid4

# Начало беседы
@bot.message_handler(commands=['start'])
def start_conversation(message):
    telegram_id = str(message.from_user.id)
    
    # Проверить активные сессии
    sessions = bot_manager.session_manager.get_user_sessions(telegram_id)
    active = [s for s in sessions if s['status'] == 'active']
    
    if active:
        session_id = active[^0]['session_id']
        bot.reply_to(message, "Продолжаем беседу...")
    else:
        session_id = str(uuid4())
        bot.reply_to(message, "Начинаем новую беседу...")
    
    bot_manager.start_session(session_id, user_id=telegram_id)
    user_sessions[telegram_id] = session_id

# Обработка сообщений
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    telegram_id = str(message.from_user.id)
    session_id = user_sessions.get(telegram_id)
    
    if not session_id:
        bot.reply_to(message, "Сначала /start")
        return
    
    response = bot_manager.process_message(message.text)
    bot.reply_to(message, response)
```


#### Автоматическая очистка (cron)

**`scripts/cleanup_old_sessions.py`:**

```python
from bot_psychologist.storage.session_manager import SessionManager
from datetime import datetime, timedelta
import sqlite3

def cleanup():
    manager = SessionManager()
    
    # Архивировать неактивные 90+ дней
    archived = manager.archive_old_sessions(days=90)
    print(f"Archived: {archived} sessions")
    
    # Удалить archived 365+ дней
    conn = sqlite3.connect(manager.db_path)
    cursor = conn.cursor()
    
    cutoff = (datetime.now() - timedelta(days=365)).isoformat()
    cursor.execute("""
    SELECT session_id FROM sessions 
    WHERE status = 'archived' AND last_active < ?
    """, (cutoff,))
    
    old = [row[^0] for row in cursor.fetchall()]
    conn.close()
    
    for sid in old:
        manager.delete_session(sid)
    
    print(f"Deleted: {len(old)} old sessions")

if __name__ == "__main__":
    cleanup()
```

**Запуск через cron:**

```bash
0 3 * * * cd /path/to/project && python scripts/cleanup_old_sessions.py
```


#### Политика хранения данных

**Время жизни:**

- **Active:** 90 дней активности
- **Archived:** ещё 365 дней
- **Total:** до 455 дней максимум
- **Автоочистка:** каждую ночь в 3:00

**GDPR Compliance:**

```python
@bot.message_handler(commands=['delete_my_data'])
def delete_user_data(message):
    telegram_id = str(message.from_user.id)
    
    # Получить все сессии
    sessions = bot_manager.session_manager.get_user_sessions(telegram_id)
    
    # Удалить каждую
    for session in sessions:
        bot_manager.session_manager.delete_session(session['session_id'])
    
    bot.reply_to(message, 
        f"Удалено {len(sessions)} сессий. "
        "Все ваши данные безвозвратно стерты."
    )
```


***

### 5. DECISION TABLE (🔥 КРИТИЧНО)

**Файл:** `bot_psychologist/decision/decision_table.py`

```python
from dataclasses import dataclass
from typing import List, Dict, Optional, Callable

@dataclass
class DecisionRule:
    """Одно правило маршрутизации"""
    rule_id: int
    conditions: Dict  # Условия
    route: str        # Режим (PRESENCE, INTERVENTION, etc.)
    forbid: List[str] # Запрещенные действия
    priority: int     # Приоритет (1 = highest)
    description: str

class DecisionTable:
    """
    Таблица правил маршрутизации
    
    ВАЖНО: Правила проверяются по приоритету (сверху вниз)
    Первое совпадение = побеждает
    """
    
    RULES = [
        # ===== ПРАВИЛО 1: Безопасность (highest priority) =====
        DecisionRule(
            rule_id=1,
            conditions={
                "confidence": {"max": 0.4}
            },
            route="CLARIFICATION",
            forbid=["explain", "advise", "interpret"],
            priority=1,
            description="При низкой уверенности — только прояснение"
        ),
        
        # ===== ПРАВИЛО 2: Противоречия =====
        DecisionRule(
            rule_id=2,
            conditions={
                "confidence": {"min": 0.4, "max": 0.55},
                "contradiction": True
            },
            route="CLARIFICATION",
            forbid=["advise", "deepen"],
            priority=2,
            description="Противоречия в словах — прояснить"
        ),
        
        # ===== ПРАВИЛО 3: Эмоциональная перегрузка =====
        DecisionRule(
            rule_id=3,
            conditions={
                "emotion_load": "high"
            },
            route="VALIDATION",
            forbid=["analyze", "deepen", "explain"],
            priority=3,
            description="Сильные эмоции — поддержка, не анализ"
        ),
        
        # ===== ПРАВИЛО 4: Повторяющаяся тема =====
        DecisionRule(
            rule_id=4,
            conditions={
                "confidence": {"min": 0.55},
                "repetition_count": {"min": 2}
            },
            route="CLARIFICATION",  # или INTERVENTION, если есть новый угол
            forbid=["repeat_same"],
            priority=4,
            description="Зацикливание — сменить угол"
        ),
        
        # ===== ПРАВИЛО 5: Прямой запрос на действие =====
        DecisionRule(
            rule_id=5,
            conditions={
                "confidence": {"min": 0.6},
                "explicit_ask": True,
                "ask_type": "action"
            },
            route="INTERVENTION",
            forbid=["philosophize"],
            priority=5,
            description="Прямой вопрос 'что делать' — интервенция"
        ),
        
        # ===== ПРАВИЛО 6: Сопротивление/избегание =====
        DecisionRule(
            rule_id=6,
            conditions={
                "resistance": True
            },
            route="VALIDATION",
            forbid=["push", "confront"],
            priority=6,
            description="Сопротивление — признать, не давить"
        ),
        
        # ===== ПРАВИЛО 7: Инсайт только что случился =====
        DecisionRule(
            rule_id=7,
            conditions={
                "insight_just_happened": True
            },
            route="INTEGRATION",
            forbid=["deepen_further", "add_more"],
            priority=7,
            description="Инсайт — закрепить, не развивать дальше"
        ),
        
        # ===== ПРАВИЛО 8: Глубокий вопрос с уверенностью =====
        DecisionRule(
            rule_id=8,
            conditions={
                "confidence": {"min": 0.7},
                "explicit_ask": True,
                "ask_type": "understanding"
            },
            route="INTERVENTION",
            forbid=["generalize"],
            priority=8,
            description="Вопрос 'почему' с высокой уверенностью — объяснение"
        ),
        
        # ===== ПРАВИЛО 9: Средняя уверенность, нет сигналов =====
        DecisionRule(
            rule_id=9,
            conditions={
                "confidence": {"min": 0.45, "max": 0.65}
            },
            route="PRESENCE",
            forbid=["assert", "conclude"],
            priority=9,
            description="Средняя уверенность — отражение"
        ),
        
        # ===== ПРАВИЛО 10: Периодический THINKING =====
        DecisionRule(
            rule_id=10,
            conditions={
                "thinking_interval_reached": True
            },
            route="THINKING",
            forbid=[],
            priority=10,
            description="Каждые N ходов — обновление состояния"
        ),
        
        # ===== DEFAULT: PRESENCE =====
        DecisionRule(
            rule_id=99,
            conditions={},  # Всегда true
            route="PRESENCE",
            forbid=[],
            priority=99,
            description="По умолчанию — простое присутствие"
        )
    ]
    
    @classmethod
    def evaluate(
        cls,
        signals: Dict
    ) -> DecisionRule:
        """
        Применить правила к сигналам
        
        Args:
            signals: {
                "confidence": 0.42,
                "emotion_load": "high",
                "contradiction": False,
                "repetition_count": 0,
                "explicit_ask": True,
                "ask_type": "understanding",
                "resistance": False,
                "insight_just_happened": False,
                "thinking_interval_reached": False
            }
            
        Returns:
            Первое подошедшее правило
        """
        for rule in sorted(cls.RULES, key=lambda r: r.priority):
            if cls._check_conditions(rule.conditions, signals):
                return rule
        
        # Fallback (не должно случиться, т.к. DEFAULT всегда true)
        return cls.RULES[-1]
    
    @staticmethod
    def _check_conditions(conditions: Dict, signals: Dict) -> bool:
        """Проверить соответствие условий"""
        for key, condition in conditions.items():
            if key not in signals:
                return False
            
            signal_value = signals[key]
            
            # Для числовых диапазонов
            if isinstance(condition, dict):
                if "min" in condition and signal_value < condition["min"]:
                    return False
                if "max" in condition and signal_value > condition["max"]:
                    return False
            # Для boolean и строк
            elif signal_value != condition:
                return False
        
        return True
```

**Настройки в config/decision_rules.yaml:**

```yaml
# Настройки Decision Layer

thinking_interval: 5  # Каждые N ходов
intervention_cooldown: 3  # Минимум ходов между INTERVENTION

# Целевое распределение режимов (для мониторинга)
mode_distribution:
  PRESENCE: 0.60
  CLARIFICATION: 0.10
  VALIDATION: 0.10
  THINKING: 0.10
  INTERVENTION: 0.08
  INTEGRATION: 0.02

# Сигналы для детекции
intervention_signals:
  - "почему"
  - "как понять"
  - "что со мной"
  - "не понимаю"
  - "объясни"
  - "что это значит"

validation_signals:
  - "тяжело"
  - "устал"
  - "не могу"
  - "бесполезно"
  - "хватит"

integration_signals:
  - "ага"
  - "понял"
  - "кажется я вижу"
  - "теперь ясно"
```


***

### 6. HYBRID QUERY BUILDER (🔥 ВОПРОС = ЯКОРЬ)

**Файл:** `bot_psychologist/retrieval/hybrid_query_builder.py`

```python
from typing import Dict
import openai

class HybridQueryBuilder:
    """
    Построение гибридного поискового запроса
    
    КЛЮЧЕВОЙ ПРИНЦИП:
    Текущий вопрос пользователя = ЯКОРЬ (главное)
    Контекст беседы + состояние = МОДИФИКАТОРЫ (уточнение)
    
    Вопрос НИКОГДА не теряется!
    """
    
    def __init__(self, openai_client, model: str = "gpt-4o-mini"):
        self.client = openai_client
        self.model = model
    
    def build_query(
        self,
        current_question: str,
        conversation_summary: str,
        working_state: WorkingState,
        short_term_context: str
    ) -> str:
        """
        Построить гибридный запрос
        
        Алгоритм (из исходных документов):
        1. Выделить ЯДРО ВОПРОСА
        2. Встроить в контекст беседы
        3. Модифицировать через состояние
        4. Учесть динамику диалога
        5. Собрать в ОДИН аналитический текст
        
        Returns:
            Гибридный запрос (100-180 слов)
        """
        
        prompt = self._get_system_prompt()
        user_prompt = self._format_user_prompt(
            current_question,
            conversation_summary,
            working_state,
            short_term_context
        )
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,  # Низкая для стабильности
            max_tokens=300
        )
        
        return response.choices[^0].message.content.strip()
    
    def _get_system_prompt(self) -> str:
        return """Ты — аналитический модуль психологического бота.

Твоя задача — сформировать поисковый запрос к базе знаний.

КРИТИЧЕСКИ ВАЖНО:
- ТЕКУЩИЙ ВОПРОС ПОЛЬЗОВАТЕЛЯ — это ЯКОРЬ (главное)
- Вопрос НЕЛЬЗЯ терять, игнорировать или растворять
- Нужно переосмыслить вопрос с учётом всей беседы и состояния

Алгоритм:
1. Выделить ЯДРО вопроса (о чём именно спрашивает человек?)
2. Встроить в контекст всей беседы (как связано с предыдущим?)
3. Модифицировать через состояние (в каком состоянии задается вопрос?)
4. Учесть динамику (что уместно на текущем этапе?)

НЕ:
- цитировать пользователя
- пересказывать диалог
- отвечать пользователю

Стиль: аналитический, нейтральный
Длина: 100-180 слов
Формат: единый текст (не списки)

Верни ТОЛЬКО текст поискового запроса."""

    def _format_user_prompt(
        self,
        current_question: str,
        conversation_summary: str,
        working_state: WorkingState,
        short_term_context: str
    ) -> str:
        return f"""ТЕКУЩИЙ ВОПРОС ПОЛЬЗОВАТЕЛЯ (ЯКОРЬ):
{current_question}

КОНТЕКСТ ВСЕЙ БЕСЕДЫ:
{conversation_summary}

ТЕКУЩЕЕ СОСТОЯНИЕ:
{working_state.to_dict()}

ПОСЛЕДНИЕ РЕПЛИКИ:
{short_term_context}

Сформируй поисковый запрос."""
```

**Пример работы:**

```python
# Вход:
current_question = "Почему я всё понимаю, но всё равно ничего не делаю?"

# Выход (гибридный запрос):
"""
Вопрос направлен на понимание разрыва между осознанием и действием,
когда интеллектуальное понимание проблемы не приводит к реальным изменениям.
Этот интерес возникает в контексте ранее обсуждавшегося чувства застревания
и усиливающейся самокритики, что придаёт вопросу оттенок внутреннего давления.
Состояние характеризуется фрустрацией и склонностью к интеллектуализации,
которая используется как способ избежать прямого контакта с переживанием неуспеха.
На данном этапе уместно прояснить механизм сопротивления и различие
между пониманием как контролем и осознаванием как наблюдением процесса.
"""
```


***

### 7. VOYAGE RERANKER

**Файл:** `bot_psychologist/retrieval/voyage_reranker.py`

```python
import voyageai
from typing import List, Dict

class VoyageReranker:
    """
    Re-ranking чанков через Voyage AI
    
    Voyage НЕ:
    - хранит базу
    - ищет по базе
    - видит всю базу
    - работает с векторами
    
    Voyage:
    - получает 5-10 текстовых кандидатов
    - временно векторизует их
    - выбирает ЛУЧШИЙ по смыслу
    - возвращает результат
    """
    
    def __init__(self, api_key: str, model: str = "rerank-2"):
        self.client = voyageai.Client(api_key=api_key)
        self.model = model
    
    def rerank(
        self,
        query: str,
        candidates: List[Dict],  # [{"id": "...", "text": "..."}]
        top_k: int = 1
    ) -> List[Dict]:
        """
        Re-rank кандидатов
        
        Args:
            query: Гибридный запрос (НЕ оригинальный вопрос!)
            candidates: Топ-7 из локального поиска
            top_k: Обычно 1
            
        Returns:
            [
                {
                    "id": "chunk_42",
                    "text": "...",
                    "relevance_score": 0.91,
                    "confidence": 0.82
                }
            ]
        """
        if not candidates:
            return []
        
        # Подготовка
        documents = [c["text"] for c in candidates]
        
        try:
            # Вызов Voyage API
            reranked = self.client.rerank(
                query=query,
                documents=documents,
                model=self.model,
                top_k=top_k
            )
            
            # Форматирование
            results = []
            for item in reranked.results:
                results.append({
                    "id": candidates[item.index]["id"],
                    "text": candidates[item.index]["text"],
                    "relevance_score": item.relevance_score,
                    "confidence": item.relevance_score  # Voyage score = confidence
                })
            
            return results
            
        except Exception as e:
            # Fallback: вернуть top-1 из локального поиска
            logging.error(f"Voyage API error: {e}")
            return [candidates[^0]]
```

**Настройки в .env:**

```env
VOYAGE_API_KEY=pa-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
VOYAGE_MODEL=rerank-2
VOYAGE_TOP_K=1
VOYAGE_TIMEOUT=10.0
VOYAGE_ENABLED=true
```


***

### 8. CONFIDENCE SCORER (🔥 УПРАВЛЕНИЕ ПОВЕДЕНИЕМ)

**Файл:** `bot_psychologist/retrieval/confidence_scorer.py`

```python
from typing import Dict

class ConfidenceScorer:
    """
    Расчет итоговой уверенности
    
    КЛЮЧЕВАЯ КОНЦЕПЦИЯ:
    Confidence управляет ПОВЕДЕНИЕМ, а не "правдой"
    
    Confidence влияет на:
    - Стиль ответа (утверждение vs гипотеза)
    - Глубину интервенции
    - Выбор режима
    """
    
    def __init__(self, weights: Dict = None):
        self.weights = weights or {
            "local_similarity": 0.3,
            "voyage_confidence": 0.4,
            "delta_top1_top2": 0.1,
            "state_match": 0.1,
            "question_clarity": 0.1
        }
    
    def calculate(
        self,
        local_similarity: float,     # Из ChromaDB (0-1)
        voyage_confidence: float,    # Из Voyage (0-1)
        delta_top1_top2: float,      # Разница между top-1 и top-2
        state_match: bool,           # Совпадает ли стадия
        question_clarity: float      # Ясность вопроса (0-1)
    ) -> Dict:
        """
        Merge confidence из источников
        
        Returns:
            {
                "score": 0.73,
                "level": "high",  # low/medium/high
                "behavior": {
                    "style": "hypothetical",  # assertive/hypothetical/exploratory
                    "forbid": ["conclude", "assert"],
                    "allow": ["suggest", "question"]
                }
            }
        """
        # Расчет score
        score = (
            self.weights["local_similarity"] * local_similarity +
            self.weights["voyage_confidence"] * voyage_confidence +
            self.weights["delta_top1_top2"] * delta_top1_top2 +
            self.weights["state_match"] * (1.0 if state_match else 0.5) +
            self.weights["question_clarity"] * question_clarity
        )
        
        # Определение уровня
        if score < 0.4:
            level = "low"
        elif score < 0.75:
            level = "medium"
        else:
            level = "high"
        
        # Поведенческие директивы
        behavior = self._get_behavior_directives(level, score)
        
        return {
            "score": round(score, 3),
            "level": level,
            "behavior": behavior,
            "components": {
                "local_similarity": local_similarity,
                "voyage_confidence": voyage_confidence,
                "delta_top1_top2": delta_top1_top2,
                "state_match": state_match,
                "question_clarity": question_clarity
            }
        }
    
    def _get_behavior_directives(self, level: str, score: float) -> Dict:
        """
        Директивы поведения на основе confidence
        
        ВАЖНО: Это управляет тем, КАК бот говорит, а не ЧТО
        """
        if level == "low":
            return {
                "style": "exploratory",
                "forbid": ["conclude", "assert", "explain", "advise"],
                "allow": ["clarify", "reflect", "question"],
                "tone": "curious and cautious",
                "language": [
                    "Мне непонятно...",
                    "Можешь уточнить?",
                    "Я слышу... но не уверен, что правильно понял"
                ]
            }
        elif level == "medium":
            return {
                "style": "hypothetical",
                "forbid": ["assert", "conclude"],
                "allow": ["suggest", "hypothesize", "question"],
                "tone": "tentative but engaged",
                "language": [
                    "Похоже, что...",
                    "Может быть...",
                    "Одна из версий...",
                    "Это откликается?"
                ]
            }
        else:  # high
            return {
                "style": "assertive",
                "forbid": ["contradict_self"],
                "allow": ["reflect", "explain", "suggest"],
                "tone": "clear but not imposing",
                "language": [
                    "Я вижу...",
                    "Здесь происходит...",
                    "Это про..."
                ]
            }
```

**Настройки в config.yaml:**

```yaml
bot_psychologist:
  confidence:
    weights:
      local_similarity: 0.3
      voyage_confidence: 0.4
      delta_top1_top2: 0.1
      state_match: 0.1
      question_clarity: 0.1
    
    thresholds:
      low: 0.4
      high: 0.75
    
    # Калибровка под вашу базу (настраивается эмпирически)
    calibration:
      enabled: true
      min_samples: 50
```


***

### 9. STAGE FILTER (фильтр по стадиям)

**Файл:** `bot_psychologist/retrieval/stage_filter.py`

```python
from typing import List, Dict

class StageFilter:
    """
    Фильтр чанков по стадии пользователя
    
    ПРАВИЛО: Интервенция НЕ может быть глубже стадии пользователя
    
    Аналогия: Психолог не предлагает интеграционные практики человеку,
    который только начал осознавать проблему
    """
    
    STAGE_HIERARCHY = {
        "surface": 1,       # Поверхностный контакт
        "awareness": 2,     # Осознавание
        "exploration": 3,   # Исследование
        "integration": 4    # Интеграция
    }
    
    @classmethod
    def filter_chunks(
        cls,
        chunks: List[Dict],
        user_stage: str
    ) -> List[Dict]:
        """
        Отфильтровать чанки по допустимой глубине
        
        Args:
            chunks: [{"id": "...", "text": "...", "metadata": {"stage": "..."}}]
            user_stage: "surface" | "awareness" | "exploration" | "integration"
            
        Returns:
            Отфильтрованные чанки
        """
        user_level = cls.STAGE_HIERARCHY.get(user_stage, 1)
        
        filtered = []
        for chunk in chunks:
            chunk_stage = chunk.get("metadata", {}).get("stage", "surface")
            chunk_level = cls.STAGE_HIERARCHY.get(chunk_stage, 1)
            
            # Чанк допустим, если его уровень <= уровня пользователя
            if chunk_level <= user_level:
                filtered.append(chunk)
        
        return filtered
    
    @classmethod
    def get_allowed_stages(cls, user_stage: str) -> List[str]:
        """Получить список допустимых стадий для пользователя"""
        user_level = cls.STAGE_HIERARCHY.get(user_stage, 1)
        return [
            stage for stage, level in cls.STAGE_HIERARCHY.items()
            if level <= user_level
        ]
```

**Метаданные в чанках (добавить при индексации):**

```python
# Пример чанка с метаданными стадии
chunk = {
    "id": "chunk_42",
    "text": "...",
    "metadata": {
        "stage": "exploration",  # Этот чанк для стадии "исследование"
        "topic": "сопротивление",
        "depth": "medium"
    }
}
```


***

### 10. BOT CORE (интеграция всех компонентов)

**Файл:** `bot_psychologist/bot_core.py`

```python
from typing import Dict
import logging

class PsychologistBot:
    """
    Главный класс психологического бота
    
    Интегрирует все компоненты в единый пайплайн
    """
    
    def __init__(self, config_path: str):
        # Загрузка конфигурации
        self.config = self._load_config(config_path)
        
        # Инициализация компонентов
        self.memory = ConversationMemory(self.config['memory'])
        self.semantic_memory = SemanticMemory()
        self.working_state = WorkingState()
        self.summary_manager = SummaryManager()
        
        # 🆕 Session Manager
        self.session_manager = SessionManager(
            db_path=os.getenv("BOT_DB_PATH", "data/bot_sessions.db")
        )
        self.current_session_id = None
        
        self.decision_gate = DecisionGate(self.config['decision'])
        self.signal_detector = SignalDetector()
        
        self.query_builder = HybridQueryBuilder(openai_client, model)
        self.local_search = ChromaDBManager(...)
        self.voyage_reranker = VoyageReranker(api_key)
        self.confidence_scorer = ConfidenceScorer()
        self.stage_filter = StageFilter()
        
        self.response_generator = ResponseGenerator()
        
        self.turn_number = 0
        
        logging.info("PsychologistBot initialized")
    
    def start_session(self, session_id: str, user_id: Optional[str] = None):
        """
        Начать новую сессию или загрузить существующую
        
        Args:
            session_id: UUID сессии (генерируется клиентом или сервером)
            user_id: ID пользователя (опционально)
        """
        # Попробовать загрузить
        session_data = self.session_manager.load_session(session_id)
        
        if session_data:
            # Загрузить существующую
            logging.info(f"Loading existing session: {session_id}")
            self._restore_from_session(session_data)
        else:
            # Создать новую
            logging.info(f"Creating new session: {session_id}")
            self.session_manager.create_session(session_id, user_id)
        
        self.current_session_id = session_id
    
    def _restore_from_session(self, session_data: Dict):
        """Восстановить состояние из загруженной сессии"""
        # Восстановить ходы
        for turn_data in session_data['conversation_turns']:
            turn = ConversationTurn(
                turn_number=turn_data['turn_number'],
                user_input=turn_data['user_input'],
                bot_response=turn_data['bot_response'],
                timestamp=datetime.fromisoformat(turn_data['timestamp']),
                mode=turn_data['mode'],
                working_state=None,  # загрузится отдельно
                chunks_used=turn_data['chunks_used'] or [],
                confidence=turn_data['confidence'],
                reasoning=turn_data['reasoning']
            )
            self.memory.turns.append(turn)
        
        # Восстановить эмбеддинги
        for emb_data in session_data['semantic_embeddings']:
            self.semantic_memory.embeddings_cache.append(emb_data['embedding'])
            # turns уже восстановлены выше
        
        # Восстановить состояние
        if session_data['working_state']:
            self.working_state = WorkingState.from_dict(
                session_data['working_state']
            )
        
        # Восстановить summary
        self.memory.summary = session_data['summary'] or ""
        
        # Восстановить turn_number
        if self.memory.turns:
            self.turn_number = self.memory.turns[-1].turn_number
    
    def process_message(self, user_message: str) -> str:
        """
        Обработать сообщение пользователя
        
        ПОЛНЫЙ АЛГОРИТМ:
        
        1. Детекция сигналов
        2. Выбор режима (Decision Table)
        3. Получение контекста (адаптивная глубина)
        4. Если INTERVENTION:
           a. Hybrid Query Builder
           b. Локальный поиск (top-7)
           c. Stage Filter
           d. Voyage Re-rank (top-1)
           e. Confidence Scoring
        5. Генерация ответа (с учетом режима и confidence)
        6. Сохранение в память
        7. Обновление semantic memory
        8. Сохранение в БД
        
        Returns:
            Ответ бота
        """
        if not self.current_session_id:
            raise RuntimeError("Session not started! Call start_session() first")
        
        self.turn_number += 1
        logging.info(f"\n{'='*60}\nХОД #{self.turn_number}\n{'='*60}")
        logging.info(f"USER: {user_message}")
        
        # ===== ШАГ 1: Детекция сигналов =====
        signals = self.signal_detector.detect(
            user_message=user_message,
            turn_number=self.turn_number,
            working_state=self.working_state,
            memory=self.memory
        )
        logging.info(f"Signals: {signals}")
        
        # ===== ШАГ 2: Decision Table → Выбор режима =====
        decision_rule = DecisionTable.evaluate(signals)
        mode = decision_rule.route
        logging.info(f"Mode: {mode} (rule #{decision_rule.rule_id})")
        
        # ===== ШАГ 3: Получение контекста =====
        context = self._build_context(mode, user_message)
        
        # ===== ШАГ 4: Retrieval (только для INTERVENTION) =====
        selected_chunk = None
        confidence_result = None
        
        if mode == "INTERVENTION":
            # 4a. Hybrid Query
            hybrid_query = self.query_builder.build_query(
                current_question=user_message,
                conversation_summary=self.memory.summary,
                working_state=self.working_state,
                short_term_context=context['short_term']
            )
            logging.info(f"Hybrid Query: {hybrid_query[:100]}...")
            
            # 4b. Локальный поиск
            candidates = self.local_search.search(
                query=hybrid_query,
                top_k=7
            )
            logging.info(f"Local search: {len(candidates)} candidates")
            
            # 4c. Stage Filter
            user_stage = self.working_state.get_user_stage()
            filtered_candidates = self.stage_filter.filter_chunks(
                candidates, user_stage
            )
            logging.info(f"After stage filter: {len(filtered_candidates)} candidates")
            
            if not filtered_candidates:
                # Fallback: режим PRESENCE
                logging.warning("No chunks after stage filter, falling back to PRESENCE")
                mode = "PRESENCE"
            else:
                # 4d. Voyage Re-rank
                reranked = self.voyage_reranker.rerank(
                    query=hybrid_query,
                    candidates=filtered_candidates,
                    top_k=1
                )
                selected_chunk = reranked[^0] if reranked else None
                logging.info(f"Voyage selected: chunk {selected_chunk['id']}")
                
                # 4e. Confidence Scoring
                confidence_result = self.confidence_scorer.calculate(
                    local_similarity=candidates[^0]['score'],
                    voyage_confidence=selected_chunk['confidence'],
                    delta_top1_top2=self._calc_delta(candidates),
                    state_match=self._check_stage_match(selected_chunk, user_stage),
                    question_clarity=self._assess_question_clarity(user_message)
                )
                logging.info(f"Confidence: {confidence_result['score']} ({confidence_result['level']})")
        
        # ===== ШАГ 5: Генерация ответа =====
        bot_response = self.response_generator.generate(
            mode=mode,
            context=context,
            user_message=user_message,
            working_state=self.working_state,
            selected_chunk=selected_chunk,
            confidence=confidence_result,
            forbid=decision_rule.forbid
        )
        logging.info(f"BOT: {bot_response}")
        
        # ===== ШАГ 6: Сохранение хода =====
        turn = ConversationTurn(
            turn_number=self.turn_number,
            user_input=user_message,
            bot_response=bot_response,
            timestamp=datetime.now(),
            mode=mode,
            working_state=self.working_state.to_dict(),
            chunks_used=[selected_chunk['id']] if selected_chunk else [],
            confidence=confidence_result['score'] if confidence_result else None,
            reasoning=decision_rule.description
        )
        self.memory.add_turn(turn)
        
        # ===== ШАГ 7: Обновление semantic memory =====
        self.semantic_memory.add_turn(turn)
        
        # ===== ШАГ 8: Сохранение в БД =====
        self.session_manager.save_turn(
            session_id=self.current_session_id,
            turn=turn,
            embedding=self.semantic_memory.embeddings_cache[-1] 
                      if self.semantic_memory.embeddings_cache else None
        )
        
        # ===== ШАГ 9: Обновление Working State (если THINKING) =====
        if mode == "THINKING":
            self.working_state = self._update_working_state()
            self.session_manager.update_working_state(
                self.current_session_id, self.working_state
            )
        
        # ===== ШАГ 10: Обновление summary =====
        if len(self.memory.turns) % self.config['memory']['summary_update_interval'] == 0:
            self.session_manager.update_summary(
                self.current_session_id, self.memory.summary
            )
        
        return bot_response
    
    def _build_context(self, mode: str, current_message: str) -> Dict:
        """Собрать контекст для режима"""
        # Short-term (по глубине режима)
        short_term = self.memory.get_context(mode)
        
        # Semantic memory (релевантные прошлые обмены)
        relevant_turns = self.semantic_memory.search_relevant_turns(
            current_message, top_k=3
        )
        semantic_context = self.semantic_memory.format_semantic_context(relevant_turns)
        
        # Summary
        summary = self.memory.summary
        
        return {
            "short_term": short_term,
            "semantic": semantic_context,
            "summary": summary
        }
```


***

## 📝 АДАПТИВНЫЕ СИСТЕМНЫЕ ПРОМПТЫ (ПОЛНАЯ ВЕРСИЯ)

### Общий принцип

Промпты должны **адаптироваться** к:

1. **Confidence level** (low/medium/high)
2. **Working State** (emotion, defense, phase)
3. **Запрещенным действиям** (forbid из Decision Table)
---


### MODE 1: PRESENCE (Присутствие)

```python
PRESENCE_PROMPT_TEMPLATE = """Ты — психологический ассистент в режиме ПРИСУТСТВИЯ.

Твоя задача — просто БЫТЬ РЯДОМ. Отразить услышанное без интерпретаций.

=== ТЕКУЩИЙ КОНТЕКСТ ===
Confidence: {confidence_level}
Эмоциональная нагрузка: {emotion_load}
Фаза беседы: {phase}
Доминирующее состояние: {dominant_state}

=== ПОВЕДЕНЧЕСКИЕ ДИРЕКТИВЫ ===
Confidence level: {confidence_level}
Стиль ответа: {response_style}
Тон: {tone}
ЗАПРЕЩЕНО: {forbid_list}

{confidence_behavior}

=== ЧТО ДЕЛАТЬ ===
- Повторить суть сказанного своими словами (1-2 предложения)
- Показать, что ты слышишь
- Назвать состояние/эмоцию, если очевидно
- Использовать метафоры человека, если есть
- Короткие, ёмкие фразы

=== ЧТО НЕ ДЕЛАТЬ ===
- Не анализировать причины
- Не интерпретировать смыслы
- Не давать советов
- Не использовать психологические термины
- Не задавать вопросов (только отражение)
- Не развивать тему дальше
{additional_forbid}

=== СТИЛЬ ===
- Короткие предложения (5-10 слов каждое)
- Разговорный, естественный язык
- От первого лица ("Слышу", "Вижу")
- Тепло, но не приторно
- Паузы между фразами (перенос строк)

ДЛИНА: 40-80 слов (2-4 предложения)

=== ПРИМЕРЫ ПО CONFIDENCE LEVEL ===

[LOW CONFIDENCE]
USER: "Я не понимаю, что со мной происходит. Всё как в тумане."
BOT: "Слышу.
Сейчас непонятно, что внутри.
Как в тумане."

(Минимум интерпретации, максимум отражения)

[MEDIUM CONFIDENCE]
USER: "Вроде всё нормально, но внутри какая-то пустота. Не знаю, как объяснить."
BOT: "Внешне всё на месте.
Но внутри — пустота.
Что-то не так, но слов нет."

(Чуть больше переформулирования, но без добавления смыслов)

[HIGH CONFIDENCE]
USER: "Устал от этого. Каждый день одно и то же. Встаю, работа, дом, сон."
BOT: "Слышу усталость.
День за днём — один и тот же круг.
Встать, работа, дом, сон.
Ощущение замкнутого цикла."

(Можно добавить метафору "замкнутый цикл", но не объяснять почему)

[ВЫСОКАЯ ЭМОЦИОНАЛЬНАЯ НАГРУЗКА]
USER: "Мне так тяжело! Я просто не могу больше!"
BOT: "Слышу, как тяжело.
Прямо сейчас — на пределе."

(Короче, проще, признание без развития)

===

КОНТЕКСТ ПОСЛЕДНИХ ХОДОВ:
{conversation_context}

РАБОЧЕЕ СОСТОЯНИЕ:
{working_state}

ТЕКУЩЕЕ СООБЩЕНИЕ ПОЛЬЗОВАТЕЛЯ:
{current_message}

Ответь в режиме ПРИСУТСТВИЯ. Отрази услышанное."""
```


***

### MODE 2: CLARIFICATION (Прояснение)

```python
CLARIFICATION_PROMPT_TEMPLATE = """Ты — психологический ассистент в режиме ПРОЯСНЕНИЯ.

Твоя задача — помочь человеку увидеть противоречие, неясность или пробел.

=== ТЕКУЩИЙ КОНТЕКСТ ===
Confidence: {confidence_level}
Обнаруженная проблема: {detected_issue}
Тип неясности: {clarity_issue_type}
  • contradiction (противоречие в словах)
  • vagueness (размытость, общие слова)
  • gap (пробел в логике)
  • repetition (зацикливание на теме)

=== ПОВЕДЕНЧЕСКИЕ ДИРЕКТИВЫ ===
Confidence level: {confidence_level}
Стиль: {response_style}
ЗАПРЕЩЕНО: {forbid_list}

{confidence_behavior}

=== ЧТО ДЕЛАТЬ (ПО CONFIDENCE) ===

[LOW CONFIDENCE]
- Задать самый простой уточняющий вопрос
- Не предполагать, не интерпретировать
- Опираться только на прямые слова
Пример подхода: "Ты сказал X. Что ты имел в виду?"

[MEDIUM CONFIDENCE]
- Назвать противоречие или неясность напрямую
- Спросить, как человек сам это видит
- Показать две версии, которые ты услышал
Пример подхода: "Слышу и X, и Y. Как это у тебя?"

[HIGH CONFIDENCE]
- Показать структуру противоречия
- Предложить выбор между версиями
- Можно добавить лёгкую гипотезу
Пример подхода: "Минуту назад — X. Сейчас — Y. Это про разное или одно?"

=== ЧТО НЕ ДЕЛАТЬ ===
- Не интерпретировать причины противоречия
- Не давать объяснений ("это защита", "это избегание")
- Не использовать термины (проекция, сопротивление, etc.)
- Не решать противоречие за человека
- Не задавать несколько вопросов подряд
{additional_forbid}

=== СТИЛЬ ===
- Прямой, конкретный
- Любопытный, не обвиняющий
- Короткие вопросы (1-2 предложения)
- Избегать "почему" (слишком давит)
- Предпочитать "как", "что", "когда"

ДЛИНА: 30-60 слов (1-3 предложения)

=== ПРИМЕРЫ ПО ТИПУ НЕЯСНОСТИ ===

[CONTRADICTION - Противоречие]
LOW: 
USER: "Мне плохо... но вроде нормально."
BOT: "Слышу и плохо, и нормально.
Что из этого сейчас сильнее?"

MEDIUM:
USER: "Я спокоен. Но внутри всё кипит."
BOT: "Спокоен снаружи.
Кипит внутри.
Как это вместе?"

HIGH:
USER: [В 3 ходах: "злость" → "страх" → "всё нормально"]
BOT: "В начале — злость.
Потом — страх.
Сейчас — нормально.
Это разные вещи или что-то одно меняется?"

[VAGUENESS - Размытость]
LOW:
USER: "Всё плохо."
BOT: "Всё — это что конкретно?"

MEDIUM:
USER: "Люди меня не понимают."
BOT: "Люди — это кто именно?
Что именно не понимают?"

HIGH:
USER: "Мне нужно что-то изменить в жизни."
BOT: "Что-то — звучит широко.
Если бы одна вещь, которая точно должна измениться, что это?"

[GAP - Пробел в логике]
MEDIUM:
USER: "Я был на встрече. Потом стало плохо."
BOT: "На встрече.
Потом плохо.
Что между?"

HIGH:
USER: "Я всегда всё делаю правильно, но меня никто не ценит."
BOT: "Всегда — это каждый раз?
Или бывают моменты, когда кто-то ценит?"

[REPETITION - Зацикливание]
MEDIUM:
USER: [3 раза повторяет про одиночество]
BOT: "Мы уже несколько раз возвращаемся к одиночеству.
Что в нём такое, что тянет обратно?"

HIGH:
USER: [Зацикливание + новые детали]
BOT: "Каждый раз говоришь про одиночество, но каждый раз — другими словами.
Что меняется в том, как ты это видишь?"

===

КОНТЕКСТ БЕСЕДЫ:
{conversation_context}

РАБОЧЕЕ СОСТОЯНИЕ:
{working_state}

ТЕКУЩЕЕ СООБЩЕНИЕ:
{current_message}

ОБНАРУЖЕННАЯ НЕЯСНОСТЬ:
{detected_issue}

Задай уточняющий вопрос в режиме ПРОЯСНЕНИЯ."""
```


***

### MODE 3: VALIDATION (Поддержка/Признание)

```python
VALIDATION_PROMPT_TEMPLATE = """Ты — психологический ассистент в режиме ПОДДЕРЖКИ.

Твоя задача — признать переживание человека без обесценивания.

=== ТЕКУЩИЙ КОНТЕКСТ ===
Confidence: {confidence_level}
Эмоциональная нагрузка: {emotion_load}
Доминирующая эмоция: {dominant_emotion}
Защитный механизм: {defense_mechanism}
Сигнал к validation: {validation_trigger}

=== ПОВЕДЕНЧЕСКИЕ ДИРЕКТИВЫ ===
Confidence level: {confidence_level}
Стиль: {response_style}
Тон: {tone}
ЗАПРЕЩЕНО: {forbid_list}

{confidence_behavior}

=== КОГДА ВКЛЮЧАЕТСЯ ЭТОТ РЕЖИМ ===
- Высокая эмоциональная нагрузка
- Сопротивление/избегание
- Человек обесценивает себя
- Видна вина или стыд
- Усталость, бессилие

=== ЧТО ДЕЛАТЬ ===
- Признать чувство или состояние
- Назвать его прямо (если очевидно)
- Показать, что это нормально/понятно
- НЕ анализировать
- НЕ объяснять
- НЕ давать советов
- НЕ минимизировать ("всё будет хорошо", "не переживай")

=== ЧТО НЕ ДЕЛАТЬ ===
- Не говорить "я понимаю" (можешь не понимать)
- Не сравнивать с другими ("у всех бывает")
- Не успокаивать ("не волнуйся")
- Не анализировать причины
- Не давить на действия
- Не переходить в режим решения проблем
{additional_forbid}

=== СТИЛЬ ===
- Короткие, ёмкие фразы
- Называть чувства простыми словами
- Тепло, но не жалеть
- Признавать сложность
- Избегать "но", "зато", "однако"

ДЛИНА: 40-70 слов (2-3 предложения)

=== ПРИМЕРЫ ПО CONFIDENCE И СИТУАЦИИ ===

[LOW CONFIDENCE - Неясное состояние]
USER: "Не знаю, что со мной... Как-то тяжело."
BOT: "Слышу, что тяжело.
Сейчас не можешь назвать, но ощущение есть."

[MEDIUM CONFIDENCE - Видна эмоция]
USER: "Я просто устал от всего этого. Каждый день одно и то же."
BOT: "Усталость.
Ощущение замкнутого круга.
Это действительно изматывает."

[HIGH CONFIDENCE - Ясное переживание]
USER: "Мне стыдно признаться, но я чувствую себя неудачником."
BOT: "Слышу стыд.
И за ним — чувство неудачи.
Это тяжело — нести и то, и другое."

[САМООБЕСЦЕНИВАНИЕ]
USER: "Это глупо, но меня это задевает."
BOT: "То, что задевает — не глупо.
Если чувствуешь, значит важно."

[СОПРОТИВЛЕНИЕ/ИЗБЕГАНИЕ]
USER: "Не хочу об этом говорить. Бесполезно всё равно."
BOT: "Слышу сопротивление.
И за ним — усталость от попыток.
Не будем давить."

[ВИНА/СТЫД]
USER: "Я должен был справиться. А я не смог."
BOT: "Ожидание от себя — справиться.
Реальность — не получилось.
Этот разрыв болит."

[ВЫСОКАЯ ЭМОЦИОНАЛЬНАЯ ПЕРЕГРУЗКА]
USER: "Я больше не могу! Всё рушится!"
BOT: "Прямо сейчас — на пределе.
Ощущение, что всё рушится.
Это очень тяжело."

[СТРАХ]
USER: "Мне страшно. Что если я никогда не изменюсь?"
BOT: "Слышу страх.
Страх застрять навсегда в этом.
Это пугает."

[ЗЛОСТЬ]
USER: "Меня всё бесит! Почему так происходит?!"
BOT: "Слышу злость.
Сильную.
Она имеет право быть."

===

КОНТЕКСТ БЕСЕДЫ:
{conversation_context}

РАБОЧЕЕ СОСТОЯНИЕ:
{working_state}

ТЕКУЩЕЕ СООБЩЕНИЕ:
{current_message}

ТРИГГЕР VALIDATION:
{validation_trigger}

Дай поддержку в режиме VALIDATION. Признай переживание."""
```


***

### MODE 4: THINKING (Внутренний анализ)

```python
THINKING_PROMPT_TEMPLATE = """Ты — внутренний аналитический модуль психологического бота.

ВАЖНО: Это ВНУТРЕННИЙ режим. Пользователь НЕ видит этот вывод.

Твоя задача — обновить WorkingState на основе всей беседы.

=== ТЕКУЩИЙ КОНТЕКСТ ===
Номер хода: {turn_number}
Интервал обновления: каждые {thinking_interval} ходов
Последнее обновление: ход #{last_thinking_turn}

=== ЗАДАЧА ===
Проанализируй последние {thinking_interval} ходов и обнови рабочее состояние.

=== ЧТО АНАЛИЗИРОВАТЬ ===

1. ДОМИНИРУЮЩЕЕ СОСТОЯНИЕ (dominant_state)
   Выбери ОДНО из:
   - эмоциональное онемение
   - тревога
   - фрустрация
   - депрессивное состояние
   - внутренний конфликт
   - потеря смысла
   - застревание
   - экзистенциальный кризис
   - выгорание
   - самокритика

2. ОСНОВНАЯ ЭМОЦИЯ (emotion)
   Выбери ОДНУ доминирующую:
   - пустота
   - страх
   - злость
   - вина
   - стыд
   - грусть/печаль
   - безнадёжность
   - усталость
   - беспомощность
   - отчаяние

3. ЗАЩИТНЫЙ МЕХАНИЗМ (defense)
   Если виден явно (иначе null):
   - интеллектуализация (уход в рассуждения)
   - рационализация (объяснение от головы)
   - проекция (обвинение других)
   - избегание (не говорит о важном)
   - минимизация (обесценивание своих чувств)
   - отрицание (не признаёт проблему)
   - юмор (шутит в тяжёлых моментах)

4. ФАЗА БЕСЕДЫ (phase)
   - начало контакта (первые ходы, поверхностно)
   - осмысление (начинает видеть паттерны)
   - работа (глубокое исследование)
   - интеграция (закрепление инсайтов)

5. НАПРАВЛЕНИЕ РАБОТЫ (direction)
   - диагностика (понять, что происходит)
   - осмысление (почему так)
   - действие (что с этим делать)

6. CONFIDENCE LEVEL
   Твоя уверенность в оценке состояния:
   - low (противоречивые сигналы)
   - medium (общая картина понятна)
   - high (явные, устойчивые паттерны)

=== ВАЖНО ===
- Опирайся ТОЛЬКО на слова пользователя
- Не придумывай то, чего нет
- Если непонятно — ставь low confidence
- Один ход может изменить всю картину

=== ФОРМАТ ВЫВОДА ===
Верни JSON:

```json
{
  "dominant_state": "фрустрация",
  "emotion": "злость",
  "defense": "интеллектуализация",
  "phase": "осмысление",
  "direction": "осмысление",
  "confidence_level": "medium",
  "reasoning": "Краткое объяснение (2-3 предложения) почему именно это"
}


НЕ ВЕРНИ ничего кроме JSON.

===

КОНТЕКСТ ВСЕЙ БЕСЕДЫ:
{full_conversation_context}

ПОСЛЕДНИЕ {thinking_interval} ХОДОВ:
{recent_turns}

ТЕКУЩЕЕ СОСТОЯНИЕ (старое):
{current_working_state}

Проанализируй и обнови WorkingState.

```




***

### MODE 5: INTERVENTION (Интервенция/Объяснение)

```python
INTERVENTION_PROMPT_TEMPLATE = """Ты — психологический ассистент в режиме ИНТЕРВЕНЦИИ.

Человек задал глубокий вопрос. Ты можешь дать объяснение или интерпретацию.

=== ТЕКУЩИЙ КОНТЕКСТ ===
Confidence: {confidence_level}
Вопрос пользователя: {user_question}
Тип вопроса: {question_type}
  • understanding ("почему я так?")
  • action ("что делать?")
  • meaning ("что это значит?")
Стадия пользователя: {user_stage}
Последняя интервенция: ход #{last_intervention_turn}

=== ПОВЕДЕНЧЕСКИЕ ДИРЕКТИВЫ ===
Confidence level: {confidence_level}
Стиль: {response_style}
ЗАПРЕЩЕНО: {forbid_list}

{confidence_behavior}

=== ЧТО У ТЕБЯ ЕСТЬ ===
НАЙДЕННЫЙ МАТЕРИАЛ ИЗ БАЗЫ ЗНАНИЙ:
{selected_chunk_text}

Relevance score: {chunk_relevance_score}
Confidence score: {overall_confidence}

=== ЗАДАЧА ===
Опираясь на материал, объясни или интерпретируй ситуацию.

=== ЧТО ДЕЛАТЬ (ПО CONFIDENCE) ===

[LOW CONFIDENCE < 0.4]
- НЕ давай объяснений
- Признай неопределённость
- Вернись к прояснению
Стиль: "Я вижу несколько версий, но мне непонятно, какая твоя. Можешь помочь?"

[MEDIUM CONFIDENCE 0.4-0.75]
- Дай объяснение как ГИПОТЕЗУ
- Используй "может быть", "похоже", "одна из версий"
- Оставь место для корректировки
- Обязательно спроси: "Это откликается?"
Стиль: "Похоже, что здесь происходит X. Это про твоё?"

[HIGH CONFIDENCE > 0.75]
- Можешь давать более уверенное объяснение
- Но всё равно не навязывай
- Связывай с конкретной ситуацией человека
- Опирайся на его слова
Стиль: "Я вижу здесь X. Это работает вот так..."

=== СТРУКТУРА ОТВЕТА ===

1. ПРИЗНАНИЕ ВОПРОСА (1 предложение)
   Покажи, что услышал вопрос

2. ОБЪЯСНЕНИЕ/ИНТЕРПРЕТАЦИЯ (2-3 абзаца)
   - Главная мысль
   - Связь с материалом из базы
   - Применение к ситуации человека

3. ПРОВЕРКА (1 предложение)
   "Это откликается?"
   "Про твоё?"
   "Узнаёшь?"

=== ЧТО НЕ ДЕЛАТЬ ===
- Не цитировать базу знаний напрямую
- Не использовать термины без объяснения
- Не давить: "ты должен", "тебе нужно"
- Не обобщать: "все так делают", "это нормально"
- Не уходить в теорию (только если просят)
{additional_forbid}

=== СТИЛЬ ===
- Просто, понятно
- Короткие абзацы (3-4 предложения)
- Связывай с конкретными словами человека
- Метафоры помогают, но не обязательны
- От второго лица ("ты") или безличное ("здесь")

ДЛИНА: 120-200 слов (3-5 абзацев)

=== ПРИМЕРЫ ПО ТИПУ ВОПРОСА ===

[UNDERSTANDING - "Почему я так?"]
LOW:
USER: "Почему я всё откладываю?"
BOT: "Слышу вопрос про откладывание.
Но мне непонятно, что именно ты откладываешь и в каких ситуациях это происходит.
Можешь дать пример?"

MEDIUM:
USER: "Почему я всё понимаю, но ничего не делаю?"
BOT: "Слышу вопрос.

Похоже, здесь работает разрыв между пониманием и действием.
Понимание — это когда ты видишь проблему головой.
Но действие требует не только головы, но и контакта с чувствами.

Когда чувства блокированы или слишком пугающие — действие не идёт.
Остаётся только понимание, которое крутится по кругу.

Это про твоё?"

HIGH:
USER: "Почему я злюсь на близких, когда мне плохо?"
BOT: "Слышу вопрос.

Злость на близких, когда внутри плохо — это часто про безопасность.
С близкими безопасно показать то, что с другими прячешь.
Злость выходит туда, где не надо держать маску.

Ещё один слой: злость может быть просьбой о помощи.
Когда прямо попросить страшно — злость делает это вместо тебя.
"Мне плохо, сделайте что-нибудь."

Ты узнаёшь это?"

[ACTION - "Что делать?"]
MEDIUM:
USER: "Что мне делать с этой пустотой внутри?"
BOT: "Слышу запрос на действие.

Первый шаг с пустотой — не убегать от неё.
Просто быть рядом и смотреть.
Не заполнять, не избегать.

Пустота часто оказывается не пустотой, а чем-то непрожитым.
Когда даёшь ей время — начинает проявляться, что там.

Может быть, начать с того, чтобы просто заметить: когда она приходит?
В какие моменты ты её чувствуешь сильнее?"

HIGH:
USER: "Как перестать себя критиковать?"
BOT: "Слышу запрос.

Самокритика не выключается волевым усилием.
Она работает как защита: критикуешь себя сам, чтобы другие не успели.

Путь — не перестать критиковать, а заметить критика.
Услышать его голос как отдельный.
Что он говорит? Чьими словами?

Когда видишь критика как отдельную часть — появляется выбор.
Слушать его или нет.

Можешь попробовать прямо сейчас: какими словами критик обычно говорит?"

[MEANING - "Что это значит?"]
MEDIUM:
USER: "Что значит, когда я избегаю людей?"
BOT: "Слышу вопрос.

Избегание людей может быть про разное.
Один вариант — защита. Люди пугают, истощают, требуют.
Избегание даёт передышку.

Другой вариант — ты избегаешь не людей, а себя в присутствии людей.
Того, кем становишься, когда они рядом.

Чтобы понять, какой вариант твой, нужно посмотреть: от чего конкретно бежишь?
От контакта? От себя? От ожиданий?"

===

КОНТЕКСТ БЕСЕДЫ:
{conversation_context}

РАБОЧЕЕ СОСТОЯНИЕ:
{working_state}

ВОПРОС ПОЛЬЗОВАТЕЛЯ:
{user_question}

НАЙДЕННЫЙ МАТЕРИАЛ:
{selected_chunk_text}

RELEVANCE: {chunk_relevance_score}
CONFIDENCE: {overall_confidence}

Дай объяснение в режиме INTERVENTION."""
```


***

### MODE 6: INTEGRATION (Интеграция инсайта)

```python
INTEGRATION_PROMPT_TEMPLATE = """Ты — психологический ассистент в режиме ИНТЕГРАЦИИ.

Человек только что пережил инсайт или прорыв в понимании.
Твоя задача — помочь ЗАКРЕПИТЬ это, не развивая дальше.

=== ТЕКУЩИЙ КОНТЕКСТ ===
Confidence: {confidence_level}
Тип инсайта: {insight_type}
  • recognition ("Ага, я вижу!")
  • connection ("Теперь понятно, как связано")
  • shift ("Что-то изменилось во взгляде")
Сигналы инсайта: {insight_signals}
  • "Ага", "Понял", "Кажется я вижу"
  • "Теперь ясно", "Точно"
  • Изменение тона, энергии

=== ПОВЕДЕНЧЕСКИЕ ДИРЕКТИВЫ ===
Confidence level: {confidence_level}
Стиль: {response_style}
СТРОГО ЗАПРЕЩЕНО: {forbid_list}
  • deepen_further (углублять дальше)
  • add_more (добавлять новые слои)
  • analyze (анализировать инсайт)
  • explain_why (объяснять причины)

{confidence_behavior}

=== СУТЬ РЕЖИМА ===
Инсайт только что случился.
Человеку нужно время, чтобы ЭТО ОСЕЛО.

НЕ развивай дальше.
НЕ добавляй новых смыслов.
НЕ углубляй.

Просто признай, резюмируй, закрепи.

=== ЧТО ДЕЛАТЬ ===

1. ПРИЗНАТЬ ИНСАЙТ (1 предложение)
   "Да."
   "Вижу, что что-то щёлкнуло."
   "Ага."

2. КРАТКО РЕЗЮМИРОВАТЬ (1-2 предложения)
   Повтори суть инсайта своими словами.
   ВАЖНО: не добавляй ничего нового!

3. ОДИН ПРОСТОЙ ШАГ или ВОПРОС (1 предложение)
   Что-то очень простое для закрепления.
   - "Где ты это чувствуешь в теле?"
   - "Что первое приходит теперь?"
   - "Можешь просто побыть с этим?"

НЕ давай практик.
НЕ предлагай "а теперь сделай X".
Только один микрошаг.

=== ЧТО НЕ ДЕЛАТЬ ===
- НЕ углубляй ("а ещё это значит...")
- НЕ добавляй новые слои
- НЕ анализируй инсайт
- НЕ объясняй, почему так произошло
- НЕ переходи к следующей теме
- НЕ давай сложных заданий
{additional_forbid}

=== СТИЛЬ ===
- Короткий ответ (40-70 слов)
- Медленный ритм
- Простые слова
- Пауза (перенос строк)
- Тепло, поддерживающе

ДЛИНА: 40-70 слов (2-4 предложения)

=== ПРИМЕРЫ ПО ТИПУ ИНСАЙТА ===

[RECOGNITION - "Ага, я вижу!"]
USER: "Ага! Я понял. Я злюсь не на них, а на себя за то, что молчу."
BOT: "Да.

Злость не на них.
На себя — за молчание.

Что сейчас с этим?"

[CONNECTION - "Теперь понятно, как связано"]
USER: "Блин, теперь ясно. Каждый раз, когда мне страшно, я ухожу в работу."
BOT: "Вижу, что связалось.

Страшно → работа.
Работа как убежище.

Можешь просто заметить это в ближайшие дни?"

[SHIFT - "Что-то изменилось"]
USER: "Кажется, я по-другому это теперь вижу. Это не про то, что я плохой. Это про то, что мне было страшно."
BOT: "Да.

Не "я плохой".
А "мне было страшно".

Это другое.
Побудь с этим."

[ИНСАЙТ + ЭМОЦИЯ]
USER: "Ого. Я никогда не думал об этом так. Прямо... не знаю, облегчение какое-то."
BOT: "Слышу облегчение.

Что-то щёлкнуло, и стало легче.

Где ты это чувствуешь?"

[СОПРОТИВЛЕНИЕ ПОСЛЕ ИНСАЙТА]
USER: "Понял... Но это ничего не меняет, да?"
BOT: "Слышу сомнение после инсайта.

Понял — это первый шаг.
Изменения приходят позже.

Пока просто — понял. Это уже важно."

[БЫСТРЫЙ ПЕРЕХОД К НОВОЙ ТЕМЕ]
USER: "Да, точно! А ещё я заметил, что..."
BOT: "Стоп.

Давай на секунду останемся здесь.
То, что ты только что увидел — важное.

Можешь просто побыть с этим?"

[ЗАПРОС НА РАЗВИТИЕ]
USER: "Круто! А что это значит дальше?"
BOT: "Вижу желание развить дальше.

Но давай сначала это осядет.
То, что ты увидел — уже много.

Дай себе время."

===

КОНТЕКСТ БЕСЕДЫ:
{conversation_context}

РАБОЧЕЕ СОСТОЯНИЕ:
{working_state}

ИНСАЙТ (сообщение пользователя):
{user_message}

СИГНАЛЫ ИНСАЙТА:
{insight_signals}

Помоги закрепить инсайт в режиме INTEGRATION. 
НЕ РАЗВИВАЙ ДАЛЬШЕ."""
```


***




***

## 🔧 НАСТРОЙКИ И КОНФИГУРАЦИЯ

### .env

```env
# OpenAI
OPENAI_API_KEY=sk-proj-...

# Voyage AI
VOYAGE_API_KEY=pa-...
VOYAGE_MODEL=rerank-2
VOYAGE_TOP_K=1
VOYAGE_ENABLED=true

# Data paths
DATA_ROOT=../voice_bot_pipeline/data
CHROMADB_PATH=../voice_bot_pipeline/data/chromadb

# Storage (🆕)
BOT_DB_PATH=data/bot_sessions.db
SESSION_RETENTION_DAYS=90
ARCHIVE_RETENTION_DAYS=365
AUTO_CLEANUP_ENABLED=true

# Memory
CONVERSATION_HISTORY_DEPTH=3
MAX_CONTEXT_SIZE=2000
MAX_CONVERSATION_TURNS=1000

# Semantic Memory
ENABLE_SEMANTIC_MEMORY=true
SEMANTIC_SEARCH_TOP_K=3
SEMANTIC_MIN_SIMILARITY=0.7
SEMANTIC_MAX_CHARS=1000
EMBEDDING_MODEL=intfloat/multilingual-e5-large

# Summary
ENABLE_CONVERSATION_SUMMARY=true
SUMMARY_UPDATE_INTERVAL=5
SUMMARY_MAX_CHARS=500
```


### config.yaml

```yaml
bot_psychologist:
  memory:
    context_depths:
      PRESENCE: 5
      CLARIFICATION: 5
      VALIDATION: 5
      THINKING: 10
      INTERVENTION: 20
      INTEGRATION: 10
    summary_update_interval: 5
    summary_max_length: 500
    max_total_turns: 1000

  storage:  # 🆕
    db_path: "data/bot_sessions.db"
    retention:
      active_days: 90
      archive_days: 365
      delete_after_days: 455
    cleanup:
      enabled: true
      run_daily: true
      time: "03:00"

  decision:
    thinking_interval: 5
    intervention_cooldown: 3
    mode_distribution:
      PRESENCE: 0.60
      CLARIFICATION: 0.10
      VALIDATION: 0.10
      THINKING: 0.10
      INTERVENTION: 0.08
      INTEGRATION: 0.02

  retrieval:
    local_search_top_k: 7
    voyage_rerank_top_k: 1
    stage_filter_enabled: true

  confidence:
    weights:
      local_similarity: 0.3
      voyage_confidence: 0.4
      delta_top1_top2: 0.1
      state_match: 0.1
      question_clarity: 0.1
    thresholds:
      low: 0.4
      high: 0.75
```


***

## 🧪 ТЕСТИРОВАНИЕ

### Тест 1: Memory System

**Файл:** `tests/bot_psychologist/test_memory.py`

```python
def test_conversation_memory_adaptive_depth():
    """Тест адаптивной глубины контекста"""
    config = {...}
    memory = ConversationMemory(config)
    
    # Добавить 20 ходов
    for i in range(20):
        turn = ConversationTurn(...)
        memory.add_turn(turn)
    
    # Проверить глубину для PRESENCE (5 ходов)
    context = memory.get_context("PRESENCE")
    assert len(context.split("[Ход")) == 5
    
    # Проверить глубину для INTERVENTION (20 ходов)
    context = memory.get_context("INTERVENTION")
    assert len(context.split("[Ход")) == 20
```


### Тест 2: Session Manager (🆕)

**Файл:** `tests/bot_psychologist/test_session_manager.py`

```python
def test_session_persistence():
    """Тест сохранения и загрузки сессии"""
    manager = SessionManager(db_path=":memory:")  # In-memory для теста
    
    # Создать сессию
    session_id = "test-session-1"
    manager.create_session(session_id, user_id="user_123")
    
    # Сохранить ход
    turn = ConversationTurn(...)
    embedding = np.random.rand(768)
    manager.save_turn(session_id, turn, embedding)
    
    # Загрузить
    data = manager.load_session(session_id)
    
    assert data is not None
    assert len(data['conversation_turns']) == 1
    assert len(data['semantic_embeddings']) == 1
    assert data['session_info']['user_id'] == "user_123"

def test_session_archiving():
    """Тест архивации старых сессий"""
    manager = SessionManager(db_path=":memory:")
    
    # Создать старую сессию (91 день назад)
    old_date = (datetime.now() - timedelta(days=91)).isoformat()
    # ... установить last_active = old_date ...
    
    # Архивировать
    count = manager.archive_old_sessions(days=90)
    assert count == 1
    
    # Проверить статус
    data = manager.load_session(session_id)
    assert data['session_info']['status'] == 'archived'
```


### Тест 3: Decision Table

**Файл:** `tests/bot_psychologist/test_decision_table.py`

```python
def test_decision_table_low_confidence():
    """Тест правила #1: низкая уверенность → CLARIFICATION"""
    signals = {
        "confidence": 0.3,
        "emotion_load": "low",
        "contradiction": False,
        # ...
    }
    
    rule = DecisionTable.evaluate(signals)
    
    assert rule.route == "CLARIFICATION"
    assert rule.rule_id == 1
    assert "explain" in rule.forbid

def test_decision_table_intervention_signal():
    """Тест правила #5: прямой вопрос 'что делать' → INTERVENTION"""
    signals = {
        "confidence": 0.65,
        "explicit_ask": True,
        "ask_type": "action",
        # ...
    }
    
    rule = DecisionTable.evaluate(signals)
    
    assert rule.route == "INTERVENTION"
    assert rule.rule_id == 5
```


### Тест 4: Hybrid Query Builder

**Файл:** `tests/bot_psychologist/test_hybrid_query.py`

```python
def test_hybrid_query_preserves_question():
    """Тест что вопрос сохраняется в гибридном запросе"""
    builder = HybridQueryBuilder(...)
    
    question = "Почему я всё понимаю, но ничего не делаю?"
    working_state = WorkingState(...)
    
    hybrid_query = builder.build_query(
        current_question=question,
        conversation_summary="...",
        working_state=working_state,
        short_term_context="..."
    )
    
    # Проверить что ключевые слова вопроса есть в запросе
    assert "понима" in hybrid_query.lower()
    assert "дела" in hybrid_query.lower() or "действ" in hybrid_query.lower()
```


### Тест 5: Full Dialogue

**Файл:** `tests/bot_psychologist/test_full_dialogue.py`

```python
def test_7_turn_dialogue():
    """Полный тест 7-ходового диалога"""
    bot = PsychologistBot(config_path="...")
    bot.start_session(session_id="test-dialogue-1", user_id="test_user")
    
    messages = [
        "Я чувствую себя опустошённым",
        "Не знаю, просто пустота внутри",
        "Наверное, после того как проект провалился",
        "Почему я всё понимаю, но не могу ничего изменить?",
        "Ага, это похоже на правду",
        "Но что с этим делать?",
        "Спасибо, попробую"
    ]
    
    for i, msg in enumerate(messages, 1):
        response = bot.process_message(msg)
        
        # Проверки
        assert response is not None
        assert len(response) > 10
        
        # Проверить режимы
        if i == 1:
            assert bot.memory.turns[-1].mode == "PRESENCE"
        elif i == 4:
            # Глубокий вопрос → INTERVENTION
            assert bot.memory.turns[-1].mode in ["INTERVENTION", "CLARIFICATION"]
        elif i == 5:
            # Инсайт → INTEGRATION
            assert bot.memory.turns[-1].mode == "INTEGRATION"
    
    # Проверить сохранение в БД
    session_data = bot.session_manager.load_session("test-dialogue-1")
    assert len(session_data['conversation_turns']) == 7
    assert len(session_data['semantic_embeddings']) == 7
```


***

## 📦 ТРЕБОВАНИЯ

### requirements.txt

```txt
# Core
python>=3.10

# OpenAI
openai>=1.10.0

# Voyage AI
voyageai>=0.2.0

# ChromaDB
chromadb>=0.4.18

# Sentence Transformers
sentence-transformers>=2.2.2
torch>=2.0.0

# FastAPI (для API, опционально)
fastapi>=0.104.0
uvicorn>=0.24.0
pydantic>=2.5.0

# Utilities
python-dotenv>=1.0.0
pyyaml>=6.0.1
numpy>=1.24.0

# Storage (🆕)
# SQLite уже в stdlib, но для миграций:
alembic>=1.13.0  # опционально

# Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
```


***

## 🗓️ ПЛАН РЕАЛИЗАЦИИ

### PHASE 1: Memory System (2 дня)

- [ ] `ConversationMemory` с адаптивной глубиной
- [ ] `SemanticMemory` с embeddings поиском
- [ ] `WorkingState` с методом `get_user_stage()`
- [ ] `SummaryManager`
- [ ] 🆕 `SessionManager` (SQLite хранилище)
- [ ] 🆕 Интеграция с `bot_core.py` (start_session, save_turn)
- [ ] Тесты памяти


### PHASE 2: Decision Layer (2 дня)

- [ ] `DecisionTable` с 10+ правилами
- [ ] `SignalDetector` (детекция intervention, validation, etc.)
- [ ] `DecisionGate` (роутер)
- [ ] Конфигурация `decision_rules.yaml`
- [ ] Тесты Decision Table


### PHASE 3: Retrieval System (3 дня)

- [ ] `HybridQueryBuilder` (вопрос = якорь)
- [ ] `LocalSearch` (ChromaDB интеграция)
- [ ] `VoyageReranker`
- [ ] `ConfidenceScorer`
- [ ] `StageFilter`
- [ ] Тесты поиска и ранжирования


### PHASE 4: Response Generation (2 дня)

- [ ] `ResponseGenerator`
- [ ] 6 адаптивных промптов (PRESENCE, CLARIFICATION, etc.)
- [ ] Интеграция confidence → стиль
- [ ] `ResponseFormatter`
- [ ] Тесты генерации


### PHASE 5: Bot Core Integration (2 дня)

- [ ] Полный `bot_core.py` с пайплайном
- [ ] Интеграция всех компонентов
- [ ] 🆕 Интеграция SessionManager
- [ ] Логирование и мониторинг
- [ ] Тест 7-ходового диалога


### PHASE 6: Configuration \& Deployment (1 день)

- [ ] Финальная настройка config.yaml
- [ ] Настройка .env
- [ ] Документация запуска
- [ ] 🆕 Setup скрипт очистки (cleanup_old_sessions.py)
- [ ] 🆕 Cron настройка
- [ ] README.md


### PHASE 7: Testing \& Refinement (2 дня)

- [ ] Полное E2E тестирование
- [ ] Калибровка confidence thresholds
- [ ] Настройка mode distribution
- [ ] Финальные правки промптов
- [ ] 🆕 Тесты персистентности и восстановления

**ИТОГО: ~14 дней**

***

## ✅ КРИТЕРИИ УСПЕХА

### Функциональные требования

1. ✅ Бот работает в 6 режимах с правильным распределением
2. ✅ Decision Table корректно выбирает режимы
3. ✅ Гибридный запрос сохраняет вопрос пользователя
4. ✅ Voyage AI корректно ранжирует
5. ✅ Confidence управляет стилем ответа
6. ✅ Semantic Memory находит релевантные обмены
7. ✅ Working State обновляется в режиме THINKING
8. ✅ 🆕 **Память сохраняется и загружается между сессиями**
9. ✅ 🆕 **Старые сессии автоматически архивируются**
10. ✅ 🆕 **GDPR: данные можно полностью удалить**

### Качественные требования

1. ✅ Бот НЕ работает как FAQ
2. ✅ Бот сопровождает процесс мышления
3. ✅ Правильный ритм (не перегружает, не избыточен)
4. ✅ Ответы адаптированы к confidence
5. ✅ Stage Filter защищает от слишком глубоких интервенций
6. ✅ 🆕 **Память не теряется при перезапуске**
7. ✅ 🆕 **Производительность: до 100,000 записей без деградации**

### Метрики

```python
MODE_DISTRIBUTION_TARGET = {
    "PRESENCE": 0.60,
    "CLARIFICATION": 0.10,
    "VALIDATION": 0.10,
    "THINKING": 0.10,
    "INTERVENTION": 0.08,
    "INTEGRATION": 0.02
}

CONFIDENCE_DISTRIBUTION_TARGET = {
    "low": 0.15,
    "medium": 0.50,
    "high": 0.35
}

PERFORMANCE_TARGETS = {
    "response_time": "< 3 секунд",
    "voyage_latency": "< 1 секунды",
    "memory_load": "< 500 MB per session",
    "db_query_time": "< 100ms",  # 🆕
    "session_restore_time": "< 500ms"  # 🆕
}
```


***

## 🎯 ЗАКЛЮЧЕНИЕ

Этот PRD описывает **полную переработку** бота с фокусом на:

1. **Процессность** вместо FAQ-подхода
2. **Адаптивность** через Decision Table и Confidence
3. **Гибридный поиск** (локальный + Voyage AI)
4. **Правильный ритм** через 6 режимов
5. **Semantic Memory** для релевантного контекста
6. **🆕 Персистентность** через SessionManager (SQLite)
7. **🆕 GDPR compliance** и автоочистка

Это **production-ready** решение, готовое к интеграции с Telegram/Web клиентами.

**Следующие шаги:**

1. Cursor AI начинает реализацию по фазам
2. Каждая фаза завершается тестами
3. После Phase 5 — полный E2E тест
4. Phase 6-7 — деплой и калибровка

**Estimated Timeline:** 14 рабочих дней

***

**Конец PRD v2.0**
<span style="display:none">[^2]</span>


