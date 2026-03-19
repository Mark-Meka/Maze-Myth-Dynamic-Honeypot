# Maze Myth

**A dynamic API honeypot that generates deception paths to keep attackers trapped in an ever-changing maze.**

> _A Dynamic API Deception Maze that traps attackers psychologically._

---

## 🔥 The Problem

Traditional honeypots are **easily fingerprinted** and abandoned:

- **Static endpoints** are trivial to detect
- **Predictable responses** reveal they're fake
- **Limited interaction** makes attackers suspicious
- **Same data** for every attacker

**Result**: You capture 10 seconds of reconnaissance before they disappear.

---

## 🧠 The Solution

**Maze Myth** introduces a **dynamic deception maze** where:
1. **Every Request Yields New Data**: No two API calls return the same data. IDs, balances, and names are randomized on the fly.
2. **Infinite Depth**: The maze never ends. New endpoints and files are generated on demand.
3. **Psychological Entrapment**: Breadcrumbs and "success" signals keep attackers engaged for hours.

### Core Concept

```
Attacker discovers /api/v1/login
    ↓
Success! Gets token → /api/v1/users appears
    ↓
More endpoints emerge → /api/v2/admin/secrets
    ↓
"Secrets" file downloads → Opens PDF/DB with beacon
    ↓
Beacon fires → We track their exact location
    ↓
Still exploring... forever trapped in the maze
```
---

## How a Request Flows Through the System

```
Attacker hits any URL
        │
        ▼
honeypot.py receives it
        │
        ├─→ Fixed route? (e.g. /api/v1/accounts)
        │       └─→ BankingDataGenerator generates fresh data
        │               └─→ Return JSON response
        │
        └─→ Dynamic catch-all (unknown path)
                │
                ├─→ maze_generator validates path & assigns access level
                │
                ├─→ LLMGenerator calls Gemini API with path context
                │       └─→ Returns realistic JSON
                │
                ├─→ 20% chance: FileGenerator creates a bait file
                │       └─→ Beacon ID saved to SQLite beacons table
                │
                ├─→ Response saved to SQLite endpoints table
                │       (same URL → same AI response forever)
                │
                └─→ Return JSON + optional _attachments download link
```

---

## ✅ Upgrade Status

| # | Upgrade | Status |
|---|---|---|
| 1 | Containerize + Docker Compose (Gunicorn) | ✅ Done |
| 2 | Replace TinyDB with SQLite (WAL mode) | ✅ Done |
| 3 | LLM Offline Fallback (Ollama) | 🔜 Planned |
| 4 | Full Config System (`config.yaml`) | 🔜 Planned |
| 5 | IP Reputation Scoring | 🔜 Planned |
| 6 | Firewall Export + Auto-Ban | 🔜 Planned |
| 7 | Tarpit Mode | 🔜 Planned |
| 8 | Webhook + SIEM Alerts | 🔜 Planned |

> See [DEPLOYMENT.md](DEPLOYMENT.md) for deployment instructions.

---

## 🚀 Key Features

### 1. Dynamic Data Generator
Generates fresh, realistic banking data for every request:
- **Companies**: 8–20 random companies per call
- **Accounts**: 15–40 accounts with realistic balances ($10k–$50M)
- **Transactions**: 20–100 unique transactions per account
- **Payments**: Wire, ACH, SWIFT payments with status tracking
- **Users**: Admin, finance, and report users

### 2. Multi-Format Bait Files
Tracked files in **10+ formats**, each with embedded beacons:
- **PDF**: Financial reports, statements
- **Excel (.xlsx)**: Transaction spreadsheets
- **Database (.db, .sqlite)**: Full SQLite databases with tables
- **CSV**: Data exports, XML, JSON credentials, JavaScript configs, SQL schema dumps

### 3. AI-Powered Responses
Integration with **Google Gemini 2.0 Flash**:
- Generates context-aware JSON responses
- Simulates realistic error messages
- Adapts to attacker inputs

### 4. Real-Time Dashboard
Monitor the attack as it happens on `http://localhost:8002`:
- **Live Feed**: See every endpoint hit
- **Download Tracking**: Watch attackers steal files
- **Beacon Alerts**: Know exactly when a file is opened
- **Sensitive Data Alerts**: Critical warnings for admin/secret access

---

## 📁 Architecture

