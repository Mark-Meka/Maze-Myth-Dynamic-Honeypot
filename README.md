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

## 🚀 Key Features (NEW)

### 1. Dynamic Data Generator
Unlike static honeypots, **Maze Myth** generates fresh, realistic data for every request:
- **Companies**: 8-20 random companies per call
- **Accounts**: 15-40 accounts with realistic balances ($10k-$50M)
- **Transactions**: 20-100 unique transactions per account
- **Payments**: Wire, ACH, SWIFT payments with status tracking
- **Merchants & Terminals**: Real-looking POS terminal data
- **Users**: Admin, finance, and report users

### 2. Multi-Format Bait Files
We generate tracked files in **10+ formats**, each with embedded beacons:
- **PDF**: Financial reports, statements
- **Excel (.xlsx)**: Transaction spreadsheets
- **Database (.db, .sqlite)**: Full SQLite databases with tables
- **CSV**: Data exports
- **XML**: Audit logs, configuration files
- **JSON**: API credentials, secrets
- **JavaScript (.js)**: Terminal configurations
- **Text (.txt)**: Connection strings, keys
- **SQL**: Database schema dumps

### 3. AI-Powered Responses
Integration with **Google Gemini 2.0 Flash**:
- Generates context-aware JSON responses
- Simulates realistic error messages
- Adapts to attacker inputs

### 4. Real-Time Dashboard
Monitor the attack as it happens:
- **Live Feed**: See every endpoint hit
- **Download Tracking**: Watch attackers steal files
- **Beacon Alerts**: Know exactly when a file is opened
- **Sensitive Data Alerts**: Critical warnings for admin/secret access

---

## � Architecture

```
Maze-Myth-Dynamic-Honeypot/
├── honeypot.py           # Main Flask application (35KB)
├── requirements.txt      # Python dependencies
├── run_honeypot.bat      # Windows startup script
├── setup_honeypot.py     # Initial setup script
├── README.md             # Project documentation
├── config/               # Configuration
│   └── .env              # API keys and settings
│
├── src/                  # Core Modules
│   ├── api_generator/    # API maze and routing logic
│   ├── data_generator/   # Dynamic banking data generation
│   ├── file_generator/   # Tracked bait file creation
│   ├── llm/              # Gemini AI integration
│   ├── rag/              # RAG context loader
│   └── state/            # State persistence (TinyDB)
│
├── dashboard/            # Monitoring System
│   ├── index.html        # Dashboard UI
│   └── monitor.py        # Dashboard backend
│
├── databases/            # Runtime state storage
├── generated_files/      # Generated bait files
└── log_files/            # Encoded audit logs
```

---

## 🧪 Quick Start

### 1. Installation
```bash
# Clone the repo
git clone https://github.com/Mark-Meka/Maze-Myth-Dynamic-Honeypot.git
cd Maze-Myth-Dynamic-Honeypot

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration
Create a `.env` file in `config/` with your API key:
```ini
# config/.env
GEMINI_API_KEY=your_gemini_api_key
HONEYPOT_URL=http://localhost:8001
LLM_MODEL=gemini-2.0-flash
```

### 3. Run System
**Terminal 1: Honeypot**
```bash
python honeypot.py
# Running on http://0.0.0.0:8001
```

**Terminal 2: Dashboard**
```bash
python dashboard/monitor.py
# Running on http://0.0.0.0:8002
```

**Access Dashboard**: Open `http://localhost:8002` in your browser.

---

## 🎭 Attack Scenario

### 1. Discovery
Attacker scans and finds `/api/v1/auth/login`. They try credentials `admin:admin`.
**Response**: Success! Returns a JWT token and breadcrumbs to `/api/v1/users`.

### 2. Exploration
Attacker lists users.
**Response**: Returns 12 realistic users (randomized). Hints at `/api/v2/admin`.

### 3. Escalation
Attacker tries `/api/v2/admin/secrets`.
**Response**: Lists "encryption_keys.json", "master_api_key.txt".

### 4. Exfiltration
Attacker downloads `master_api_key.txt`.
**System Action**:
- Logs "FILE_DOWNLOAD" event (CRITICAL)
- Generates unique file with tracking ID
- Dashboard flashes alert

### 5. Consumption
Attacker opens the file.
**System Action**: 
- Beacon fires (if applicable)
- Attacker realizes it's fake... or keeps digging into the infinite data.

---

## 📊 Dashboard Metrics

The dashboard now provides advanced tracking:
- **Total Activity**: All hits
- **File Downloads**: Specific tracking of what files were taken
- **Sensitive Access**: Highlights attempts to access secrets/admin
- **Unique endpoints**: Tracks how deep they went

---

## 🔒 Security

**⚠️ Warning**: This is a deception tool.
- Run in an isolated environment (VM/VLAN).
- Do not expose to your internal network.
- Monitoring is passive; does not block attacks.

---

## 📜 License

MIT License - See [LICENSE](LICENSE)

---

## 📞 Contact

- **Author**: Mark Meka
- **GitHub**: [@Mark-Meka](https://github.com/Mark-Meka)
