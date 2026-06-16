# Maze Myth — Deployment Guide

> **One approach. One command. Production-ready.**
> Docker Compose with proxy, decoy real app, honeypot, and operator dashboard.

---

## Environment Variables

Edit `.env` (copy from `.env.template`):

```env
# Required — Gemini AI for API responses + shell RAG fallback
GEMINI_API_KEY=AIzaSy...your-real-key-here...

# URL attackers use to trigger beacon callbacks
HONEYPOT_URL=http://YOUR_SERVER_IP

# Internal honeypot URL used by the dashboard service
HONEYPOT_INTERNAL_URL=http://10.0.0.3:8001

# Gemini model for API responses
LLM_MODEL=gemini-2.0-flash
```

> If `GEMINI_API_KEY` is missing, the honeypot still starts — API maze falls back to templates, shell RAG uses the 58-command ground-truth cache only (no LLM).

---

## Step-by-Step: Docker Compose

### Step 1 — Configure

```bash
cp .env.template .env
# Edit .env: add your GEMINI_API_KEY and public server URL
```

### Step 2 — Build

```bash
docker compose -f docker-compose.yaml build
```

Builds four services across the repo:
- **`proxy`** — OpenResty reverse proxy on port 80
- **`real-app`** — internal decoy banking service on 10.0.0.2:8080
- **`honeypot`** — internal deception service on 10.0.0.3:8001
- **`dashboard`** — operator UI on port 8002

### Step 3 — Start

```bash
docker compose -f docker-compose.yaml up -d
```

### Step 4 — Verify

```bash
docker compose -f docker-compose.yaml ps
```

Expected containers:
```
vm1-proxy          Up (healthy)    0.0.0.0:80->80/tcp
vm2-real           Up (healthy)
vm3-honeypot       Up (healthy)
vm3-dashboard      Up (healthy)    0.0.0.0:8002->8002/tcp
```

### Step 5 — Test the CVE trap is live

```bash
# Check upload form through the proxy
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost/clientportal/support/attachments.php
# Expected: 200

# Check the dashboard UI
curl -s http://localhost:8002/ | grep -i "dashboard"
# Expected: HTML response from the operator dashboard
```

### Step 6 — View logs

```bash
docker compose -f docker-compose.yaml logs -f vm3-honeypot
```

### Step 7 — Stop

```bash
# Stop (data persists in volumes)
docker compose -f docker-compose.yaml down

# Stop + wipe all data
docker compose -f docker-compose.yaml down -v
```

---

## Deploy to a VPS (Ubuntu)

```bash
# 1. Copy project
scp -r . user@YOUR_SERVER_IP:/opt/maze-myth

# 2. SSH in
ssh user@YOUR_SERVER_IP
cd /opt/maze-myth

# 3. Configure
cp .env.template .env
nano .env  # fill in GEMINI_API_KEY and HONEYPOT_URL

# 4. Start
docker compose -f docker-compose.yaml up -d
```

**Firewall rules:**
```bash
ufw allow 80/tcp    # proxy — attacker-facing
ufw allow 8002/tcp  # dashboard (SSH tunnel only recommended)
# DO NOT open 8080 or 8001 publicly
```

**View dashboard securely over SSH tunnel:**
```bash
ssh -L 8002:localhost:8002 user@YOUR_SERVER_IP
# Then open http://localhost:8002 locally
```

---

## Ports

| Port | Service | Expose? |
|------|---------|---------|
| **80** | Proxy (attacker-facing) | ✅ Yes — expose publicly |
| **8002** | Operator dashboard | ⚠️ Only via SSH tunnel or trusted network |
| **8080** | Real app (internal) | ❌ No — internal only |
| **8001** | Honeypot (internal) | ❌ No — internal only |

---

## Proxy Redirection & Risk Scoring

The `proxy` service is the attacker-facing gateway. It evaluates each IP and decides whether to forward traffic to the decoy real app or the internal honeypot.

Key behavior:
- `proxy` listens on port **80** and exposes only attacker-facing traffic.
- `real-app` is a believable decoy banking service on `10.0.0.2:8080`.
- `honeypot` runs on `10.0.0.3:8001` inside `deception-net` and is never exposed directly in the default Docker Compose deployment.
- `dashboard` is operator-only and should not be publicly accessible.
- The proxy risk engine (`proxy/lua/risk_engine.lua`) assigns attackers a risk score, tracks attacker state, and applies sticky honeypot assignment when needed.
- High-risk attacker flows and suspicious uploads are redirected into the honeypot trap.
- Low-risk traffic may be routed to the decoy `real-app` to maintain plausibility.

### Manual Redirect Testing

Use these checks when verifying the deployed platform:

```bash
# Check the attacker-facing proxy
curl -s -o /dev/null -w "%{http_code}" http://localhost/clientportal/support/attachments.php
# Expected: 200

# Confirm dashboard response
curl -s http://localhost:8002/ | grep -i "dashboard"
# Expected: HTML response from the operator dashboard

# Ensure honeypot is internal only in default compose
curl -I http://localhost:8001
# Expected: connection refused or no public access
```

