# File Structure Guide

> **Which file do I edit?** — Per-file explanations and quick-decision tables for every module in Maze Myth.

---

## 🗺️ Quick Decision Table

| What you want to change | File(s) to edit |
|------------------------|-----------------|
| Add a new fixed API route | `honeypot.py` |
| Change upload trap endpoints / logic | `src/file_upload_rce.py` |
| Change webshell payload patterns detected | `src/file_upload_rce.py` → `_WEBSHELL_PATTERNS` |
| Change AI shell responses (ls, cat, etc.) | `src/rag/shell_rag_loader.py` → `_llm()` prompt |
| Change static ground-truth command responses | `src/rag/shell_rag_loader.py` → `_get_fallback_ground_truth()` |
| Change the fake server identity (hostname, IP, pwd) | `src/rag/shell_rag_loader.py` → `_DEFAULT_IDENTITY` |
| Change attacker phase classification | `src/attacker_intel.py` → `_CMD_RISK_TABLE` |
| Change per-IP engagement scoring | `src/attacker_intel.py` → `AttackerSession._update_engagement()` |
| Change IP geolocation provider | `src/attacker_intel.py` → `_geolocate()` |
| Change deception advisor hints | `src/attacker_intel.py` → `_deception_strategy()` |
| Change how AI generates API responses | `src/llm/llm_integration.py` |
| Change API maze access levels | `src/api_generator/maze_generator.py` |
| Change 401 / 403 / 404 responses | `src/api_generator/http_responses.py` |
| Add or change banking data fields | `src/data_generator/banking_data.py` |
| Add a new bait file format | `src/file_generator/` — add generator |
| Change PDF / Excel bait content | `src/file_generator/generator.py` |
| Change XML / CSV / JSON / JS bait content | `src/file_generator/multi_format_gen.py` |
| Change SQLite bait database content | `src/file_generator/sqlite_gen.py` |
| Change the Gemini API prompts (banking paths) | `src/llm/llm_integration.py` |
| Add new banking RAG context | `src/rag/` files |
| Add a new DB table / query method | `src/state/state_manager.py` |
| Change log encoding or handlers | `honeypot.py` → `EncodedFileHandler` / `SQLiteLogHandler` |
| Change dashboard UI look | `dashboard/index.html` |
| Add dashboard API endpoint | `dashboard/monitor.py` |
| Change Docker build steps or Gunicorn workers | `docker/Dockerfile` |
| Change environment variables | `.env.template` |
| Change Windows startup behaviour | `run_honeypot.bat` |

---

## 📁 Root Files

| File | What it does |
|------|-------------|
| `honeypot.py` | **Main application.** All HTTP routes + log handlers. CVE shim routes registered first, dynamic catch-all at bottom. ~1050 lines. Gunicorn-compatible WSGI entry point. |
| `requirements.txt` | Python packages. Run `pip install -r requirements.txt`. |
| `run_honeypot.bat` | Windows launcher. Starts honeypot (8001) + dashboard (8002). |
| `setup_honeypot.py` | Creates `databases/`, `generated_files/`, `log_files/` on first run. |
| `DEPLOYMENT.md` | Docker and VPS deployment guide. |
| `ATTACK_GUIDE.md` | Red-team testing guide — how to trigger every trap. |
| `.env.template` | Template for environment variables. Copy to `.env`. |
| `.env` | Your secrets (`GEMINI_API_KEY`, `LLM_MODEL`). Gitignored. |

---

## 📦 Source Modules (`src/`)

---

### `src/file_upload_rce.py` — CVE-2020-36179 Deception Module ⭐

Implements the fake file upload vulnerability trap simulating CVE-2020-36179 (Jackson/Spring multipart RCE).
**No real files are ever written to disk.**

**Registered routes:**

| Route | Method | What it does |
|-------|--------|-------------|
| `/api/v2/documents/compliance-upload` | GET | Spring Java compliance portal upload form |
| `/api/v2/documents/compliance-upload` | POST | Spring upload handler |
| `/clientportal/support/attachments.php` | GET | PHP bank client portal upload form |
| `/clientportal/support/attachments.php` | POST | PHP upload handler |
| `/uploads/<filename>` | GET | Webshell execution trap (only `_shell_registry` filenames accepted) |
| `/api/dashboard/cve/file-upload` | GET | Full attacker intel summary |
| `/api/dashboard/cve/file-upload/attackers` | GET | All attacker profiles |
| `/api/dashboard/cve/file-upload/attacker/<ip>` | GET | Per-IP deep profile |

**Key functions:**

