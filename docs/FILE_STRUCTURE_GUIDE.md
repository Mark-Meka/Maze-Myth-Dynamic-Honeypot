# File Structure Guide
> **For team members:** This guide explains every file in the project and — most importantly — **which file to edit when you want to make a specific change.**

---

## 🗺️ Quick Decision Table — "Which file do I edit?"

| What you want to change | File(s) to edit |
|---|---|
| Add a new fixed API route (e.g. `/api/v3/cards`) | `honeypot.py` |
| Change how AI generates endpoint responses | `src/llm/llm_integration.py` |
| Change access levels / breadcrumbs / endpoint validity | `src/api_generator/maze_generator.py` |
| Change what 401 / 403 / 404 responses look like | `src/api_generator/http_responses.py` |
| Add or change generated banking data (accounts, txns, etc.) | `src/data_generator/banking_data.py` |
| Add a new bait file format (e.g. `.docx`) | `src/file_generator/` — add a new generator |
| Change PDF / Excel bait file content | `src/file_generator/generator.py` |
| Change XML / CSV / JSON / JS bait file content | `src/file_generator/multi_format_gen.py` |
| Change SQLite bait database content | `src/file_generator/sqlite_gen.py` |
| Change the Gemini AI prompts | `src/llm/llm_integration.py` |
| Change RAG banking context / terminology | `src/rag/` files |
| Save a new kind of data permanently | `src/state/state_manager.py` |
| Query logs / add a new DB table | `src/state/state_manager.py` |
| Change dashboard UI look | `dashboard/index.html` |
| Add a new dashboard API endpoint | `dashboard/monitor.py` |
| Change Docker build steps | `docker/Dockerfile` |
| Change how services are started in Docker | `docker/docker-compose.yaml` |
| Change environment variables / config keys | `.env.template` and `src/llm/llm_integration.py` |
| Change Windows startup behavior | `run_honeypot.bat` |

---

## 📁 Root Files

| File | What it does |
|---|---|
| `honeypot.py` | **The main application.** Every HTTP request comes here first. Fixed routes are at the top, the dynamic catch-all is at the bottom. 930+ lines. |
| `requirements.txt` | Lists all Python packages. Run `pip install -r requirements.txt` after pulling changes that add new packages. |
| `run_honeypot.bat` | Windows launcher. Double-click to start both the honeypot (port 8001) and dashboard (port 8002) automatically. |
| `setup_honeypot.py` | Creates `databases/`, `generated_files/`, `log_files/` folders on first run. |
| `DEPLOYMENT.md` | Step-by-step guide for Docker and VPS deployment. |
| `.env.template` | Template for environment variables. Copy to `.env` and fill in your keys. Never commit `.env`. |
| `.env` | Your local secrets (GEMINI_API_KEY, HONEYPOT_URL). Gitignored. |

---

## 📦 Source Modules (`src/`)

Each subfolder is a self-contained module with its own `__init__.py`.

---

### `src/api_generator/` — The Maze Logic

Controls **which endpoints exist**, **who can access them**, and **what breadcrumbs appear** in responses.

| File | What it does | Edit when... |
|---|---|---|
| `maze_generator.py` | Validates incoming paths, assigns access levels (public/user/admin), generates breadcrumb hints to other endpoints | You want to add new access levels, change what endpoints are "valid", change what hints the maze gives attackers |
| `http_responses.py` | Returns template JSON for 401 Unauthorized, 403 Forbidden, 404 Not Found, 500 Error | You want to change how error responses look to attackers |

---

### `src/data_generator/` — Fake Banking Data

Generates realistic-looking banking data on **every single request** — so no two attacker calls get the same numbers.

| File | What it does | Edit when... |
|---|---|---|
| `banking_data.py` | Generates companies, accounts, transactions, payments, merchants, users, reports, backups, secrets | You want to add a new data category (e.g. loans), change value ranges, add new fields to generated objects |

**Key class:** `BankingDataGenerator`

| Method | Returns | Count range |
|---|---|---|
| `generate_companies()` | List of company dicts | 8–20 |
| `generate_accounts()` | List of account dicts | 15–40 |
| `generate_transactions()` | List of transaction dicts | 20–100 |
| `generate_payments()` | List of payment dicts | 10–35 |
| `generate_merchants()` | List of merchant dicts | 8–25 |
| `generate_users()` | List of admin user dicts | 5–15 |
| `generate_secrets()` | List of secret entry dicts | 10 |

---

### `src/file_generator/` — Bait Files

Creates tracked files that are served to attackers when they hit download endpoints. Every file gets a unique **beacon ID** embedded. When the attacker opens the file, the beacon calls back.

| File | What it does | Edit when... |
|---|---|---|
| `generator.py` | Creates PDF reports and Excel `.xlsx` files | You want to change the PDF layout, add charts to Excel, change what data goes in them |
| `multi_format_gen.py` | Creates XML, CSV, JSON, JavaScript files | You want to change the content of these bait formats |
| `sqlite_gen.py` | Creates fake `.db` / `.sqlite` bait databases with tables | You want to add more tables to the bait databases, change the fake data inside |
| `txt_gen.py` | Creates `.txt` files (credentials, connection strings, API keys) | You want to change what fake credentials look like |

