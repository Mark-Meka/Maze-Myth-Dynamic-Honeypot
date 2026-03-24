# Project Structure Guide

## Overview
**Maze Myth** is a dynamic banking API honeypot with three deception layers:
1. **Dynamic API Maze** — AI-generated banking endpoints that never repeat
2. **CVE-2020-36179 Trap** — Fake file upload RCE that accepts webshells and responds with AI-generated shell output
3. **Attacker Intelligence Engine** — Per-IP behavioural profiling, geo lookup, phase classification, and deception strategy advisor

---

## Directory Tree

```
Maze-Myth-Dynamic-Honeypot/
│
├── honeypot.py                    ← Main Flask application (all routes)
├── requirements.txt               ← Python packages
├── run_honeypot.bat               ← Windows: double-click to start everything
├── setup_honeypot.py              ← Creates required folders on first run
├── README.md                      ← Project overview + attack flow diagrams
├── DEPLOYMENT.md                  ← Docker / VPS deployment guide
├── ATTACK_GUIDE.md                ← Red-team guide: how to trigger all traps
├── SECURITY.md                    ← Security notes
├── LICENSE
├── .env.template                  ← Copy to .env and add your API key
├── .env                           ← Your secrets (gitignored)
│
├── docker/
│   ├── Dockerfile                 ← Multi-stage: `honeypot` + `dashboard` targets
│   ├── docker-compose.yaml        ← One-command production launch
│   └── .dockerignore
│
├── .github/workflows/
│   └── docker-publish.yml         ← CI: auto-build & push to GHCR
│
├── Dataset/                       ← Training data (gitignored)
│   ├── shell_rag.pkl              ← Trained dataset command→response model
│   └── ai_cmd_cache.json          ← Gemini-generated command responses
│
├── src/                           ← All core modules
│   │
│   ├── file_upload_rce.py         ← CVE-2020-36179 deception module
│   ├── attacker_intel.py          ← Attacker behaviour profiling engine
│   │
│   ├── api_generator/             ← Maze routing and access control
│   │   ├── maze_generator.py      ← Endpoint validity, access levels, breadcrumbs
│   │   └── http_responses.py      ← 401 / 403 / 404 / 500 templates
│   │
│   ├── data_generator/            ← Fake banking data
│   │   └── banking_data.py        ← Companies, accounts, transactions, secrets
│   │
│   ├── file_generator/            ← Bait file creation
│   │   ├── generator.py           ← PDF, Excel (.xlsx)
│   │   ├── multi_format_gen.py    ← XML, CSV, JSON, JavaScript
│   │   ├── sqlite_gen.py          ← Fake .db / .sqlite databases
│   │   └── txt_gen.py             ← Credential .txt files
│   │
│   ├── llm/                       ← AI response generation
│   │   └── llm_integration.py     ← Google Gemini prompts and response handling
│   │
│   ├── rag/                       ← RAG context loaders
│   │   ├── rag_loader.py          ← Banking domain context for API LLM
│   │   ├── shell_rag_loader.py    ← Hybrid shell command engine
│   │   └── shell_rag.pkl          ← Rag-trained model (copy from Dataset/)
│   │
│   └── state/                     ← SQLite persistence
│       ├── state_manager.py       ← All DB reads/writes (WAL mode)
│       └── schema.sql             ← Table definitions (reference)
│
├── dashboard/                     ← Real-time operator monitoring
│   ├── index.html                 ← Dashboard UI (port 8002)
│   └── monitor.py                 ← Flask backend, port 8002
│
├── docs/                          ← Team documentation
│   ├── PROJECT_STRUCTURE.md       ← This file
│   ├── FILE_STRUCTURE_GUIDE.md    ← Per-file explanations + "which file to edit"
│   └── AUDIT_LOGS_GUIDE.md        ← How to read and query logs
│
├── databases/                     ← Runtime: gitignored
│   └── honeypot.db                ← Single SQLite file for all state
│
├── generated_files/               ← Runtime: bait files served to attackers
└── log_files/                     ← Runtime: Base64-encoded audit log
    └── api_audit.log
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
        ├─→ CVE upload routes? (explicit shims registered first)
        │       └─→ file_upload_rce.py handles it → see below
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

### CVE-2020-36179 Upload Trap

```
GET /clientportal/support/attachments.php
        └─→ Show realistic PHP upload form
               └─→ attacker_intel.record_form_view(ip)

POST /clientportal/support/attachments.php  (file=shell.php)
        ├─→ _contains_webshell_code() → detect PHP payload patterns
        ├─→ _analyze_file() → 18 pattern tags, extension risk, threat level
        ├─→ attacker_intel.record_upload(ip, filename, bytes)
        ├─→ Register filename in _shell_registry (NEVER write to disk)
        └─→ Return success page with /uploads/shell.php URL

GET /uploads/shell.php?cmd=whoami
        ├─→ Guard: filename must be in _shell_registry
        ├─→ attacker_intel.record_webshell_access(ip, cmd)
        ├─→ shell_rag_loader.resolve_shell_command("whoami")
        │       1. Exact cache (58 ground-truth commands)
        │       2. Case-insensitive exact match
        │       3. Dynamic handler (echo/cat/grep/ls/revshell patterns)
        │       4. TF-IDF fuzzy match (Cowrie dataset)
        │       5. Gemini LLM (cached per session)
        │       6. bash: cmd: command not found
        └─→ Return: "www-data"
```

---

## Data Flow — Logs

```
Every event (upload, webshell hit, form view)
        │
        ├─→ _log_event() → _logger.critical/warning/info()
        │       ├─→ EncodedFileHandler → log_files/api_audit.log (Base64)
        │       ├─→ SQLiteLogHandler  → databases/honeypot.db → logs table
        │       └─→ StreamHandler     → Console
        │
        └─→ attacker_intel module (in-memory session store)
                └─→ GET /api/dashboard/cve/file-upload
```

---

## Ports

| Port | Service | Audience |
|------|---------|----------|
| **8001** | Honeypot API + CVE traps | **Attackers** — expose this |
| **8002** | Monitoring Dashboard | **Operators only** — never expose |

---

## Running the System

### Windows
```cmd
run_honeypot.bat
```

### Docker (production)
```bash
cp .env.template .env
# Edit .env: GEMINI_API_KEY=your_key
docker compose -f docker/docker-compose.yaml up -d
```

### Manual
```bash
# Terminal 1
python honeypot.py
# Terminal 2
python dashboard/monitor.py
```
