# File Structure Guide

> **Which file do I edit?** — Per-file explanations and quick-decision tables for every module in Maze Myth.

---

## 🗺️ Quick Decision Table

| What you want to change | File(s) to edit |
|------------------------|-----------------|
| Add a new fixed API route | `honeypot.py` |
| Change upload trap endpoints / logic | `src/file_upload_rce.py` |
| Change webshell payload patterns detected | `src/file_upload_rce.py` → `_WEBSHELL_PATTERNS` |
| Change webshell command responses | `src/rag/shell_rag_loader.py` |
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
| Change the Gemini API prompts | `src/llm/llm_integration.py` |
| Add new banking RAG context | `src/rag/` files |
| Add a new DB table / query method | `src/state/state_manager.py` |
| Change dashboard UI look | `dashboard/index.html` |
| Add dashboard API endpoint | `dashboard/monitor.py` |
| Change Docker build steps | `docker/Dockerfile` |
| Change environment variables | `.env.template` |
| Change Windows startup behaviour | `run_honeypot.bat` |

---

## 📁 Root Files

| File | What it does |
|------|-------------|
| `honeypot.py` | **Main application.** All HTTP routes. CVE shim routes registered first, dynamic catch-all at bottom. ~950 lines. |
| `requirements.txt` | Python packages. Run `pip install -r requirements.txt` after pulling. |
| `run_honeypot.bat` | Windows launcher. Starts honeypot (8001) + dashboard (8002). |
| `setup_honeypot.py` | Creates `databases/`, `generated_files/`, `log_files/` on first run. |
| `DEPLOYMENT.md` | Docker and VPS deployment guide. |
| `ATTACK_GUIDE.md` | Red-team testing guide — how to trigger every trap. |
| `.env.template` | Template for environment variables. Copy to `.env`. |
| `.env` | Your secrets (`GEMINI_API_KEY`). Gitignored. |

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
| `/uploads/<filename>` | GET | Webshell execution trap (only registered filenames work) |
| `/api/dashboard/cve/file-upload` | GET | Full attacker intel summary |
| `/api/dashboard/cve/file-upload/attackers` | GET | All attacker profiles |
| `/api/dashboard/cve/file-upload/attacker/<ip>` | GET | Per-IP deep profile |

**Key functions:**

| Function | What it does |
|----------|-------------|
| `_route_spring_upload_get()` | Returns Spring compliance portal HTML form with Apache-Coyote headers |
| `_route_php_upload_get()` | Returns PHP bank client portal HTML form with PHP/Apache headers |
| `_handle_upload()` | Shared handler — reads ≤512 bytes, detects webshell patterns, registers filename in `_shell_registry` |
| `_contains_webshell_code()` | 13-pattern regex check (`<?php`, `system(`, `eval(`, `passthru(`, `$_GET[`, etc.) |
| `_analyze_file()` | 18-pattern full analysis → threat level (LOW/MEDIUM/HIGH/CRITICAL), extension risk, payload tags |
| `_route_webshell_get()` | Webshell execution trap — only filenames in `_shell_registry` accepted |
| `_get_shell_output()` | Delegates to `shell_rag_loader.resolve_shell_command()` |
| `register_file_upload_routes(app)` | Registers all routes + inits RAG loader |

**Deceptive headers applied:**

| Endpoint type | Server header | X-Powered-By |
|--------------|---------------|-------------|
| Spring | `Apache-Coyote/1.1` | `Spring Framework 5.3.9` |
| PHP | `Apache/2.4.54 (Debian)` | `PHP/7.4.33` |

**Dangerous extensions triggering CRITICAL alert:**
`.php`, `.php3`, `.php4`, `.php5`, `.phtml`, `.phar`, `.jsp`, `.jspx`, `.aspx`, `.asp`, `.cfm`, `.py`, `.rb`, `.pl`, `.sh`, `.bash`, `.cgi`

**Webshell payload patterns detected:**
`<?php`, `system(`, `exec(`, `shell_exec(`, `passthru(`, `eval(`, `base64_decode(`, `$_GET[`, `$_POST[`, `$_REQUEST[`, `popen(`, `proc_open(`, `cmd=`

---