**How beacons work:** Every generated file contains a URL like `http://HONEYPOT_URL/track/<beacon_id>`. When the attacker opens the file, a request fires to that URL, which logs where they are.

**Supported bait formats:** `.pdf`, `.xlsx`, `.csv`, `.xml`, `.json`, `.js`, `.db`, `.sqlite`, `.txt`

---

### `src/llm/` — AI Response Generation

Connects to Google Gemini to generate realistic JSON responses for endpoints the honeypot has never seen before.

| File | What it does | Edit when... |
|---|---|---|
| `llm_integration.py` | Sends prompts to Gemini, returns JSON API response strings | You want to change the AI prompts, switch to a different model, add a fallback for when Gemini is unavailable |

**How it fits in:** When an attacker hits `/api/v1/accounts/ACC123/loans` (a path that has never been generated), `honeypot.py` calls `llm.generate_api_response(path, method)`. The result is returned to the attacker **and saved to the SQLite DB** — so the next visit to the same URL returns the same AI response (consistency).

---

### `src/rag/` — Banking Context

Provides banking domain language to the LLM so it generates more convincing responses.

| File | What it does | Edit when... |
|---|---|---|
| `rag_loader.py` | Loads context files and feeds them to LLM prompts | You want to add more context documents |
| `metadata.json` | RAG configuration | You want to change which context files are loaded |

---

### `src/state/` — Persistence (SQLite)

Stores everything that needs to survive between requests. Lives in `databases/honeypot.db`.

| File | What it does | Edit when... |
|---|---|---|
| `state_manager.py` | All database reads and writes — the single source of truth for stored state | You want to add a new table, add a query method, change retention policy |
| `schema.sql` | Human-readable reference for all table structures | Update this when you add or change a table in `state_manager.py` |

**SQLite Tables in `databases/honeypot.db`:**

| Table | Stores | Key use |
|---|---|---|
| `endpoints` | AI-generated JSON responses keyed by `(path, method)` | Ensures the same URL always gives the same response |
| `objects` | Typed fake objects (users, accounts) | Reuse generated objects across requests |
| `beacons` | Every bait file with its tracking beacon ID | Know which files were generated and if they were opened |
| `downloads` | Every `/download/*` request | Dashboard download tracking |
| `logs` | **Every log entry in plain text** — level, event, IP, message | Query attacker activity without decoding Base64 |

**New in Upgrade 2 — `logs` table:**  
Every `logger.info/warning/critical()` call in `honeypot.py` now writes to this table via `SQLiteLogHandler`. You can query by level, event type, or attacker IP directly in SQL.

```python
# Examples using state_manager
state.get_logs(level='CRITICAL')
state.get_logs(event='FILE_DOWNLOAD')
state.get_logs(client_ip='10.0.0.1')
```

---

## 📊 Dashboard (`dashboard/`)

The monitoring UI that team members watch during an active engagement.

| File | What it does | Edit when... |
|---|---|---|
| `index.html` | The entire dashboard UI (HTML + CSS + JS in one file). Polls the backend every few seconds and updates the live feed. | You want to change the dashboard look, add new panels, change the refresh interval |
| `monitor.py` | Flask backend serving the dashboard API. Reads `log_files/api_audit.log` and `databases/honeypot.db`. Runs on port 8002. | You want to add a new dashboard API endpoint, add new statistics, change what data the dashboard exposes |

**Dashboard API endpoints:**
- `GET /` — Dashboard UI
- `GET /api/activity` — Last 100 decoded log entries
- `GET /api/new` — New entries since last poll (incremental)
- `GET /api/stats` — Total endpoints, downloads, beacon activations
- `GET /api/downloads` — All file downloads
- `GET /api/sensitive` — Only sensitive file downloads

---

## 🐳 Docker (`docker/`)

For running in production or sharing a fully self-contained environment.

| File | What it does | Edit when... |
|---|---|---|
| `Dockerfile` | Multi-stage build with two named targets: `honeypot` (port 8001, 4 gunicorn workers) and `dashboard` (port 8002, 2 workers). Runs as non-root user. | You change Python version, add system dependencies, or change startup command |
| `docker-compose.yaml` | Defines both services, named volumes for persistent data, internal network, health checks. Single command to run everything. | You want to add a new service, change port mappings, or change environment variable defaults |
| `.dockerignore` | Prevents `venv/`, logs, databases, and secrets from being copied into the image | Add new directories you don't want in the image |

---

## 🗄️ Runtime Directories (auto-created, gitignored)

| Directory | Contents | Notes |
|---|---|---|
| `databases/` | `honeypot.db` — the single SQLite file for all state | Auto-created on first run. Never commit this. |
| `generated_files/` | Bait files (PDFs, spreadsheets, DBs) served to attackers | Grows over time. Clean it out periodically. |
| `log_files/` | `api_audit.log` — Base64-encoded audit log | Each line is one Base64-encoded log entry. See `docs/AUDIT_LOGS_GUIDE.md` for how to decode. |

---

## 📚 Other Docs (`docs/`)

| File | What it covers |
|---|---|
| `PROJECT_STRUCTURE.md` | Full directory tree and overview of key components |
| `FILE_STRUCTURE_GUIDE.md` | This file — per-file explanations and "which file to edit" decisions |
| `AUDIT_LOGS_GUIDE.md` | How to read logs from both the Base64 file and the SQLite `logs` table |
