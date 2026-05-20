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


-- Phase 14: entity / claim / decision persistence.
-- Entity = a piece of equipment, line, bus, etc. — anything claims are about.
-- Claim  = one (entity, attribute, value) statement with citation back to a
--          ParameterRecord (page, bbox, span_text).
-- Decision = a reviewer's accept/dismiss verdict on a surfaced flag.

CREATE TABLE IF NOT EXISTS entity (
  id          TEXT PRIMARY KEY,         -- 'xfmr_001', 'p_101', 'implicit_doc_a'
  type        TEXT NOT NULL,            -- transformer | pump | line | bus | ...
  label       TEXT NOT NULL,
  project_id  TEXT,                     -- nullable for multi-project futures
  created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_entity_type ON entity(type);


CREATE TABLE IF NOT EXISTS claim (
  id                    TEXT PRIMARY KEY,           -- sha256 of canonical key tuple
  entity_id             TEXT NOT NULL REFERENCES entity(id),
  attribute             TEXT NOT NULL,              -- canonical phrase
  raw_value             TEXT NOT NULL,
  normalized_magnitude  REAL,
  normalized_unit       TEXT,
  doc_id                TEXT NOT NULL,
  source_path           TEXT NOT NULL,
  page                  INTEGER NOT NULL,
  bbox_x0               REAL NOT NULL,
  bbox_y0               REAL NOT NULL,
  bbox_x1               REAL NOT NULL,
  bbox_y1               REAL NOT NULL,
  section               TEXT,
  span_text             TEXT NOT NULL,
  extraction_version    TEXT NOT NULL,              -- 'regex-v1', 'llm-v1', ...
  created_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_claim_entity ON claim(entity_id);
CREATE INDEX IF NOT EXISTS idx_claim_attribute ON claim(attribute);
CREATE INDEX IF NOT EXISTS idx_claim_doc ON claim(doc_id);


CREATE TABLE IF NOT EXISTS decision (
  id                INTEGER PRIMARY KEY AUTOINCREMENT,
  fixture_pair_id   TEXT NOT NULL,
  flag_id           TEXT NOT NULL,
  verdict           TEXT NOT NULL,        -- 'accepted' | 'dismissed'
  reviewer          TEXT,                 -- nullable (single-user MVP)
  rationale         TEXT,                 -- optional reviewer note
  created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_decision_pair ON decision(fixture_pair_id);
CREATE INDEX IF NOT EXISTS idx_decision_flag ON decision(flag_id);