| Function | What it does |
|----------|-------------|
| `_route_spring_upload_get()` | Returns Spring compliance portal HTML form with Apache-Coyote headers |
| `_route_php_upload_get()` | Returns PHP bank client portal HTML form with Apache/PHP headers |
| `_handle_upload()` | Reads ≤512 bytes, runs 13-pattern webshell check, runs 18-tag file analysis, registers in `_shell_registry` |
| `_contains_webshell_code()` | 13-pattern regex check (`<?php`, `system(`, `eval(`, `passthru(`, `$_GET[`, etc.) |
| `_analyze_file()` | 18-pattern analysis → threat level (LOW/MEDIUM/HIGH/CRITICAL), extension risk, payload tags |
| `_route_webshell_get()` | Webshell execution trap — delegates to `shell_rag_loader.resolve_shell_command()` |
| `register_file_upload_routes(app)` | Registers all routes + inits RAG loader |

**Deceptive headers:**

| Portal | Server | X-Powered-By |
|--------|--------|-------------|
| Spring | `Apache-Coyote/1.1` | `Spring Framework 5.3.9` |
| PHP | `Apache/2.4.54 (Debian)` | `PHP/7.4.33` |

**Dangerous extensions:** `.php`, `.php3`–`.php5`, `.phtml`, `.phar`, `.jsp`, `.jspx`, `.aspx`, `.asp`, `.cfm`, `.py`, `.rb`, `.pl`, `.sh`, `.bash`, `.cgi`

---

### `src/attacker_intel.py` — Intelligence Engine ⭐

Per-IP attacker profiling. Fully in-memory (no DB write on every event — fast).

**Key components:**

| Component | What it does |
|-----------|-------------|
| `AttackerSession` | Full per-IP profile: timeline, commands, files, phase, engagement score (0–100) |
| `_CMD_RISK_TABLE` | 25+ shell command patterns → (risk 0–100, attack phase, label) |
| `_FILE_PATTERNS` | 18 byte-regex patterns → payload tags (`PHP_OPENER`, `TCP_REVSHELL`, `JAVA_RCE`, etc.) |
| `_DANGEROUS_EXT` | 17 extension strings triggering CRITICAL alert on upload |
| `_classify_command(cmd)` | Returns risk score + phase + label for any shell command |
| `_analyze_file(bytes, filename)` | Returns threat level, extension risk, payload tags, has_revshell, has_eval |
| `_geolocate(ip)` | Free IP lookup (ip-api.com), skips private IPs, in-memory cache |
| `_deception_strategy(session)` | Returns up to 3 phase-specific deception hints |
| `dashboard_summary()` | Full aggregated intelligence for the dashboard API |

**Attack phases and engagement scoring:**

| Phase | Risk range | Engagement delta | Typical commands |
|-------|-----------|-----------------|-----------------|
| `IDLE` | — | +1 | Just connected |
| `RECON` | 15–35 | +risk/5 | `whoami`, `id`, `ls`, `ps aux`, `ifconfig`, `env` |
| `EXPLOIT` | 45–80 | +risk/5 | `sudo -l`, `cat /etc/shadow`, `wget`, `useradd` |
| `POST_EXPLOIT` | 85–95 | +risk/5 | `bash -i >& /dev/tcp/`, `nc -e /bin/bash`, `msfvenom` |
| `LATERAL` | 65–80 | +risk/5 | `ssh user@host`, `crontab -e`, `scp`, `rsync` |

| Event type | Engagement delta |
|-----------|----------------|
| `FORM_VIEW` | +2 |
| `UPLOAD_SAFE` | +5 |
| `UPLOAD_SHELL` | +25 |
| `WEBSHELL_EXEC` | +15 |
| `CMD` | +risk_score / 5 |

**Public API:**

```python
from src import attacker_intel as intel

intel.record_form_view(ip, endpoint)
intel.record_upload(ip, filename, raw_bytes, endpoint)
intel.record_command(ip, cmd, output)
intel.record_webshell_access(ip, filename, cmd, output)
intel.get_session(ip)        # → full per-IP dict
intel.get_all_sessions()     # → list[dict]
intel.dashboard_summary()    # → global dashboard dict
```

---

### `src/rag/shell_rag_loader.py` — Hybrid Shell Engine ⭐

Resolves shell commands with a **6-step pipeline**, always returning a string.

**Important**: In the current implementation, **Gemini LLM is called first** (step 1 — primary engine), with cache and TF-IDF as offline fallbacks. This means every `ls`, `cat`, `find`, or novel command gets a **fresh, realistic, dynamically generated response**.

