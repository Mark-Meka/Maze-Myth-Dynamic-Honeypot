# Project Structure Guide

## Overview

**Maze Myth** is a dynamic banking API honeypot with three deception layers:

1. **Dynamic API Maze** — AI-generated banking endpoints with unique randomized data on every request, infinite path generation, and 10+ bait file formats with tracking beacons
2. **CVE-2020-36179 Trap** — Fake file upload RCE simulating a vulnerable Spring/PHP banking portal; accepts real webshell payloads, registers them in-memory, responds with AI-generated terminal output
3. **Attacker Intelligence Engine** — Per-IP behavioral profiling: geo lookup, attack phase machine (IDLE→RECON→EXPLOIT→POST_EXPLOIT→LATERAL), 25+ command risk patterns, 18 file payload tags, engagement scoring, and a deception strategy advisor

---

## Directory Tree

```
Maze-Myth-Dynamic-Honeypot/
│
├── honeypot.py                    ← Main Flask application (all routes, ~950 lines)
├── requirements.txt               ← Python packages
├── run_honeypot.bat               ← Windows: double-click to start everything
├── setup_honeypot.py              ← Creates required runtime folders on first run
├── README.md                      ← Project overview + architecture + all flow diagrams
├── DEPLOYMENT.md                  ← Docker / VPS deployment guide
├── ATTACK_GUIDE.md                ← Red-team guide: how to trigger all traps
├── SECURITY.md                    ← Security notes and isolation requirements
├── LICENSE
├── .env.template                  ← Copy to .env and add your API key
├── .env                           ← Your secrets: GEMINI_API_KEY (gitignored)
│
├── docker/
│   ├── Dockerfile                 ← Multi-stage: `honeypot` + `dashboard` targets
│   ├── docker-compose.yaml        ← One-command production launch
│   └── .dockerignore
│
├── .github/workflows/
│   └── docker-publish.yml         ← CI: auto-build & push to GHCR
│
├── Dataset/                       ← Model data (gitignored)
│   ├── shell_rag.pkl              ← Cowrie-trained command→response model
│   └── ai_cmd_cache.json          ← Gemini-generated command response cache
│
├── src/                           ← All core source modules
│   │
│   ├── file_upload_rce.py         ← CVE-2020-36179 deception module ⭐
│   │                                 Spring + PHP upload portals, webshell trap,
│   │                                 shell registry, deception headers, intel API routes
│   │
│   ├── attacker_intel.py          ← Attacker behaviour profiling engine ⭐
│   │                                 Per-IP session, phase machine, geo, engagement score,
│   │                                 command risk scoring, file analysis, deception advisor
│   │
│   ├── api_generator/             ← Maze routing and access control
│   │   ├── maze_generator.py      ← Endpoint validity, access levels (public/user/admin),
│   │   │                             breadcrumb hints, inline API structure seed
│   │   └── http_responses.py      ← 401 / 403 / 404 / 500 realistic banking templates
│   │
│   ├── data_generator/            ← Dynamic fake banking data
│   │   └── banking_data.py        ← BankingDataGenerator: companies, accounts, transactions,
│   │                                 payments, users, merchants, terminals, secrets
│   │                                 Faker + random — unique data on every request
│   │
│   ├── file_generator/            ← Bait file creation with beacon tracking
│   │   ├── generator.py           ← PDF (ReportLab), Excel/XLSX (openpyxl)
│   │   ├── multi_format_gen.py    ← XML, CSV, JSON, JavaScript
│   │   ├── sqlite_gen.py          ← Fake .db / .sqlite databases with _tracking table
│   │   └── txt_gen.py             ← Credential .txt files
│   │
│   ├── llm/                       ← AI response generation
│   │   └── llm_integration.py     ← Google Gemini prompts for banking API responses;
│   │                                 result cached in SQLite endpoints table
│   │
│   ├── rag/                       ← RAG context and shell command resolution
│   │   ├── rag_loader.py          ← Banking domain context for API response LLM prompts
│   │   ├── shell_rag_loader.py    ← 6-step hybrid shell engine ⭐
│   │   │                             (cache→case→dynamic→TF-IDF→Gemini→fallback)
│   │   └── shell_rag.pkl          ← Cowrie-trained model (symlink/copy from Dataset/)
│   │
│   └── state/                     ← SQLite persistence layer
│       ├── state_manager.py       ← All DB reads/writes (WAL mode); log handlers;
│       │                             endpoints, beacons, downloads, logs tables
│       └── schema.sql             ← Table definitions (reference only)
│
├── dashboard/                     ← Real-time operator monitoring
│   ├── index.html                 ← Dashboard UI (port 8002) — polls backend every ~3s
│   └── monitor.py                 ← Flask backend; serves activity, stats, downloads APIs
│
├── docs/                          ← Team documentation
│   ├── PROJECT_STRUCTURE.md       ← This file
│   ├── FILE_STRUCTURE_GUIDE.md    ← Per-file explanations + "which file to edit" table
│   └── AUDIT_LOGS_GUIDE.md        ← How to read, decode, and query audit logs
│
├── databases/                     ← Runtime state (gitignored)
│   └── honeypot.db                ← Single SQLite file (WAL mode) for all state
│
├── generated_files/               ← Runtime: bait files served to attackers (gitignored)
└── log_files/                     ← Runtime: audit log (gitignored)
    └── api_audit.log              ← Base64-encoded structured log
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
        │       └─→ BankingDataGenerator generates fresh randomized data
        │               └─→ Return JSON — unique on every request
        │
        ├─→ /download/<filename>?
        │       └─→ FileGenerator creates tracked bait file
        │               └─→ Beacon ID logged to downloads table
        │                       └─→ CRITICAL alert logged
        │
        └─→ Dynamic catch-all (unknown path)
                │
                ├─→ maze_generator validates path & assigns access level
                │       (public / user / admin based on path structure)
                │
                ├─→ LLMGenerator calls Gemini with path + banking context
                │       └─→ Returns realistic JSON for this path
                │
                ├─→ 20% chance: FileGenerator creates bait file
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
        ├─→ attacker_intel.record_form_view(ip, endpoint)
        └─→ Return PHP upload form (Apache/2.4.54 + PHP/7.4.33 headers)

GET /api/v2/documents/compliance-upload
        ├─→ attacker_intel.record_form_view(ip, endpoint)
        └─→ Return Spring upload form (Apache-Coyote + Spring Framework headers)

POST /clientportal/support/attachments.php  (file=shell.php)
        ├─→ Read ≤512 bytes from uploaded file
        ├─→ _contains_webshell_code() → 13 regex patterns checked
        ├─→ _analyze_file() → 18 payload tags, extension risk, threat level
        ├─→ attacker_intel.record_upload(ip, filename, bytes, endpoint)
        │       → UPLOAD_SHELL event (threat_level=CRITICAL) or UPLOAD_SAFE
        ├─→ Register filename in _shell_registry (NEVER write to disk)
        └─→ Return success page with /uploads/shell.php URL

GET /uploads/shell.php?cmd=whoami
        ├─→ Guard: filename must be in _shell_registry
        ├─→ attacker_intel.record_webshell_access(ip, cmd, output)
        ├─→ shell_rag_loader.resolve_shell_command("whoami")
        │       1. Exact cache match (58 ground-truth commands)
        │       2. Case-insensitive exact match
        │       3. Dynamic handler (echo/cat/grep/ls/revshell → 1.5s hang + EOF)
        │       4. TF-IDF fuzzy match on Cowrie 235-session dataset (threshold 0.40)
        │       5. Gemini LLM (live generation, cached per session)
        │       6. Fallback: "bash: cmd: command not found"
        └─→ Return: "www-data"

GET /api/dashboard/cve/file-upload
        └─→ attacker_intel.dashboard_summary() → full JSON: stats, phase dist,
                top attackers by engagement, dangerous commands, recent events
```

