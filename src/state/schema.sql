-- ============================================================
-- Maze Myth State Database — Schema Reference
-- ============================================================
-- This file documents the table structure.
-- Tables are created automatically by state_manager.py using
-- CREATE TABLE IF NOT EXISTS — you do NOT need to run this file manually.
-- ============================================================

-- AI-generated endpoint responses
-- Each unique (path, method) pair maps to one LLM-generated JSON blob.
-- INSERT OR IGNORE ensures the FIRST AI response is always returned
-- for repeat visits — giving attackers consistent fake data.
CREATE TABLE IF NOT EXISTS endpoints (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    path              TEXT    NOT NULL,
    method            TEXT    NOT NULL,
    response_template TEXT    NOT NULL,   -- raw JSON string from LLM / fallback
    description       TEXT    DEFAULT '',
    created_at        TEXT    NOT NULL,   -- ISO-8601 UTC
    access_count      INTEGER DEFAULT 1,
    UNIQUE(path, method)                  -- enforces deduplication
);
CREATE INDEX IF NOT EXISTS idx_endpoints_path_method ON endpoints(path, method);

-- Arbitrary typed objects created during honeypot sessions
-- (e.g. fake users, accounts generated on demand)
CREATE TABLE IF NOT EXISTS objects (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    type       TEXT NOT NULL,             -- e.g. 'user', 'account'
    object_id  TEXT NOT NULL,             -- caller-defined ID
    data       TEXT NOT NULL,             -- JSON blob
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_objects_type ON objects(type);

-- Tracking beacons embedded in every bait file download
-- When an attacker opens a bait file, it calls back to /track/<beacon_id>
-- and the accessed_at + activation_ip fields are populated.
CREATE TABLE IF NOT EXISTS beacons (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    beacon_id     TEXT    NOT NULL UNIQUE,
    file_type     TEXT    NOT NULL,       -- 'pdf', 'xlsx', 'sqlite', etc.
    file_name     TEXT    NOT NULL,
    client_ip     TEXT    NOT NULL,       -- IP that downloaded the file
    generated_at  TEXT    NOT NULL,
    accessed_at   TEXT,                   -- NULL until beacon fires
    activation_ip TEXT,                   -- may differ from client_ip (proxy)
    access_count  INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_beacons_id ON beacons(beacon_id);
CREATE INDEX IF NOT EXISTS idx_beacons_ip ON beacons(client_ip);

-- Full log of every /api/download/* request
-- is_sensitive=1 triggers CRITICAL log level and dashboard alerts
CREATE TABLE IF NOT EXISTS downloads (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    filename     TEXT    NOT NULL,
    client_ip    TEXT    NOT NULL,
    user_agent   TEXT    DEFAULT '',
    timestamp    TEXT    NOT NULL,        -- ISO-8601 UTC
    is_sensitive INTEGER DEFAULT 0        -- 1 = matched sensitive keyword
);
CREATE INDEX IF NOT EXISTS idx_downloads_ip ON downloads(client_ip);
CREATE INDEX IF NOT EXISTS idx_downloads_ts ON downloads(timestamp);
