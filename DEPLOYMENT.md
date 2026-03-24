# Maze Myth — Deployment Guide

> **One approach. One command. Production-ready.**
> Docker Compose with Gunicorn — all you need for a real server or VPS.

---

## Environment Variables

Edit `.env` (copy from `.env.template`):

```env
# Required — Gemini AI for API responses + shell RAG fallback
GEMINI_API_KEY=AIzaSy...your-real-key-here...

# URL attackers use to trigger beacon callbacks
HONEYPOT_URL=http://YOUR_SERVER_IP:8001

# Gemini model for API responses
LLM_MODEL=gemini-2.0-flash
```

> If `GEMINI_API_KEY` is missing, the honeypot still starts — API maze falls back to templates, shell RAG uses the 58-command ground-truth cache only (no LLM).

---

## Step-by-Step: Docker Compose

### Step 1 — Configure

```bash
cp .env.template .env
# Edit .env: add your GEMINI_API_KEY and server IP
```

### Step 2 — Build

```bash
docker compose -f docker/docker-compose.yaml build
```

Builds two targets from a single multi-stage `Dockerfile`:
- **`honeypot`** — port 8001, 4 Gunicorn workers
- **`dashboard`** — port 8002, 2 Gunicorn workers

Final images: ~200–250 MB each (multi-stage eliminates build tools).

### Step 3 — Start

```bash
docker compose -f docker/docker-compose.yaml up -d
```

### Step 4 — Verify

```bash
docker compose -f docker/docker-compose.yaml ps
```

```
NAME                    STATUS          PORTS
maze-myth-honeypot      Up (healthy)    0.0.0.0:8001->8001/tcp
maze-myth-dashboard     Up (healthy)    0.0.0.0:8002->8002/tcp
```

### Step 5 — Test the CVE trap is live

```bash
# Check upload form
curl -s -o /dev/null -w "%{http_code}" \
  http://localhost:8001/clientportal/support/attachments.php
# Expected: 200

# Check intelligence dashboard
curl http://localhost:8001/api/dashboard/cve/file-upload | python3 -m json.tool
# Expected: JSON with stats, top_attackers, phase_distribution
```

### Step 6 — View logs

```bash
docker compose -f docker/docker-compose.yaml logs -f honeypot
```

### Step 7 — Stop

```bash
# Stop (data persists in volumes)
docker compose -f docker/docker-compose.yaml down

# Stop + wipe all data
docker compose -f docker/docker-compose.yaml down -v
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
docker compose -f docker/docker-compose.yaml up -d
```

**Firewall rules:**
```bash
ufw allow 8001/tcp   # honeypot (attacker-facing — expose this)
# DO NOT open 8002 publicly
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
| **8001** | Honeypot + CVE traps + Intelligence API | ✅ Yes — attackers use this |
| **8002** | Operator dashboard | ❌ Never — SSH tunnel only |

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

## Update After Code Changes

```bash
docker compose -f docker/docker-compose.yaml build --no-cache
docker compose -f docker/docker-compose.yaml up -d
```

---

## Troubleshooting

### Container exits immediately
```bash
docker compose -f docker/docker-compose.yaml logs honeypot
```
Common causes: missing `.env`, missing `GEMINI_API_KEY`, port conflict.

### Port in use
```bash
netstat -ano | findstr :8001   # Windows
lsof -i :8001                   # Linux/Mac
```

### Shell RAG not loading
```bash
# Check pkl exists
ls -la src/rag/shell_rag.pkl

# Check loader status
curl http://localhost:8001/api/dashboard/cve/file-upload | python3 -m json.tool
# Look for "tfidf_enabled" and "llm_enabled" in the response
```

### Webshell trap returns 403 for uploaded shell
The filename must be uploaded WITH real webshell code first — the guard `_shell_registry` only allows filenames that contained `<?php system(...)` etc. A plain `.php` file with no payload is NOT registered.

### Data volumes
Both containers share named volumes:
- `honeypot-logs` → honeypot writes, dashboard reads (read-only)
- `honeypot-db` → shared SQLite state

Data survives `docker compose down`. Only `down -v` removes it.
