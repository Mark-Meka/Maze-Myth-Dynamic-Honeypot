# Project Structure Guide

## Overview
**Maze Myth** is a dynamic banking API honeypot. It generates realistic-looking API endpoints and fake data on demand using Google Gemini AI, tracks every attacker action in a SQLite database, and serves bait files with embedded beacons.

---

## Directory Tree

```
Maze-Myth-Dynamic-Honeypot/
│
├── honeypot.py               ← Main Flask application (all routes)
├── requirements.txt          ← Python packages
├── run_honeypot.bat          ← Windows: double-click to start everything
├── setup_honeypot.py         ← Creates required folders on first run
├── README.md                 ← Project overview and quick start
├── DEPLOYMENT.md             ← Docker / VPS deployment guide
├── SECURITY.md               ← Security notes
├── LICENSE
├── .env.template             ← Copy to .env and add your API key
├── .env                      ← Your secrets (gitignored)
│
├── docker/                   ← Container deployment
│   ├── Dockerfile            ← Multi-stage: `honeypot` + `dashboard` targets
│   ├── docker-compose.yaml   ← One command to start both services
│   └── .dockerignore
│
├── .github/workflows/
│   └── docker-publish.yml    ← Auto-build & push to GHCR on git push
│
├── src/                      ← All core logic lives here
│   │
│   ├── api_generator/        ← Maze routing and access control
│   │   ├── maze_generator.py ← Endpoint validity, access levels, breadcrumbs
│   │   └── http_responses.py ← 401 / 403 / 404 / 500 templates
│   │
│   ├── data_generator/       ← Fake banking data
│   │   └── banking_data.py   ← Generates companies, accounts, transactions, etc.
│   │
│   ├── file_generator/       ← Bait file creation
│   │   ├── generator.py      ← PDF, Excel (.xlsx)
│   │   ├── multi_format_gen.py ← XML, CSV, JSON, JavaScript
│   │   ├── sqlite_gen.py     ← Fake .db / .sqlite databases
│   │   └── txt_gen.py        ← Credential .txt files
│   │
│   ├── llm/                  ← AI response generation
│   │   └── llm_integration.py ← Google Gemini prompts and response handling
│   │
│   ├── rag/                  ← Banking domain context for the LLM
│   │   └── rag_loader.py
│   │
│   └── state/                ← SQLite persistence
│       ├── state_manager.py  ← All DB reads/writes (WAL mode)
│       └── schema.sql        ← Table definitions (reference)
│
├── dashboard/                ← Real-time operator monitoring
│   ├── index.html            ← Dashboard UI (HTML/CSS/JS)
│   └── monitor.py            ← Flask backend, port 8002
│
├── docs/                     ← Team documentation
│   ├── PROJECT_STRUCTURE.md  ← This file
│   ├── FILE_STRUCTURE_GUIDE.md ← Per-file explanations + "which file to edit"
│   └── AUDIT_LOGS_GUIDE.md   ← How to read and query logs
│
├── databases/                ← Runtime (gitignored)
│   └── honeypot.db           ← Single SQLite file for all state
│
├── generated_files/          ← Runtime: bait files served to attackers
└── log_files/                ← Runtime: Base64-encoded audit log
    └── api_audit.log
```

---

## How a Request Flows Through the System

```
Attacker hits any URL
        │
        ▼
honeypot.py receives it
        │
        ├─→ Fixed route? (e.g. /api/v1/accounts)
        │       └─→ BankingDataGenerator generates fresh data
        │               └─→ Return JSON response
        │
        └─→ Dynamic catch-all (unknown path)
                │
                ├─→ maze_generator validates path & assigns access level
                │
                ├─→ LLMGenerator calls Gemini API with path context
                │       └─→ Returns realistic JSON
                │
                ├─→ 20% chance: FileGenerator creates a bait file
                │       └─→ Beacon ID saved to SQLite beacons table
                │
                ├─→ Response saved to SQLite endpoints table
                │       (same URL → same AI response forever)
                │
                └─→ Return JSON + optional _attachments download link
```

---

## Data Flow — Logs

```
logger.critical("FILE_DOWNLOAD ...")
        │
        ├─→ EncodedFileHandler  →  log_files/api_audit.log  (Base64)
        ├─→ SQLiteLogHandler    →  databases/honeypot.db → logs table (plain SQL)
        └─→ StreamHandler       →  Console (plain text)
```

---

## Key Components Explained

### `honeypot.py`
The entry point. Top section has ~20 fixed routes that always return fresh dynamic data (accounts, transactions, etc.). Bottom section has one `/<path:full_path>` catch-all route that handles everything else by calling the LLM and maze logic.

### `src/state/state_manager.py`
The single point of contact for the database. All reads and writes go through here. The `APIStateManager` class uses thread-local SQLite connections and WAL mode so multiple gunicorn workers can read/write concurrently without conflicts.

**Tables:**
| Table | Purpose |
|---|---|
| `endpoints` | LLM-generated responses per `(path, method)` — consistent fake data |
| `objects` | Typed fake objects reused across sessions |
| `beacons` | Bait file tokens — tracks download and open events |
| `downloads` | Every `/download/*` hit with IP and user agent |
| `logs` | Full structured audit log (level, event, IP, message) |

### `src/llm/llm_integration.py`
Sends a prompt to Gemini like: *"Generate a realistic JSON response for a banking API at GET /api/v2/admin/users, access_level=admin"*. Returns a JSON string that is saved to the `endpoints` table and returned to the attacker.

### `dashboard/monitor.py`
A separate Flask app (port 8002) that reads `log_files/api_audit.log`, decodes the Base64 lines, and serves them as JSON for the dashboard UI. The operator leaves this open during an engagement.

---

## Running the System

### Windows (quickest)
```cmd
run_honeypot.bat
```
Opens two windows — dashboard on 8002, honeypot on 8001.

### Docker (production)
```bash
cp .env.template .env
# Edit .env: add GEMINI_API_KEY
docker compose -f docker/docker-compose.yaml up -d
```

### Manual (any OS)
```bash
# Terminal 1
python honeypot.py

# Terminal 2
python dashboard/monitor.py
```

---

## Ports

| Port | Service | Audience |
|---|---|---|
| **8001** | Honeypot API | **Attackers** — expose this to the internet |
| **8002** | Dashboard | **Operators only** — never expose publicly |