### Behavior Validation

The platform is designed to keep suspicious traffic trapped in the honeypot while letting normal decoy traffic flow through `real-app`.

- `HTTP 200` on `/clientportal/support/attachments.php` should be served through the proxy.
- `dashboard` should be reachable only on port `8002` and ideally via SSH tunnel.
- The honeypot should remain internal and not appear on a public network port unless manually started in standalone mode.

---

## Honeypot Access Control

The honeypot (`honeypot.py`) enforces an IP gate on every incoming request via the `honeypot_gate()` `@app.before_request` hook:

| Request source | Result |
|---------------|--------|
| Proxy with `X-Risk-Score >= 100` | ✅ Admitted — IP remembered for session |
| Previously approved attacker IP | ✅ Admitted (returning attacker) |
| `127.0.0.1` loopback | ✅ Admitted (Docker health checks) |
| `/api/dashboard/*` from `10.0.*` subnet | ✅ Admitted (dashboard polling) |
| Everything else | ❌ `404 Not Found` — honeypot invisible |

This means:
- Scanners probing port 8001 directly always see `404`.
- Low-risk users browsing through the proxy are served by `real-app` only.
- Only IPs whose Lua risk score reached ≥ 100 are redirected AND admitted.

---

## Shell RAG Model Setup

The CVE webshell trap needs `src/rag/shell_rag.pkl` to serve Cowrie-trained responses.

**Option A — Use pre-trained model (recommended)**
```bash
# Copy from Dataset/ to src/rag/
cp Dataset/shell_rag.pkl src/rag/shell_rag.pkl
cp Dataset/ai_cmd_cache.json src/rag/ai_cmd_cache.json
```

**Option B — Retrain from new Cowrie logs**
1. Upload `kaggle_shell_ai_trainer.ipynb` to Kaggle
2. Add your Cowrie dataset at the path configured in Cell 3
3. Run all cells → download `shell_rag.pkl`
4. Place in `src/rag/shell_rag.pkl`

> If `shell_rag.pkl` is missing, the loader falls back to the 58-command built-in ground-truth + Gemini LLM only.

---

## Why Gunicorn?

| | Flask dev server | Gunicorn |
|--|-----------------|---------|
| Workers | 1 single-threaded | 4 workers × 2 threads |
| Concurrent requests | 1 at a time | ~8 at a time |
| Crash recovery | App dies = gone | Worker crashes = restart |
| Safe to expose | ❌ | ✅ |

Config: `--workers 4 --threads 2 --timeout 120`
(120s timeout for slow Gemini calls)

---

## Dockerfile — Zero Build Dependencies

The `docker/Dockerfile` builder stage no longer runs any `apt-get install`. All Python packages in `requirements.txt` (`pillow`, `numpy`, `pandas`, `scikit-learn`, `reportlab`, `google-generativeai`, etc.) ship as pre-compiled **manylinux wheels** for Python 3.11 on linux/amd64 — no C compiler required.

```dockerfile
# Builder stage — no apt-get, pure wheel install
RUN pip install --only-binary=:all: -r requirements.txt
```

The runtime base only installs `curl` (needed for `HEALTHCHECK`). This eliminates `deb.debian.org` download failures and makes builds deterministic and network-resilient.

---

## Update After Code Changes

```bash
# Full rebuild (all services)
docker compose -f docker-compose.yaml build --no-cache
docker compose -f docker-compose.yaml up -d

# Fast partial rebuild (only changed services)
docker compose -f docker-compose.yaml build honeypot dashboard
docker compose -f docker-compose.yaml up -d honeypot dashboard
```

---

## Troubleshooting

### Container exits immediately
```bash
docker compose -f docker-compose.yaml logs vm3-honeypot
```
Common causes: missing `.env`, missing `GEMINI_API_KEY`, port conflict.

### Port in use
```bash
netstat -ano | findstr :80   # Windows
lsof -i :80                    # Linux/Mac
```

### Dashboard unable to query honeypot
If the dashboard cannot reach live honeypot intel, add `HONEYPOT_INTERNAL_URL=http://10.0.0.3:8001` to `.env`.

### Shell RAG not loading
```bash
# Check pkl exists
ls -la src/rag/shell_rag.pkl

# Check loader status
curl http://localhost:8002/api/intel/summary
```

### Data volumes
Both containers share named volumes:
- `honeypot-logs` → honeypot writes, dashboard reads (read-only)
- `honeypot-db` → shared SQLite state

Data survives `docker compose down`. Only `down -v` removes it.

---

## Windows Local Development

```
Double-click run_honeypot.bat
```

Or manually:
```bash
pip install -r requirements.txt
cp .env.template .env   # add GEMINI_API_KEY
python honeypot.py      # Terminal 1 — port 8001
python dashboard/monitor.py  # Terminal 2 — port 8002
```

