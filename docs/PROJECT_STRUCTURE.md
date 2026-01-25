# Project Structure Guide

## Overview
Dynamic Banking API Honeypot with AI-powered responses and file tracking.

## Directory Structure

```
Maze-Myth-Dynamic-Honeypot/
├── honeypot.py           # Main Flask application (35KB)
├── requirements.txt      # Python dependencies
├── run_honeypot.bat      # Windows startup script
├── setup_honeypot.py     # Initial setup script
├── README.md             # Project documentation
├── LICENSE               # MIT License
├── .gitignore            
│
├── config/
│   └── .env.template     # Environment variables template
│   └── .env              # Your API keys (create from template)
│
├── src/                  # Source modules
│   ├── __init__.py
│   ├── api_generator/    # API maze and HTTP responses
│   │   ├── maze_generator.py
│   │   └── http_responses.py
│   ├── data_generator/   # Dynamic banking data
│   │   └── banking_data.py
│   ├── file_generator/   # Tracked file generation
│   │   ├── generator.py       # PDF, Excel
│   │   ├── multi_format_gen.py # XML, CSV, JS, JSON
│   │   ├── sqlite_gen.py      # SQLite databases
│   │   └── txt_gen.py         # Text files
│   ├── llm/              # Gemini AI integration
│   │   └── llm_integration.py
│   ├── rag/              # RAG context loader
│   │   └── rag_loader.py
│   └── state/            # State management
│       └── state_manager.py
│
├── dashboard/            # Real-time monitoring
│   ├── index.html        # Dashboard UI
│   └── monitor.py        # Flask monitoring server
│
├── databases/            # Runtime: TinyDB state
├── generated_files/      # Runtime: Generated bait files
└── log_files/            # Runtime: Audit logs
```

## Key Components

### honeypot.py
Main application with 50+ banking API endpoints:
- `/companies` - Company management (8-20 dynamic entries)
- `/api/v1/accounts` - Account data (15-40 entries)
- `/api/v1/transactions` - Transaction history (20-100 entries)
- `/api/v1/payments` - Payment processing (10-35 entries)
- `/merchants` - Merchant management (8-25 entries)
- `/api/v1/reports` - Report downloads (PDF, CSV, XML, DB)
- `/api/v2/admin` - Admin panel with secrets
- `/internal` - Internal config and backups

### src/data_generator/banking_data.py
Generates random banking data on each request:
- Real-looking IDs (ACC847291038, TXN3847562910)
- Random company names, balances, dates
- Varies counts per category on each call

### src/file_generator/
Generates tracked bait files:
- **PDF**: Financial reports with embedded beacons
- **Excel**: Transaction spreadsheets
- **SQLite/DB**: Fake database files
- **XML**: Audit logs, webhook configs
- **CSV**: Transaction exports
- **JSON**: API credentials, configs
- **JS**: Terminal configurations
- **TXT**: Database credentials

### dashboard/
Real-time monitoring:
- Tracks all API access
- Monitors file downloads
- Alerts on sensitive file access
- Shows attacker activity

## Running the System

```bash
# Install dependencies
pip install -r requirements.txt

# Set Gemini API key
copy config\.env.template config\.env
# Edit .env with your API key

# Start honeypot (port 8001)
python honeypot.py

# Start dashboard (port 8002) - separate terminal
python dashboard/monitor.py
```

## Ports
- **8001**: Honeypot API
- **8002**: Dashboard/Monitor
