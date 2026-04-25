-- PRD-013 identity layer migration
-- SQLite migration, idempotent for CREATE TABLE statements.
-- Rollback note:
--   Drop tables in reverse dependency order:
--   DROP TABLE IF EXISTS link_codes;
--   DROP TABLE IF EXISTS linked_identities;
--   DROP TABLE IF EXISTS sessions;
--   DROP TABLE IF EXISTS users;

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    canonical_name TEXT,
    timezone TEXT NOT NULL DEFAULT 'UTC',
    language TEXT NOT NULL DEFAULT 'ru',
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS linked_identities (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    external_id TEXT NOT NULL,
    verified_at TEXT,
    created_at TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    UNIQUE(provider, external_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_linked_identities_user_id
ON linked_identities(user_id);

CREATE INDEX IF NOT EXISTS idx_linked_identities_provider_external
ON linked_identities(provider, external_id);

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    created_at TEXT NOT NULL,
    last_active TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    working_state TEXT,
    conversation_summary TEXT,
    metadata TEXT,
    channel TEXT DEFAULT 'web',
    device_fingerprint TEXT,
    last_seen_at TEXT,
    expires_at TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS link_codes (
    code TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT,
    used_at TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_sessions_user_id
ON sessions(user_id);

CREATE INDEX IF NOT EXISTS idx_sessions_last_seen_at
ON sessions(last_seen_at);

CREATE INDEX IF NOT EXISTS idx_link_codes_user_id
ON link_codes(user_id);
