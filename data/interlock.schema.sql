-- InterLock AI — SQLite schema
--
-- Applied at runtime by src/interlock/store/sqlite.py (Phase 14+) and
-- src/interlock/cache/cost_ledger.py (Phase 13).
-- Tables are additive across phases; never drop or rename columns once
-- shipped. Migrations live in dated SQL files alongside this one when needed.

-- Phase 13: cost ledger.
-- Every LLM / embedding API call records one row. Aggregation is at query
-- time. Pricing constants live in code (cost_ledger.py) with citations.
CREATE TABLE IF NOT EXISTS cost_event (
  id                      INTEGER PRIMARY KEY AUTOINCREMENT,
  ts                      TEXT NOT NULL DEFAULT (datetime('now')),  -- ISO 8601
  provider                TEXT NOT NULL,        -- 'anthropic' | 'voyage'
  model                   TEXT,                  -- 'claude-opus-4-7', 'voyage-3', etc.
  namespace               TEXT NOT NULL,         -- caller workstream label
  input_tokens            INTEGER NOT NULL DEFAULT 0,
  cache_read_tokens       INTEGER NOT NULL DEFAULT 0,
  cache_creation_tokens   INTEGER NOT NULL DEFAULT 0,
  output_tokens           INTEGER NOT NULL DEFAULT 0,
  est_cost_usd            REAL NOT NULL DEFAULT 0.0
);

CREATE INDEX IF NOT EXISTS idx_cost_event_ts ON cost_event(ts);
CREATE INDEX IF NOT EXISTS idx_cost_event_provider ON cost_event(provider);