```
Maze-Myth-Dynamic-Honeypot/
├── honeypot.py               # Main Flask application
├── requirements.txt          # Python dependencies
├── run_honeypot.bat          # Windows: start everything locally
├── setup_honeypot.py         # Initial directory setup
├── DEPLOYMENT.md             # Docker / production guide
│
├── docker/                   # Container files (Upgrade 1)
│   ├── Dockerfile            # Multi-stage build (honeypot + dashboard targets)
│   ├── docker-compose.yaml   # One-command production launch
│   └── .dockerignore
│
├── .github/workflows/
│   └── docker-publish.yml    # CI: auto-build & push to GHCR
│
├── src/                      # Core Modules
│   ├── api_generator/        # API maze and routing logic
│   ├── data_generator/       # Dynamic banking data generation
│   ├── file_generator/       # Tracked bait file creation
│   ├── llm/                  # Gemini AI integration
│   ├── rag/                  # RAG context loader
│   └── state/                # State persistence
│
├── dashboard/                # Monitoring System
│   ├── index.html            # Dashboard UI
│   └── monitor.py            # Dashboard Flask backend (port 8002)
│
├── databases/                # Runtime state storage
├── generated_files/          # Generated bait files
└── log_files/                # Encoded audit logs
```

---

## 🚀 Quick Start

### Option A — Docker (Recommended, production-ready)

Requires [Docker Desktop](https://docs.docker.com/get-docker/).

```bash
# 1. Clone
git clone https://github.com/Mark-Meka/Maze-Myth-Dynamic-Honeypot.git
cd Maze-Myth-Dynamic-Honeypot

# 2. Set your API key
cp .env.template .env
# Edit .env and add: GEMINI_API_KEY=your_key_here

# 3. Build and start both services
docker compose -f docker/docker-compose.yaml build
docker compose -f docker/docker-compose.yaml up -d
```

| Service | URL |
|---|---|
| 🎯 Honeypot API | http://localhost:8001 |
| 📊 Monitoring Dashboard | http://localhost:8002 |

```bash
# View live logs
docker compose -f docker/docker-compose.yaml logs -f

# Stop
docker compose -f docker/docker-compose.yaml down
```

---

### Option B — Local Python (Windows, development)

Use **`run_honeypot.bat`** — it handles everything automatically:

```
Double-click run_honeypot.bat
```

Or from a terminal:

```cmd
run_honeypot.bat
```

The script will:
1. Check Python is installed
2. Create and activate the virtual environment
3. Install all dependencies if missing
4. Start the **honeypot** on `http://localhost:8001`
5. Open a second window for the **dashboard** on `http://localhost:8002`

---

### Option C — Manual (any OS)

```bash
# Clone and install
git clone https://github.com/Mark-Meka/Maze-Myth-Dynamic-Honeypot.git
cd Maze-Myth-Dynamic-Honeypot
pip install -r requirements.txt

# Configure
cp .env.template .env
# Edit .env: add GEMINI_API_KEY=your_key_here

# Terminal 1 — Honeypot
python honeypot.py

# Terminal 2 — Dashboard
python dashboard/monitor.py
```

---

## 🎭 Attack Scenario

1. **Discovery** — Attacker scans and finds `/api/v1/auth/login`. Tries `admin:admin`. Gets a JWT token and breadcrumb to `/api/v1/users`.
2. **Exploration** — Lists users. Gets 12 realistic randomized users. Hint at `/api/v2/admin`.
3. **Escalation** — Hits `/api/v2/admin/secrets`. Returns `encryption_keys.json`, `master_api_key.txt`.
4. **Exfiltration** — Downloads `master_api_key.txt`. A CRITICAL event fires. Dashboard flashes alert. File has embedded tracking beacon.
5. **Consumption** — Attacker opens the file. Beacon fires. They're tracked — and the maze continues forever.

---

## 🔒 Security Warning

> ⚠️ This is a deception tool. Run in an isolated environment (VM/container/VLAN). Do not expose the dashboard port (8002) publicly — it is for operators only. Use an SSH tunnel to view it remotely.

---

## 📜 License

MIT License — See [LICENSE](LICENSE)

---

## 📞 Contact

- **Author**: Mark Meka
- **GitHub**: [@Mark-Meka](https://github.com/Mark-Meka)
