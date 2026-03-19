"""
Dynamic API Honeypot — State Manager
-------------------------------------
Persists all honeypot state to a SQLite database in WAL mode.

WAL (Write-Ahead Logging) allows many concurrent readers and one writer
simultaneously, making it safe under gunicorn's multi-threaded handling
of simultaneous attacker connections.

Database: databases/honeypot.db (auto-created on first run)

Tables
------
endpoints  — AI-generated endpoint responses (path + method → JSON)
objects    — Arbitrary typed objects produced during sessions
beacons    — Tracking tokens embedded in bait files
downloads  — Every file download event
"""

import sqlite3
import json
import threading
import logging
from pathlib import Path
from datetime import datetime, timedelta, timezone

def _now() -> str:
    """Return current UTC time as ISO-8601 string (timezone-aware)."""
    return datetime.now(timezone.utc).isoformat()

logger = logging.getLogger(__name__)

# Each thread gets its own SQLite connection (thread-local storage).
# This is required because sqlite3 connections are not safe to share
# across threads — especially under gunicorn's gthread worker class.
_local = threading.local()


class APIStateManager:
    """
    Manages state persistence for the dynamic API honeypot.

    Storage: SQLite database at `db_path` (default: databases/honeypot.db)
    Mode:    WAL — concurrent reads never block each other or writes.

    Tables
    ------
    endpoints  — AI-generated endpoint responses (path + method → JSON)
    objects    — Arbitrary typed objects created during the session
    beacons    — Tracking tokens embedded in bait files
    downloads  — Every file download event
    """

    def __init__(self, db_path: str = "databases/honeypot.db",
                 retention_days: int = 90):
        self.db_path = str(Path(db_path).resolve())
        self.retention_days = retention_days

        # Ensure the databases/ directory exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create schema on first run (idempotent — uses IF NOT EXISTS)
        self._init_schema()

        # Remove records older than retention_days
        self._cleanup_old_records(retention_days)

    # ── Internal: connection management ──────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        """
        Return the thread-local SQLite connection, creating it if needed.
        WAL mode + 5-second busy timeout to survive write contention.
        Row factory makes rows behave like dicts.
        """
        if not getattr(_local, "conn", None):
            conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False,  # each thread has its own connection
                timeout=5.0
            )
            conn.row_factory = sqlite3.Row          # rows accessible as dicts
            conn.execute("PRAGMA journal_mode=WAL") # enable WAL
            conn.execute("PRAGMA synchronous=NORMAL")  # safe + fast
            conn.execute("PRAGMA foreign_keys=ON")
            _local.conn = conn
        return _local.conn

    def _init_schema(self):
        """Create all tables if they don't exist yet."""
        conn = self._conn()
        conn.executescript("""
            -- AI-generated endpoint responses
            -- path + method form a unique key so the same URL always
            -- returns the same LLM-generated JSON (consistency for attackers)
            CREATE TABLE IF NOT EXISTS endpoints (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                path           TEXT    NOT NULL,
                method         TEXT    NOT NULL,
                response_template TEXT NOT NULL,   -- raw JSON string from LLM
                description    TEXT    DEFAULT '',
                created_at     TEXT    NOT NULL,
                access_count   INTEGER DEFAULT 1,
                UNIQUE(path, method)
            );
            CREATE INDEX IF NOT EXISTS idx_endpoints_path_method
                ON endpoints(path, method);

            -- Arbitrary typed objects (users, products, etc.)
            CREATE TABLE IF NOT EXISTS objects (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                type       TEXT NOT NULL,
                object_id  TEXT NOT NULL,
                data       TEXT NOT NULL,          -- JSON blob
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_objects_type ON objects(type);

            -- Tracking beacons embedded in every bait file
            CREATE TABLE IF NOT EXISTS beacons (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                beacon_id    TEXT    NOT NULL UNIQUE,
                file_type    TEXT    NOT NULL,
                file_name    TEXT    NOT NULL,
                client_ip    TEXT    NOT NULL,
                generated_at TEXT    NOT NULL,
                accessed_at  TEXT,                 -- NULL until file is opened
                activation_ip TEXT,
                access_count INTEGER DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_beacons_id ON beacons(beacon_id);
            CREATE INDEX IF NOT EXISTS idx_beacons_ip ON beacons(client_ip);

            -- File download log (every /api/download/* hit)
            CREATE TABLE IF NOT EXISTS downloads (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                filename     TEXT NOT NULL,
                client_ip    TEXT NOT NULL,
                user_agent   TEXT DEFAULT '',
                timestamp    TEXT NOT NULL,
                is_sensitive INTEGER DEFAULT 0     -- 1 = sensitive file
            );
            CREATE INDEX IF NOT EXISTS idx_downloads_ip
                ON downloads(client_ip);
            CREATE INDEX IF NOT EXISTS idx_downloads_ts
                ON downloads(timestamp);

            -- Structured audit log (mirrors log_files/api_audit.log in searchable form)
            -- level: INFO / WARNING / CRITICAL / ERROR
            -- event: short machine-readable tag (NEW_ENDPOINT_DISCOVERY, FILE_DOWNLOAD, etc.)
            -- message: full decoded log line (plain text, NOT Base64)
            -- client_ip: extracted attacker IP when available
            CREATE TABLE IF NOT EXISTS logs (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp  TEXT    NOT NULL,
                level      TEXT    NOT NULL,
                event      TEXT    DEFAULT '',
                message    TEXT    NOT NULL,
                client_ip  TEXT    DEFAULT ''
            );
            CREATE INDEX IF NOT EXISTS idx_logs_level   ON logs(level);
            CREATE INDEX IF NOT EXISTS idx_logs_ts      ON logs(timestamp);
            CREATE INDEX IF NOT EXISTS idx_logs_ip      ON logs(client_ip);
            CREATE INDEX IF NOT EXISTS idx_logs_event   ON logs(event);
        """)
        conn.commit()

    # ── Endpoints ─────────────────────────────────────────────────────────

    def endpoint_exists(self, path: str, method: str) -> bool:
        """Return True if this path+method has already been generated by the LLM."""
        conn = self._conn()
        cur = conn.execute(
            "SELECT 1 FROM endpoints WHERE path=? AND method=? LIMIT 1",
            (path, method)
        )
        return cur.fetchone() is not None

    def save_endpoint(self, path: str, method: str,
                      response_template: str, description: str = ""):
        """
        Persist an LLM-generated endpoint response.
        Uses INSERT OR IGNORE — duplicate path+method pairs are silently
        skipped, so the first AI response is always the canonical one.
        """
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO endpoints
                    (path, method, response_template, description, created_at, access_count)
                VALUES (?, ?, ?, ?, ?, 1)
                """,
                (path, method, response_template, description,
                 _now())
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"[STATE] save_endpoint failed: {e}")

    def get_endpoint(self, path: str, method: str) -> dict | None:
        """
        Retrieve a saved endpoint and atomically increment its access_count.
        UPDATE is committed before SELECT so the returned dict reflects the
        new (incremented) count. Returns None if not found.
        """
        conn = self._conn()
        try:
            # First check it exists
            exists = conn.execute(
                "SELECT 1 FROM endpoints WHERE path=? AND method=? LIMIT 1",
                (path, method)
            ).fetchone()

            if exists:
                # UPDATE + commit first so the subsequent SELECT sees the new count
                conn.execute(
                    "UPDATE endpoints SET access_count=access_count+1 WHERE path=? AND method=?",
                    (path, method)
                )
                conn.commit()
                # Now SELECT to get the fully updated row
                row = conn.execute(
                    "SELECT * FROM endpoints WHERE path=? AND method=? LIMIT 1",
                    (path, method)
                ).fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"[STATE] get_endpoint failed: {e}")
        return None

    def get_all_endpoints(self) -> list[dict]:
        """Return all generated endpoints as a list of dicts."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM endpoints ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Objects ───────────────────────────────────────────────────────────

    def save_object(self, object_type: str, object_id, data: dict):
        """Save an arbitrary typed object (e.g. a generated user record)."""
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO objects (type, object_id, data, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (object_type, str(object_id),
                 json.dumps(data), _now())
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"[STATE] save_object failed: {e}")

    def get_objects_by_type(self, object_type: str) -> list[dict]:
        """Return all objects of a given type as list of dicts."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM objects WHERE type=? ORDER BY created_at DESC",
            (object_type,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_object(self, object_type: str, object_id) -> dict | None:
        """Return the data dict for a specific typed object."""
        conn = self._conn()
        row = conn.execute(
            "SELECT data FROM objects WHERE type=? AND object_id=? LIMIT 1",
            (object_type, str(object_id))
        ).fetchone()
        if row:
            try:
                return json.loads(row["data"])
            except (json.JSONDecodeError, KeyError):
                return None
        return None

    # ── Beacons ───────────────────────────────────────────────────────────

    def save_beacon(self, beacon_id: str, file_type: str,
                    file_name: str, client_ip: str):
        """Record a tracking beacon that was embedded in a bait file."""
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO beacons
                    (beacon_id, file_type, file_name, client_ip, generated_at,
                     accessed_at, access_count)
                VALUES (?, ?, ?, ?, ?, NULL, 0)
                """,
                (beacon_id, file_type, file_name, client_ip,
                 _now())
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"[STATE] save_beacon failed: {e}")

    def activate_beacon(self, beacon_id: str, client_ip: str) -> dict | None:
        """
        Mark a beacon as accessed (the attacker opened the bait file).
        Returns the beacon record dict, or None if not found.
        """
        conn = self._conn()
        try:
            conn.execute(
                """
                UPDATE beacons
                SET accessed_at   = ?,
                    activation_ip = ?,
                    access_count  = access_count + 1
                WHERE beacon_id = ?
                """,
                (_now(), client_ip, beacon_id)
            )
            conn.commit()
            row = conn.execute(
                "SELECT * FROM beacons WHERE beacon_id=? LIMIT 1",
                (beacon_id,)
            ).fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"[STATE] activate_beacon failed: {e}")
            return None

    # ── Downloads ─────────────────────────────────────────────────────────

    def log_download(self, filename: str, client_ip: str, user_agent: str = ""):
        """Record a file download event for the dashboard."""
        sensitive_keywords = [
            'credential', 'secret', 'key', 'password',
            'backup', 'config', 'db', 'sqlite'
        ]
        is_sensitive = int(
            any(k in filename.lower() for k in sensitive_keywords)
        )
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO downloads (filename, client_ip, user_agent, timestamp, is_sensitive)
                VALUES (?, ?, ?, ?, ?)
                """,
                (filename, client_ip,
                 (user_agent[:200] if user_agent else ""),
                 _now(), is_sensitive)
            )
            conn.commit()
        except sqlite3.Error as e:
            logger.error(f"[STATE] log_download failed: {e}")

    def get_downloads(self, limit: int = 50) -> list[dict]:
        """Return the most recent downloads, newest first."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM downloads ORDER BY timestamp DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def get_sensitive_downloads(self) -> list[dict]:
        """Return only downloads of sensitive files."""
        conn = self._conn()
        rows = conn.execute(
            "SELECT * FROM downloads WHERE is_sensitive=1 ORDER BY timestamp DESC"
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Statistics ────────────────────────────────────────────────────────

    def get_statistics(self) -> dict:
        """
        Return honeypot-wide counters.
        Used by the startup banner and the dashboard /api/stats endpoint.
        """
        conn = self._conn()

        def count(table, where=""):
            sql = f"SELECT COUNT(*) FROM {table}"
            if where:
                sql += f" WHERE {where}"
            return conn.execute(sql).fetchone()[0]

        return {
            "total_endpoints":    count("endpoints"),
            "total_objects":      count("objects"),
            "total_beacons":      count("beacons"),
            "activated_beacons":  count("beacons", "accessed_at IS NOT NULL"),
            "total_downloads":    count("downloads"),
        }

    # ── Attacker history (new — used by future upgrades) ──────────────────

    def get_attacker_history(self, ip: str) -> dict:
        """
        Return all recorded activity for a single attacker IP.
        New method — not present in the old TinyDB version.
        Used by Upgrade 5 (IP Reputation Scoring) and later.
        """
        conn = self._conn()
        endpoints = conn.execute(
            "SELECT * FROM endpoints WHERE path IN "
            "(SELECT path FROM endpoints) LIMIT 0"  # placeholder until Upgrade 5 adds request_log
        ).fetchall()
        downloads = conn.execute(
            "SELECT * FROM downloads WHERE client_ip=? ORDER BY timestamp DESC",
            (ip,)
        ).fetchall()
        beacons = conn.execute(
            "SELECT * FROM beacons WHERE client_ip=? OR activation_ip=? ORDER BY generated_at DESC",
            (ip, ip)
        ).fetchall()
        return {
            "ip": ip,
            "downloads": [dict(r) for r in downloads],
            "beacons":   [dict(r) for r in beacons],
        }

    # ── Audit Logs ────────────────────────────────────────────────────────

    def log_entry(self, level: str, message: str,
                  event: str = "", client_ip: str = ""):
        """
        Write a structured log entry to the SQLite logs table.
        Called by the SQLiteLogHandler in honeypot.py so that every
        log line written to log_files/api_audit.log is also queryable
        directly in databases/honeypot.db.

        Parameters
        ----------
        level     : 'INFO' | 'WARNING' | 'CRITICAL' | 'ERROR'
        message   : plain-text log message (NOT Base64)
        event     : machine-readable event tag, e.g. 'FILE_DOWNLOAD'
        client_ip : attacker IP extracted from the message when available
        """
        conn = self._conn()
        try:
            conn.execute(
                """
                INSERT INTO logs (timestamp, level, event, message, client_ip)
                VALUES (?, ?, ?, ?, ?)
                """,
                (_now(), level.upper(), event, message, client_ip)
            )
            conn.commit()
        except sqlite3.Error as e:
            # Never let a log write crash the honeypot
            pass

    def get_logs(self, level: str = None, event: str = None,
                 client_ip: str = None, limit: int = 200) -> list[dict]:
        """
        Query the logs table with optional filters.

        Examples
        --------
        state.get_logs()                               # last 200 entries
        state.get_logs(level='CRITICAL')               # critical only
        state.get_logs(event='FILE_DOWNLOAD')          # file downloads only
        state.get_logs(client_ip='10.0.0.1')           # one attacker
        state.get_logs(level='CRITICAL', limit=50)     # critical, newest 50
        """
        conn = self._conn()
        conditions = []
        params = []

        if level:
            conditions.append("level = ?")
            params.append(level.upper())
        if event:
            conditions.append("event = ?")
            params.append(event)
        if client_ip:
            conditions.append("client_ip = ?")
            params.append(client_ip)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params.append(limit)

        rows = conn.execute(
            f"SELECT * FROM logs {where} ORDER BY timestamp DESC LIMIT ?",
            params
        ).fetchall()
        return [dict(r) for r in rows]

    # ── Maintenance ───────────────────────────────────────────────────────

    def _cleanup_old_records(self, days: int):
        """
        Delete records older than `days` days.
        Runs automatically at startup to keep the DB lean.
        Called with retention_days from __init__.
        """
        if days <= 0:
            return  # retention disabled

        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        conn = self._conn()
        try:
            for table, col in [
                ("endpoints", "created_at"),
                ("beacons",   "generated_at"),
                ("downloads", "timestamp"),
                ("objects",   "created_at"),
            ]:
                conn.execute(
                    f"DELETE FROM {table} WHERE {col} < ?", (cutoff,)
                )
            conn.commit()
            logger.info(f"[STATE] Cleaned up records older than {days} days")
        except sqlite3.Error as e:
            logger.error(f"[STATE] Cleanup failed: {e}")

    def close(self):
        """Close the thread-local connection (call on app shutdown)."""
        conn = getattr(_local, "conn", None)
        if conn:
            conn.close()
            _local.conn = None
