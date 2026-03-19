# Maze Myth — Deployment Guide

> **One approach. One command. Production-ready.**  
> We removed Kubernetes and Helm — they are overkill for a honeypot.  
> Docker Compose is all you need for a real server or VPS.

---

## What Changed & Why

| Before | After | Reason |
|---|---|---|
| `flask run` (dev server) | **Gunicorn** (production WSGI) | Flask dev server crashes under load, is single-threaded, and is not safe to expose |
| Two separate Dockerfiles | **One Dockerfile, two targets** | Less duplication — same builder stage, same base image |
| k8s/ + helm/ folders | **Deleted** | Overkill for this project — adds complexity with zero benefit |
| Dashboard on port 8050 | **Port 8002** | Matches `dashboard/monitor.py` actual code |

---

## Project Layout (docker files)

```
docker/
├── Dockerfile            ← Single file, two build targets: `honeypot` and `dashboard`
├── docker-compose.yaml   ← Launches both services
└── .dockerignore         ← Excludes venv, logs, secrets from the image

.github/workflows/
└── docker-publish.yml    ← CI: auto-build & push to GHCR on git push
```

---

## Prerequisites

- [Docker Desktop](https://docs.docker.com/get-docker/) (Windows/Mac) **or** Docker Engine (Linux)
- Docker Compose v2 (included with Docker Desktop)

That's it.

---

## Step-by-Step: Run with Docker Compose

### Step 1 — Set your API key

```bash
cp .env.template .env
```

Edit `.env`:

```env
GOOGLE_API_KEY=AIzaSy...your-real-key-here...
HONEYPOT_URL=http://YOUR_SERVER_IP:8001
LLM_MODEL=gemini-2.0-flash
```

> If you don't have a Google API key yet the honeypot still starts — it falls back to template responses.

---

### Step 2 — Build the images

```bash
docker compose -f docker/docker-compose.yaml build
```

What happens:
1. **Stage 1 (builder)** — installs all Python packages + gunicorn into `/install`
2. **Stage 2 (base)** — creates a lean Python image with only runtime libraries
3. **Target `honeypot`** — copies everything, starts gunicorn on port 8001 (4 workers)
4. **Target `dashboard`** — copies everything, starts gunicorn on port 8002 (2 workers)

The final images are ~200–250 MB each (versus ~700 MB if we didn't use multi-stage).

---

### Step 3 — Start

```bash
docker compose -f docker/docker-compose.yaml up -d
```

`-d` = detached (runs in background). Both containers start automatically.  
The dashboard waits for the honeypot health check to pass before starting.

---

### Step 4 — Verify

```bash
docker compose -f docker/docker-compose.yaml ps
```

```
NAME                    STATUS          PORTS
maze-myth-honeypot      Up (healthy)    0.0.0.0:8001->8001/tcp
maze-myth-dashboard     Up (healthy)    0.0.0.0:8002->8002/tcp
```

| Service | URL |
|---|---|
| 🎯 Honeypot API | http://localhost:8001 |
| 📊 Monitoring Dashboard | http://localhost:8002 |

---

### Step 5 — View live logs

```bash
# All services
docker compose -f docker/docker-compose.yaml logs -f

# Honeypot only
docker compose -f docker/docker-compose.yaml logs -f honeypot

# Dashboard only
docker compose -f docker/docker-compose.yaml logs -f dashboard
```

---

### Step 6 — Stop

```bash
# Stop without deleting data
docker compose -f docker/docker-compose.yaml down

# Stop AND delete all stored logs/data
docker compose -f docker/docker-compose.yaml down -v
```

**Data** (logs, state DB, generated files) lives in named Docker volumes and **survives** a normal `down`. Only `down -v` wipes it.

---

## Update After Code Changes

```bash
# Rebuild images with latest code
docker compose -f docker/docker-compose.yaml build --no-cache

# Restart containers
docker compose -f docker/docker-compose.yaml up -d
```

---

## Deploy to a VPS (e.g. Ubuntu server)

```bash
# 1. Copy project to server
scp -r . user@YOUR_SERVER_IP:/opt/maze-myth

# 2. SSH in
ssh user@YOUR_SERVER_IP
cd /opt/maze-myth

# 3. Set up .env
cp .env.template .env
nano .env    # fill in GOOGLE_API_KEY and HONEYPOT_URL=http://YOUR_SERVER_IP:8001

# 4. Run
docker compose -f docker/docker-compose.yaml up -d
```

**Open firewall ports** if needed:
```bash
ufw allow 8001/tcp   # honeypot (attacker-facing)
ufw allow 8002/tcp   # dashboard (restrict to your IP only!)
```

> ⚠️ **Security tip:** Never expose port 8002 publicly. Use an SSH tunnel to view the dashboard:
> ```bash
> ssh -L 8002:localhost:8002 user@YOUR_SERVER_IP
> ```
> Then open http://localhost:8002 on your local machine.

---

## Why Gunicorn?

| | Flask `run` (dev) | Gunicorn (production) |
|---|---|---|
| Workers | 1 single-threaded | 4 workers × 2 threads |
| Concurrent requests | 1 at a time | ~8 at a time |
| Crash recovery | App dies = gone | Worker crashes = gunicorn restarts it |
| Safe to expose | ❌ No | ✅ Yes |
| Startup time | Instant | ~2 seconds |

Gunicorn config used: `--workers 4 --threads 2 --timeout 120`  
The 120-second timeout allows slow Gemini API calls to complete without killing the request.

---

## Troubleshooting

### Container exits immediately

```bash
docker compose -f docker/docker-compose.yaml logs honeypot
```

Common cause: missing `GOOGLE_API_KEY` environment variable. Check your `.env` file.

### Port already in use

```bash
# See what is using port 8001
netstat -ano | findstr :8001   # Windows
lsof -i :8001                   # Linux/Mac
```

Change the port in `.env`:
```env
HONEYPOT_PORT=9001
DASHBOARD_PORT=9002
```

### Image build fails

Make sure Docker has at least **2 GB of disk space** and **1 GB of RAM** available.  
On Windows: Docker Desktop → Settings → Resources.

### Data is shared between containers

Both containers mount the **same named volumes**:
- `honeypot-logs` → honeypot writes, dashboard reads (read-only)
- `honeypot-db` → honeypot writes, dashboard reads (read-only)

This is intentional — the dashboard reads the honeypot's logs live.
