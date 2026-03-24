# File Structure Guide
> **Which file do I edit?** — Per-file explanations and quick-decision tables for every module.

---

## 🗺️ Quick Decision Table

| What you want to change               | File(s) to edit                                   |
| ------------------------------------- | ------------------------------------------------- |
| Add a new fixed API route             | `honeypot.py`                                     |
| Change upload trap endpoints/logic    | `src/file_upload_rce.py`                          |
| Change webshell command responses     | `src/rag/shell_rag_loader.py`                     |
| Change attacker phase classification  | `src/attacker_intel.py` → `_CMD_RISK_TABLE`       |
| Change IP geolocation provider        | `src/attacker_intel.py` → `_geolocate()`          |
| Change deception advisor hints        | `src/attacker_intel.py` → `_deception_strategy()` |
| Change how AI generates API responses | `src/llm/llm_integration.py`                      |
| Change API maze access levels         | `src/api_generator/maze_generator.py`             |
| Change 401 / 403 / 404 responses      | `src/api_generator/http_responses.py`             |
| Add or change banking data fields     | `src/data_generator/banking_data.py`              |
| Add a new bait file format            | `src/file_generator/` — add generator             |
| Change PDF / Excel bait content       | `src/file_generator/generator.py`                 |
| Change XML / CSV / JSON bait content  | `src/file_generator/multi_format_gen.py`          |
| Change SQLite bait database content   | `src/file_generator/sqlite_gen.py`                |
| Change the Gemini API prompts         | `src/llm/llm_integration.py`                      |
| Add new banking RAG context           | `src/rag/` files                                  |
| Add a new DB table / query method     | `src/state/state_manager.py`                      |
| Change dashboard UI look              | `dashboard/index.html`                            |
| Add dashboard API endpoint            | `dashboard/monitor.py`                            |
| Change Docker build steps             | `docker/Dockerfile`                               |
| Change environment variables          | `.env.template`                                   |
| Change Windows startup behaviour      | `run_honeypot.bat`                                |

---

## 📁 Root Files

| File                            | What it does                                                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `honeypot.py`                   | **Main application.** All HTTP routes. CVE shim routes registered at top, dynamic catch-all at bottom. ~950 lines. |
| `requirements.txt`              | Python packages. Run `pip install -r requirements.txt` after pulling.                                              |
| `run_honeypot.bat`              | Windows launcher. Starts honeypot (8001) + dashboard (8002).                                                       |
| `setup_honeypot.py`             | Creates `databases/`, `generated_files/`, `log_files/` on first run.                                               |
| `DEPLOYMENT.md`                 | Docker and VPS deployment guide.                                                                                   |
| `ATTACK_GUIDE.md`               | Red-team testing guide — how to trigger every trap.                                                                |
| `.env.template`                 | Template for environment variables. Copy → `.env`.                                                                 |
| `.env`                          | Your secrets (`GEMINI_API_KEY`). Gitignored.                                                                       |


---

## 📦 Source Modules (`src/`)

---

### `src/file_upload_rce.py` — CVE-2020-36179 Deception Module ⭐

Implements the fake file upload vulnerability trap. No real files are ever written to disk.

**Key functions:**

| Function/Route | What it does |
|---------------|-------------|
| `_route_spring_upload_get()` | Returns Spring compliance portal upload form |
| `_route_php_upload_get()` | Returns PHP bank client portal upload form |
| `_handle_upload()` | Shared upload handler — reads ≤512 bytes, detects webshell patterns, registers filename |
| `_contains_webshell_code()` | Matches 13 regex patterns (PHP system/eval/passthru etc.) |
| `_route_webshell_get()` | Webshell execution trap — only registered filenames work |
| `_get_shell_output()` | Delegates to `shell_rag_loader.resolve_shell_command()` |
| `_route_dashboard_summary()` | Returns full intel summary from `attacker_intel.dashboard_summary()` |
| `register_file_upload_routes()` | Registers all routes + inits RAG loader |

**Dangerous extension detection:** `.php`, `.phtml`, `.phar`, `.jsp`, `.asp`, `.aspx`, `.py`, `.sh`, `.rb`

**Webshell payload patterns detected:** `<?php`, `system(`, `exec(`, `shell_exec(`, `passthru(`, `eval(`, `base64_decode(`, `$_GET[`, `$_POST[`, `$_REQUEST[`, `popen(`, `proc_open(`, `cmd=`

---

### `src/attacker_intel.py` — Intelligence Engine ⭐

Per-IP attacker profiling. All data is in-memory (fast, no DB write on every hit).

**Key components:**

| Component | What it does |
|-----------|-------------|
| `AttackerSession` | Full per-IP profile: timeline, commands, files, phase, engagement score |
| `_CMD_RISK_TABLE` | 25+ command patterns → (risk 0-100, phase, label) |
| `_FILE_PATTERNS` | 18 regex patterns → payload type tags |
| `_classify_command()` | Returns risk score + phase for any shell command |
| `_analyze_file()` | Returns extension risk, payload tags, threat level for any uploaded file |
| `_geolocate()` | Free IP geolocation (ip-api.com) with local cache |
| `_deception_strategy()` | Returns hints to keep attacker engaged longer |
| `dashboard_summary()` | Full intelligence summary for the API |

**Attack phases:**

