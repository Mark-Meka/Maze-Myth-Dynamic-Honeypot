# How to Run the Dynamic API Honeypot

Complete guide to running your honeypot system with real-time monitoring.

## Quick Start (4 Steps)

### Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Setup Directories

```bash
python setup_honeypot.py
```

This creates:
- `log_files/` - Audit logs
- `databases/` - State persistence
- `generated_files/` - Bait files (SQLite, PDF, TXT)
- `static/` - Tracking pixels

### Step 3: Configure API Key

Set your Gemini API key:

```bash
# Windows
set GEMINI_API_KEY=your-api-key-here

# Linux/Mac
export GEMINI_API_KEY=your-api-key-here
```

### Step 4: Start the Honeypot

```bash
python honeypot.py
```

You should see:
```
[HONEYPOT] Dynamic API Honeypot with Maze System Started
[RAG] Loaded context: 3 patterns, 2 schemas, 1 samples
[LLM] Enabled (Gemini)
[FILE_GEN] Generators ready: SQLite, PDF, Excel, TXT
[SERVER] http://localhost:8001
[SERVER] Press CTRL+C to quit
```

## Advanced: Real-Time Dashboard

### Start Dashboard (Recommended)

In a new terminal:

```bash
cd dashboard
python monitor.py
```

Then open: **http://localhost:8002**

The dashboard shows:
- 🔍 Live activity feed
- 📊 Real-time statistics
- 🚨 Beacon activations
- 📄 File downloads with IP tracking
- 🔢 Unique endpoint discoveries

### One-Click Startup (Windows)

```bash
cd dashboard
start.bat
```

This automatically:
1. Starts honeypot on port 8001
2. Starts dashboard on port 8002  
3. Opens browser to dashboard

## Accessing the Honeypot

- **Root API:** http://localhost:8001/
- **Health Check:** http://localhost:8001/health
- **API Documentation:** http://localhost:8001/docs
- **Dashboard:** http://localhost:8002 (if running)

## Testing

### Basic Test
```bash
curl http://localhost:8001/health
```

### Test Dynamic Endpoints
```bash
curl http://localhost:8001/api/v1/users
curl http://localhost:8001/api/v2/admin/secrets
```

### Test File Downloads
```bash
# Download SQLite database
curl http://localhost:8001/api/data/export -o data.db

# Download credentials file
curl http://localhost:8001/api/config/secrets -o secrets.txt

# Download PDF
curl http://localhost:8001/api/reports/financial -o report.pdf
```

Watch the dashboard update in real-time as you make requests!

### Full Test Suite
```bash
python tests/test_api_honeypot.py
```

### Attack Simulation
```bash
python tests/demo_maze_attack.py
```

Watch the dashboard for live updates during the simulation!

## New Features

### RAG-Based Context
The honeypot now uses RAG (Retrieval-Augmented Generation) with banking API context:
- Consistent API responses across endpoints
- Realistic schemas and data
- Context-aware file generation

### Enhanced File Generation
Multiple file types automatically generated based on endpoint:
- **SQLite databases** - Customer, transaction, account data
- **PDF files** - Reports with tracking beacons
- **TXT files** - Logs, configs, credentials
- **ENV files** - Fake API keys and secrets

All files tracked with IP addresses and timestamps!

### Download Tracking
Every file download is logged with:
- Downloader's IP address
- Filename and type
- Source API endpoint
- Timestamp
- Beacon activation (when file is opened)

## Configuration

**Change Port:** Edit `honeypot.py`, search for `port=8001`

**Gemini API Key:** Set `GEMINI_API_KEY` environment variable

**Dashboard Port:** Edit `dashboard/monitor.py`, search for `port=8002`

## Monitoring Activity

### Real-Time Dashboard (Recommended)
Open http://localhost:8002 to see:
- Live activity feed
- Download events
- Beacon activations
- Statistics

### View Logs Manually
```bash
python utils/read_logs.py
```

### Tail Last 50 Entries
```bash
python utils/read_logs.py --tail 50
```

## Troubleshooting

**Database Error:** Delete `databases/api_state.json` and restart

**Port In Use:** Change port or kill existing process

**Module Not Found:** Run `pip install -r requirements.txt`

**Dashboard Not Showing Data:** Make sure honeypot is running first

**No Files Generated:** Check `generated_files/` folder permissions

## What Gets Generated

Each honeypot run creates:
- **New API structure** - Different endpoints each time
- **Unique bait files** - SQLite, PDF, TXT with fake data
- **Tracking beacons** - Embedded in all files
- **Audit logs** - Base64-encoded activity trail

## More Info

See [README.md](../README.md) for complete documentation.
