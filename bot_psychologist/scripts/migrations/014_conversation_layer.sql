-- PRD-014 conversation layer migration
-- Idempotent migration for conversation lifecycle and memory compatibility.
-- ROLLBACK:
--   DROP INDEX IF EXISTS idx_conversations_last_message_at;
--   DROP INDEX IF EXISTS idx_conversations_status_user;
--   DROP INDEX IF EXISTS idx_conversations_session_id;
--   DROP INDEX IF EXISTS idx_conversations_user_id;
--   DROP TABLE IF EXISTS conversations;
--   -- Columns added to memory_items are not dropped automatically in SQLite.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL
        REFERENCES users(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL
        REFERENCES sessions(session_id) ON DELETE CASCADE,
    channel TEXT NOT NULL DEFAULT 'web'
        CHECK(channel IN ('web', 'telegram', 'api')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK(status IN ('active', 'paused', 'closed', 'archived')),
    title TEXT,
    started_at TEXT NOT NULL,
    last_message_at TEXT NOT NULL,
    ended_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    message_count INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id
ON conversations(user_id);

CREATE INDEX IF NOT EXISTS idx_conversations_session_id
ON conversations(session_id);

CREATE INDEX IF NOT EXISTS idx_conversations_status_user
ON conversations(status, user_id);

CREATE INDEX IF NOT EXISTS idx_conversations_last_message_at
ON conversations(last_message_at DESC);

-- Расширение memory_items выполняется в runtime через
-- api.conversations.repository.ConversationRepository.ensure_schema(),
-- где сначала проверяется наличие таблицы и колонок.
-- Это сделано для совместимости с SQLite окружениями,
-- где ALTER TABLE ... ADD COLUMN IF NOT EXISTS недоступен.