| Phase | Risk range | Typical commands |
|-------|-----------|-----------------|
| `IDLE` | — | Just connected |
| `RECON` | 15–35 | `whoami`, `id`, `ls`, `ps aux`, `ifconfig` |
| `EXPLOIT` | 45–80 | `sudo -l`, `cat /etc/shadow`, `wget http://...` |
| `POST_EXPLOIT` | 85–95 | `bash -i >& /dev/tcp/...`, `nc -e /bin/bash` |
| `LATERAL` | 65–80 | `ssh user@host`, `crontab -e`, `scp` |

**Public API functions:**

```python
from src import attacker_intel as intel

intel.record_form_view(ip, endpoint)
intel.record_upload(ip, filename, raw_bytes, endpoint)
intel.record_command(ip, cmd, output)
intel.record_webshell_access(ip, filename, cmd, output)
intel.get_session(ip)          # → dict
intel.get_all_sessions()       # → list[dict]
intel.dashboard_summary()      # → full dashboard dict
```

---

### `src/rag/shell_rag_loader.py` — Hybrid Shell Engine ⭐

Resolves shell commands with a 6-step pipeline:

```
1. Exact cache match        (58 ground-truth commands, always correct)
2. Case-insensitive match
3. Dynamic handler          (echo, cat <path>, grep, ls <path>, revshell → hang)
4. TF-IDF fuzzy match       (threshold 0.40 — Cowrie dataset, no sklearn version lock)
5. Gemini LLM               (live, cached per session)
6. bash: X: command not found
```

**Key functions:**

| Function | What it does |
|----------|-------------|
| `init(pkl_path, json_path, api_key)` | Loads data, builds TF-IDF, initialises Gemini. Idempotent. |
| `resolve_shell_command(cmd)` | Full pipeline lookup — always returns a string |
| `get_metadata()` | Returns loader status (cache size, TF-IDF, LLM enabled) |

**Data files:**
- `src/rag/shell_rag.pkl` — Dataset-trained model (copy from `Dataset/`)
- `src/rag/ai_cmd_cache.json` — Gemini-generated responses (copy from `Dataset/`)

---

### `src/api_generator/` — Maze Logic

| File | What it does | Edit when... |
|------|-------------|-------------|
| `maze_generator.py` | Validates paths, assigns access levels (public/user/admin), generates breadcrumb hints | Add access levels, change valid endpoint patterns |
| `http_responses.py` | Returns 401 / 403 / 404 / 500 JSON templates | Change error response appearance |

---

### `src/data_generator/` — Fake Banking Data

Generates fresh data on **every request** — no two attacker calls get the same numbers.

| Method | Returns | Count |
|--------|---------|-------|
| `generate_companies()` | List of company dicts | 8–20 |
| `generate_accounts()` | List of account dicts | 15–40 |
| `generate_transactions()` | List of transaction dicts | 20–100 |
| `generate_payments()` | List of payment dicts | 10–35 |
| `generate_users()` | List of admin user dicts | 5–15 |
| `generate_secrets()` | List of fake secret entries | 10 |

---

### `src/file_generator/` — Bait Files

Creates tracked files served to attackers. Every file gets a unique **beacon ID** embedded. When the attacker opens the file, the beacon calls back.

| File | Formats | Edit when... |
|------|---------|-------------|
| `generator.py` | PDF, Excel (.xlsx) | Change PDF layout, add charts |
| `multi_format_gen.py` | XML, CSV, JSON, JavaScript | Change bait content |
| `sqlite_gen.py` | .db / .sqlite | Add tables to bait databases |
| `txt_gen.py` | .txt credentials | Change fake credential format |

---

### `src/llm/` — API Response AI

Calls Gemini to generate realistic JSON for unknown API paths. Result is saved to SQLite `endpoints` table — same URL always returns same response.

---

### `src/state/` — Persistence

**SQLite tables in `databases/honeypot.db`:**

| Table | Stores |
|-------|--------|
| `endpoints` | AI-generated responses per `(path, method)` |
| `objects` | Typed fake objects reused across sessions |
| `beacons` | Bait file tokens — tracks download + open events |
| `downloads` | Every `/download/*` hit with IP and user agent |
| `logs` | Full structured audit log (level, event, IP, message) |

---

## 📊 Dashboard (`dashboard/`)

| File | What it does |
|------|-------------|
| `index.html` | Full dashboard UI — polls backend every few seconds |
| `monitor.py` | Flask backend on port 8002 |

**Dashboard API:**
- `GET /` — Dashboard UI
- `GET /api/activity` — Last 100 decoded log entries
- `GET /api/new` — New entries since last poll
- `GET /api/stats` — Totals (endpoints, downloads, beacons)
- `GET /api/downloads` — All file downloads
- `GET /api/sensitive` — Sensitive file downloads only

**CVE Intelligence API (port 8001):**
- `GET /api/dashboard/cve/file-upload` — Full intel summary
- `GET /api/dashboard/cve/file-upload/attackers` — All attacker profiles
- `GET /api/dashboard/cve/file-upload/attacker/<ip>` — Per-IP deep profile

---

## 🗄️ Runtime Directories (auto-created, gitignored)

| Directory | Contents |
|-----------|---------|
| `databases/` | `honeypot.db` — all SQLite state |
| `generated_files/` | Bait files served to attackers |
| `log_files/` | `api_audit.log` — Base64-encoded audit log |
| `Dataset/` | `shell_rag.pkl` + `ai_cmd_cache.json` training data |