### Attacker Intelligence — Data Produced Per IP

```
Every event (upload, webshell exec, form view, command) →

attacker_intel.AttackerSession
        ├─→ timeline: [{type, ts, data}]     ← all events chronologically
        ├─→ commands: [{cmd, risk_score, phase, label, output}]
        ├─→ files:    [{filename, ext, threat_level, payload_tags, has_revshell}]
        ├─→ current_phase: IDLE|RECON|EXPLOIT|POST_EXPLOIT|LATERAL
        ├─→ engagement_score: 0-100
        └─→ geo: {country, city, ISP, ASN, lat, lon, is_proxy, is_hosting}

dashboard_summary() aggregates all sessions:
        ├─→ stats: {unique_attackers, total_uploads, webshell_uploads,
        │           total_commands, revshell_attempts, wrong_ext_uploads}
        ├─→ phase_distribution: {IDLE: N, RECON: N, ...}
        ├─→ top_attackers: [top 10 by engagement_score]
        ├─→ top_dangerous_commands: [top 20 by risk_score]
        └─→ recent_events: [last 30 events across all sessions]
```

---

## Data Flow — Logging

```
Every event in honeypot.py or file_upload_rce.py calls _log_event()
        │
        ├─→ EncodedFileHandler  → log_files/api_audit.log  (Base64-encoded JSON)
        ├─→ SQLiteLogHandler    → databases/honeypot.db → logs table
        └─→ StreamHandler       → Console (color-coded by level)

Every event in file_upload_rce.py also calls attacker_intel.*()
        └─→ In-memory session store (per-IP AttackerSession objects)
                └─→ GET /api/dashboard/cve/file-upload serves live data
```

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
LLM_MODEL=gemini-2.0-flash
```

---

## Running the System

### Windows (one click)
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
# Terminal 1 — Honeypot
python honeypot.py

# Terminal 2 — Dashboard
python dashboard/monitor.py
```