**Key behaviors powered by Gemini:**
- **`ls <any directory>`**: Gemini generates a full directory listing with real timestamps, inodes, www-data ownership, and context-appropriate filenames
- **`cat <php file>`**: Gemini generates realistic PHP banking application source code with embedded DB credentials
- **`cat <config file>`**: Gemini generates plausible Apache/PHP config, `.env` files, cronjobs
- **Any unknown command**: Gemini generates authentic-looking output as a compromised Ubuntu 22.04 server

**Fake server identity** (embedded in all Gemini prompts):

| Field | Value |
|-------|-------|
| Hostname | `bankcorpweb-02.internal` |
| IP | `10.0.1.52` |
| User | `www-data` (uid=33) |
| CWD | `/var/www/html/clientportal/support` |
| DB host | `db-primary-1.internal` |
| DB name | `bankcorp_prod` |

**Resolution pipeline:**

```
1. Gemini LLM     — Primary (always called if enabled; generates dynamic unique output)
2. Exact cache    — 58 ground-truth commands (Gemini-bootstrapped at startup)
3. Case-insensitive exact match
4. Dynamic handler — echo, cd, touch, mkdir, chmod (silent), revshell (1.5–3s delay + random error)
5. TF-IDF fuzzy   — Cowrie 235-session dataset (threshold ≥ 0.85)
6. Fallback       — "bash: <cmd>: command not found"
```

**Startup bootstrapping:**
On init, if Gemini is enabled, it pre-generates all 58 ground-truth responses in a single batch API call, producing server-specific output (hostname, IP, CWD, DB creds) before any attacker connects.

**Key functions:**

| Function | What it does |
|----------|-------------|
| `init(pkl_path, json_path, api_key)` | Load data, build TF-IDF, configure Gemini, bootstrap ground-truth. Idempotent. |
| `resolve_shell_command(cmd)` | Full 6-step pipeline — always returns a string |
| `get_metadata()` | Returns loader status: cache size, TF-IDF enabled, LLM enabled |

---

### `src/api_generator/` — Maze Logic

| File | What it does | Edit when... |
|------|-------------|-------------|
| `maze_generator.py` | Validates paths, assigns access levels (public/user/admin), generates breadcrumb hints. API structure defined inline (no external JSON file). | Adding access levels, changing valid endpoint patterns |
| `http_responses.py` | Returns 401 / 403 / 404 / 500 JSON templates with realistic banking error messages | Changing error response appearance |

---

### `src/data_generator/banking_data.py` — Dynamic Banking Data ⭐

Generates fresh, randomized data on **every request** using `Faker` + `random`.
If Gemini is enabled (`banking_data.llm = llm`), it can also generate AI-enriched content.

| Method | Returns | Count per call |
|--------|---------|---------------|
| `generate_companies()` | Company dicts (name, id, balance, status, sector) | 8–20 |
| `generate_accounts()` | Account dicts (IBAN, type, balance, currency, status) | 15–40 |
| `generate_transactions()` | Transaction dicts (amount, from/to, timestamp, status) | 20–100 |
| `generate_payments()` | Payment dicts (reference, method, status, merchant) | 10–35 |
| `generate_users()` | Admin user dicts (name, role, last_login, permissions) | 5–15 |
| `generate_secrets()` | Fake secrets (API keys, tokens, credentials) | 10 |
| `generate_merchants()` | Merchant dicts (name, MCC, terminal count) | varies |
| `generate_terminals()` | POS terminal dicts (serial, location, status) | varies |

---

### `src/file_generator/` — Bait Files with Beacons

Every file gets a unique **beacon ID** embedded. When the attacker opens it, the beacon calls back.

| File | Formats | Beacon method |
|------|---------|--------------|
| `generator.py` | PDF, Excel (.xlsx) | URL in PDF footer / hyperlink in Excel cell |
| `multi_format_gen.py` | XML, CSV, JSON, JavaScript | `<beacon>` tag / URL column / `_beacon_url` / `fetch()` |
| `sqlite_gen.py` | .db / .sqlite | Row in `_tracking` table |
| `txt_gen.py` | .txt credentials | URL at bottom |

---

### `src/llm/llm_integration.py` — Banking API AI

Calls Gemini to generate realistic JSON for unknown API paths. Result saved to SQLite `endpoints` table.

**Methods:**

| Method | What it does |
|--------|-------------|
| `generate_api_response(path, method, context, rag_context)` | Primary: generates realistic banking JSON for any unknown path |
| `generate_endpoint_description(path, method)` | Generates Swagger/OpenAPI documentation for a path |
| `generate_file_content(file_type)` | Generates bait file content (PDF/Excel/env formats) |
| `generate_structured_data(prompt, format)` | Generic helper: returns JSON, CSV, XML, SQL, JS — strips markdown |

