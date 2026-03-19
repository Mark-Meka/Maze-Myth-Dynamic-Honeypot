# Audit Logs Guide

Maze Myth writes every event to **two places in parallel**:

| Where | Format | Good for |
|---|---|---|
| `log_files/api_audit.log` | Base64-encoded text lines | Tamper-evident archiving |
| `databases/honeypot.db` → `logs` table | Plain SQL rows | Instant querying, filtering, analysis |

---

## Log Levels

| Level | Meaning |
|-------|---------|
| `INFO` | Normal API access |
| `WARNING` | Suspicious access (admin endpoints, internal paths) |
| `CRITICAL` | High-value targets — secrets, credentials, file downloads |
| `ERROR` | System errors / failed generations |

## Event Tags

The `event` column in the `logs` table contains a short machine-readable tag:

| Tag | Trigger |
|---|---|
| `NEW_ENDPOINT_DISCOVERY` | Attacker hits a new path |
| `FILE_DOWNLOAD` | Attacker downloads a bait file |
| `BEACON_ACTIVATED` | Attacker opened a bait file (beacon fired) |
| `AUTH` | Login attempt |
| `MAZE` | Maze navigation event |

---

## Option A — Query the SQLite Database (Recommended)

The `logs` table in `databases/honeypot.db` stores every log in plain text. No decoding needed.

### Open with DB tool

```bash
# Built-in SQLite CLI
sqlite3 databases/honeypot.db
```

### Useful SQL queries

```sql
-- All logs, newest first
SELECT timestamp, level, event, client_ip, message
FROM logs
ORDER BY timestamp DESC
LIMIT 50;

-- Critical events only
SELECT * FROM logs
WHERE level = 'CRITICAL'
ORDER BY timestamp DESC;

-- All activity from one attacker IP
SELECT * FROM logs
WHERE client_ip = '10.0.0.1'
ORDER BY timestamp;

-- All file download events
SELECT timestamp, client_ip, message FROM logs
WHERE event = 'FILE_DOWNLOAD';

-- All beacon activations (file was opened)
SELECT timestamp, client_ip, message FROM logs
WHERE event = 'BEACON_ACTIVATED';

-- Count events per type
SELECT event, COUNT(*) AS total
FROM logs
WHERE event != ''
GROUP BY event
ORDER BY total DESC;

-- Count hits per attacker IP
SELECT client_ip, COUNT(*) AS hits
FROM logs
WHERE client_ip != ''
GROUP BY client_ip
ORDER BY hits DESC;
```

### Query from Python

```python
import sqlite3

conn = sqlite3.connect("databases/honeypot.db")
conn.row_factory = sqlite3.Row

# Last 20 critical events
rows = conn.execute("""
    SELECT timestamp, level, event, client_ip, message
    FROM logs
    WHERE level = 'CRITICAL'
    ORDER BY timestamp DESC
    LIMIT 20
""").fetchall()

for r in rows:
    print(f"[{r['timestamp']}] {r['level']} | {r['event']} | {r['client_ip']}")
    print(f"  {r['message']}")

conn.close()
```

### Via state_manager (from inside the honeypot)

```python
from src.state import APIStateManager
state = APIStateManager()

# All logs
logs = state.get_logs()

# Filtered
state.get_logs(level='CRITICAL')
state.get_logs(event='FILE_DOWNLOAD')
state.get_logs(client_ip='10.0.0.1')
state.get_logs(level='CRITICAL', limit=50)
```

---

## Option B — Read the Encoded Log File

`log_files/api_audit.log` — each line is a Base64-encoded log entry.

### Decode all lines (Python)

```python
import base64

with open("log_files/api_audit.log", "r") as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                print(base64.b64decode(line).decode("utf-8"))
            except Exception:
                pass
```

### Decode and filter to CRITICAL only

```python
import base64

with open("log_files/api_audit.log", "r") as f:
    for line in f:
        try:
            decoded = base64.b64decode(line.strip()).decode("utf-8")
            if "CRITICAL" in decoded:
                print(decoded)
        except Exception:
            pass
```

### One-liner (PowerShell)

```powershell
Get-Content log_files\api_audit.log | ForEach-Object {
    [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($_))
}
```

### One-liner (Bash/Linux)

```bash
while IFS= read -r line; do echo "$line" | base64 -d; echo; done < log_files/api_audit.log
```

---

## Reading `databases/honeypot.db` — All Tables

The database holds all honeypot state, not just logs.

### Open interactively

```bash
sqlite3 databases/honeypot.db

# Show all tables
.tables

# Show columns of a table
.schema logs
.schema endpoints
.schema downloads
.schema beacons

# Pretty print
.mode column
.headers on
```

### Read all tables (Python)

```python
import sqlite3, json

conn = sqlite3.connect("databases/honeypot.db")
conn.row_factory = sqlite3.Row

# All AI-generated endpoints
endpoints = conn.execute(
    "SELECT path, method, access_count, created_at FROM endpoints ORDER BY access_count DESC"
).fetchall()
for ep in endpoints:
    print(f"{ep['method']:6} {ep['path']} — {ep['access_count']} hits")

# All downloads
downloads = conn.execute(
    "SELECT filename, client_ip, timestamp, is_sensitive FROM downloads ORDER BY timestamp DESC"
).fetchall()
for d in downloads:
    tag = "🔴 SENSITIVE" if d["is_sensitive"] else ""
    print(f"{d['timestamp']}  {d['client_ip']}  {d['filename']} {tag}")

# Active beacons (fired)
beacons = conn.execute(
    "SELECT beacon_id, file_name, client_ip, accessed_at, activation_ip FROM beacons WHERE accessed_at IS NOT NULL"
).fetchall()
for b in beacons:
    print(f"BEACON {b['beacon_id'][:8]}  file={b['file_name']}  downloaded_by={b['client_ip']}  opened_from={b['activation_ip']}")

conn.close()
```

---

## Using the Dashboard (Easiest)

The dashboard at `http://localhost:8002` reads the same `log_files/api_audit.log` and auto-decodes it in real time. No command line needed.

```bash
# API access
curl http://localhost:8002/api/activity   # recent events
curl http://localhost:8002/api/stats      # counts
curl http://localhost:8002/api/downloads  # file downloads
curl http://localhost:8002/api/sensitive  # sensitive downloads only
```

---

## High-Value CRITICAL Triggers

| Access | Endpoint |
|---|---|
| Admin secrets | `/api/v2/admin/secrets` |
| API credentials | `/companies/*/apiCredentials` |
| Internal config | `/internal/config/*` |
| Database config | `/internal/config/database` |
| Backups | `/internal/backups` |

Sensitive file download keywords: `credential`, `secret`, `key`, `password`, `backup`, `config`, `db`, `sqlite`