### `src/attacker_intel.py` — Intelligence Engine ⭐

Per-IP attacker profiling. All data is in-memory (fast; no DB write on every hit).
Feeds the dashboard via `dashboard_summary()`.

**Key components:**

| Component | What it does |
|-----------|-------------|
| `AttackerSession` | Full per-IP profile: timeline, commands, files, phase, engagement score (0–100) |
| `_CMD_RISK_TABLE` | 25+ command patterns → (risk 0–100, attack phase, label) |
| `_FILE_PATTERNS` | 18 regex patterns → payload type tags (PHP_OPENER, TCP_REVSHELL, JAVA_RCE, etc.) |
| `_DANGEROUS_EXT` | 17 dangerous extensions detected on upload |
| `_classify_command(cmd)` | Returns risk score + phase label for any shell command |
| `_analyze_file(bytes, filename)` | Returns extension risk, payload tags, threat level, has_revshell, has_eval |
| `_geolocate(ip)` | Free IP geolocation (ip-api.com) with in-memory cache; skips private IPs |
| `_deception_strategy(session)` | Returns up to 3 deception hints based on current phase and what attacker has done |
| `dashboard_summary()` | Full intelligence summary for the dashboard API |

**Attack phases:**

| Phase | Risk range | Engagement delta | Typical commands |
|-------|-----------|-----------------|-----------------|
| `IDLE` | — | +1 | Just connected |
| `RECON` | 15–35 | +risk/5 | `whoami`, `id`, `ls`, `ps aux`, `ifconfig`, `env`, `history` |
| `EXPLOIT` | 45–80 | +risk/5 | `sudo -l`, `cat /etc/shadow`, `wget http://...`, `useradd`, `chmod 4755` |
| `POST_EXPLOIT` | 85–95 | +risk/5 | `bash -i >& /dev/tcp/`, `nc -e /bin/bash`, `msfvenom` |
| `LATERAL` | 65–80 | +risk/5 | `ssh user@host`, `crontab -e`, `scp`, `rsync` |

**Engagement score deltas:**