**Model**: Configured via `LLM_MODEL` env var (default: `gemini-2.5-flash`).
Auto-loads API key from `.env` or `.env.template`.

---

### `src/state/state_manager.py` — SQLite Persistence

All honeypot state in a single `databases/honeypot.db` (WAL mode).
Migrated from TinyDB; thread-safe via `threading.local()` connections per thread.

**SQLite tables:**

| Table | Stores | Key methods |
|-------|--------|------------|
| `endpoints` | AI-generated responses per `(path, method)` — unique constraint | `save_endpoint()`, `get_endpoint()`, `endpoint_exists()` |
| `objects` | Typed fake objects reused across sessions | `save_object()`, `get_objects_by_type()` |
| `beacons` | Bait file tokens — download + open tracking | `save_beacon()`, `activate_beacon()` |
| `downloads` | Every `/download/*` hit (IP, UA, is_sensitive flag) | `log_download()`, `get_downloads()`, `get_sensitive_downloads()` |
| `logs` | Structured audit log (level, event, IP, message) | `log_entry()`, `get_logs()` |

**Maintenance**: `_cleanup_old_records(90)` runs at startup and deletes records > 90 days old.

---

## 🔒 Log Architecture — Dual-Write System

Every event is written to **two places simultaneously** in `honeypot.py`:

```python
# 1. EncodedFileHandler → log_files/api_audit.log
#    Base64-encodes every line before writing — resists casual tampering
encoded_msg = base64.b64encode(msg.encode('utf-8')).decode('utf-8')

# 2. SQLiteLogHandler → databases/honeypot.db → logs table
#    Plain-text structured entry — fully queryable by level/event/IP
state.log_entry(level, message, event, client_ip)
```

**Decoding a log line:**
```python
import base64
# Read a line from log_files/api_audit.log
decoded = base64.b64decode(line.strip()).decode('utf-8')
```

---

## 🐳 Production Deployment — Docker + Gunicorn

| Component | Detail |
|-----------|--------|
| **Dockerfile** | Multi-stage: `builder` compiles C extensions, `base` is 90MB runtime image |
| **Non-root user** | All processes run as `honeypot` uid=1001 — never root |
| **Gunicorn** | 4 workers × 2 threads (honeypot); 2 workers (dashboard); 120s LLM timeout |
| **Health checks** | Both services: `curl -sf http://localhost:{port}/` every 30s |
| **Named volumes** | `honeypot-logs`, `honeypot-db`, `honeypot-files` — persist across restarts |
| **Dashboard isolation** | Mounts volumes as `:ro` (read-only) — can't modify honeypot state |
| **Auto-restart** | `restart: unless-stopped` on both services |
| **Network** | `maze-net` bridge network — services isolated from host |

---

## 📊 Dashboard (`dashboard/`)

| File | What it does |
|------|-------------|
| `index.html` | Full dashboard UI — polls backend every few seconds |
| `monitor.py` | Flask backend on port 8002; Gunicorn-compatible |

**Standard Dashboard API (port 8002):**

| Endpoint | Returns |
|----------|---------|
| `GET /` | Dashboard UI |
| `GET /api/activity` | Last 100 decoded log entries |
| `GET /api/new` | New entries since last poll |
| `GET /api/stats` | Totals (endpoints, downloads, beacons) |
| `GET /api/downloads` | All file download records |
| `GET /api/sensitive` | Sensitive file downloads only |

**CVE Intelligence API (port 8001 — served by honeypot):**

| Endpoint | Returns |
|----------|---------|
| `GET /api/dashboard/cve/file-upload` | Global summary (all IPs, phase dist, top commands) |
| `GET /api/dashboard/cve/file-upload/attackers` | All attacker profiles, sorted by engagement |
| `GET /api/dashboard/cve/file-upload/attacker/<ip>` | Per-IP deep profile (geo, timeline, files, deception hints) |

---

## 🗄️ Runtime Directories (auto-created, gitignored)

| Directory | Contents |
|-----------|---------|
| `databases/` | `honeypot.db` — SQLite WAL mode, 5 tables, 90-day retention |
| `generated_files/` | Bait files served to attackers |
| `log_files/` | `api_audit.log` — Base64-encoded structured audit log |
| `Dataset/` | `shell_rag.pkl` + `ai_cmd_cache.json` — Cowrie training data |