| Event type | Score delta |
|-----------|------------|
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
intel.get_session(ip)          # → full per-IP dict
intel.get_all_sessions()       # → list[dict]
intel.dashboard_summary()      # → global dashboard dict
```

---

### `src/rag/shell_rag_loader.py` — Hybrid Shell Engine ⭐

Resolves shell commands with a **6-step resolution pipeline** (never fails — always returns a string):

```
1. Exact cache match        (58 ground-truth commands, always correct)
2. Case-insensitive match   (same 58 commands, any case)
3. Dynamic handler          (echo, cat <path>, grep, ls <path>, revshell → 1.5s hang + EOF)
4. TF-IDF fuzzy match       (235 real Cowrie attacker sessions, threshold 0.40)
5. Gemini LLM               (live generation, cached per session via ai_cmd_cache.json)
6. Fallback                 ("bash: <cmd>: command not found")
```

**Key functions:**

| Function | What it does |
|----------|-------------|
| `init(pkl_path, json_path, api_key)` | Loads dataset, builds TF-IDF index, initialises Gemini client. Idempotent. |
| `resolve_shell_command(cmd)` | Runs the full 6-step pipeline — always returns a string |
| `get_metadata()` | Returns loader status: cache size, TF-IDF enabled, LLM enabled |

**Data files:**
- `src/rag/shell_rag.pkl` — Cowrie-trained command→response model
- `src/rag/ai_cmd_cache.json` — Gemini-pre-generated responses (bootstrapped on startup)

---

### `src/api_generator/` — Maze Logic

| File | What it does | Edit when... |
|------|-------------|-------------|
| `maze_generator.py` | Validates paths, assigns access levels (public/user/admin), generates breadcrumb hints | Adding access levels, changing valid endpoint patterns |
| `http_responses.py` | Returns 401 / 403 / 404 / 500 JSON templates with realistic banking error messages | Changing error response appearance |

---

### `src/data_generator/banking_data.py` — Fake Banking Data ⭐

Generates fresh, randomized data on **every request** — no two attacker calls get the same numbers.
Uses `Faker` for realistic names and `random` for numeric variance.

| Method | Returns | Count per call |
|--------|---------|---------------|
| `generate_companies()` | List of company dicts (name, id, balance, status) | 8–20 |
| `generate_accounts()` | List of account dicts (IBAN, type, balance, currency) | 15–40 |
| `generate_transactions()` | List of transaction dicts (amount, from/to, timestamp) | 20–100 |
| `generate_payments()` | List of payment dicts (reference, status, method) | 10–35 |
| `generate_users()` | List of admin user dicts (name, role, last_login) | 5–15 |
| `generate_secrets()` | List of fake secret entries (API keys, tokens, creds) | 10 |
| `generate_merchants()` | List of merchant dicts (name, MCC, terminal count) | varies |
| `generate_terminals()` | List of POS terminal dicts (serial, location, status) | varies |

---

### `src/file_generator/` — Bait Files

Creates tracked files served to attackers. Every file gets a unique **beacon ID** embedded.
When the attacker opens the file, the beacon calls back to the honeypot.

| File | Formats | Beacon method |
|------|---------|--------------|
| `generator.py` | PDF, Excel (.xlsx) | URL in PDF footer / hyperlink in Excel cell |
| `multi_format_gen.py` | XML, CSV, JSON, JavaScript | `<beacon>` tag / URL column / `_beacon_url` field / `fetch()` call |
| `sqlite_gen.py` | .db / .sqlite | Row inserted in `_tracking` table |
| `txt_gen.py` | .txt credentials | URL at bottom of file |

---

### `src/llm/llm_integration.py` — API Response AI

Calls Gemini to generate realistic JSON responses for unknown API paths.
Result is saved to SQLite `endpoints` table — same URL always returns the same AI response.

**Prompt logic**: Includes path context, HTTP method, inferred resource type, and banking domain context from `rag_loader.py`.

---

### `src/state/state_manager.py` — Persistence

**SQLite tables in `databases/honeypot.db` (WAL mode):**

| Table | Stores |
|-------|--------|
| `endpoints` | AI-generated responses per `(path, method)` |
| `objects` | Typed fake objects reused across sessions |
| `beacons` | Bait file tokens — tracks download + open events |
| `downloads` | Every `/download/*` hit with IP, user agent, timestamp |
| `logs` | Structured audit log (level, event, IP, message, Base64-encoded) |

**Key methods:**
- `log_event(level, event, ip, message)` — writes to all three log handlers
- `log_download(ip, ua, filename, beacon_id)` — records file download
- `get_downloads()` — returns all download records for dashboard
- `get_endpoint(path, method)` / `save_endpoint(...)` — AI response cache
- `get_or_create_beacon(token)` / `fire_beacon(token, ip)` — beacon tracking

---

## 📊 Dashboard (`dashboard/`)

| File | What it does |
|------|-------------|
| `index.html` | Full dashboard UI — polls backend every few seconds |
| `monitor.py` | Flask backend on port 8002 |

**Standard Dashboard API (port 8002):**

| Endpoint | Returns |
|----------|---------|
| `GET /` | Dashboard UI |
| `GET /api/activity` | Last 100 decoded log entries |
| `GET /api/new` | New entries since last poll |
| `GET /api/stats` | Totals (endpoints, downloads, beacons) |
| `GET /api/downloads` | All file download records |
| `GET /api/sensitive` | Sensitive file downloads only |

**CVE Intelligence API (port 8001 — served by honeypot itself):**

| Endpoint | Returns |
|----------|---------|
| `GET /api/dashboard/cve/file-upload` | Global intelligence summary (all IPs, phase dist, top commands) |
| `GET /api/dashboard/cve/file-upload/attackers` | All attacker profiles, sorted by engagement score |
| `GET /api/dashboard/cve/file-upload/attacker/<ip>` | Per-IP deep profile (geo, timeline, files, commands, deception hints) |

---

## 🗄️ Runtime Directories (auto-created, gitignored)

| Directory | Contents |
|-----------|---------|
| `databases/` | `honeypot.db` — all SQLite state (WAL mode) |
| `generated_files/` | Bait files served to attackers |
| `log_files/` | `api_audit.log` — Base64-encoded audit log |
| `Dataset/` | `shell_rag.pkl` + `ai_cmd_cache.json` training data |
