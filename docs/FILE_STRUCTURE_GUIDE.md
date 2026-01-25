# File Structure Guide

## Core Files

| File | Purpose | Size |
|------|---------|------|
| `honeypot.py` | Main Flask app with 50+ API endpoints | 35KB |
| `requirements.txt` | Python dependencies | 614B |
| `run_honeypot.bat` | Windows startup script | 2KB |
| `setup_honeypot.py` | Initial configuration | 2KB |

## Source Modules (`src/`)

### api_generator/
| File | Purpose |
|------|---------|
| `maze_generator.py` | API endpoint validation, access levels, breadcrumbs |
| `http_responses.py` | HTTP response templates (401, 403, 404, 500) |

### data_generator/
| File | Purpose |
|------|---------|
| `banking_data.py` | Dynamic data generator for all API responses |

**BankingDataGenerator Methods:**
- `generate_companies(count)` → 8-20 companies
- `generate_accounts(count)` → 15-40 accounts
- `generate_transactions(count)` → 20-100 transactions
- `generate_payments(count)` → 10-35 payments
- `generate_merchants(count)` → 8-25 merchants
- `generate_terminals(merchant_id)` → 3-15 terminals
- `generate_users(count)` → 5-15 admin users
- `generate_reports()` → 14-22 report files
- `generate_backups()` → 5-12 backup files
- `generate_secrets()` → 10 secret entries

### file_generator/
| File | Purpose |
|------|---------|
| `generator.py` | PDF and Excel generation with beacons |
| `multi_format_gen.py` | XML, CSV, JS, JSON generation |
| `sqlite_gen.py` | SQLite database generation |
| `txt_gen.py` | Text file generation (credentials, configs) |

**Supported File Types:**
- `.pdf` - Financial reports, statements
- `.xlsx` - Transaction spreadsheets
- `.csv` - Data exports
- `.xml` - Audit logs, webhook configs
- `.json` - API credentials, configs
- `.js` - Terminal configurations
- `.db` / `.sqlite` - Database files
- `.txt` - Credential files, connection strings

### llm/
| File | Purpose |
|------|---------|
| `llm_integration.py` | Gemini AI integration for realistic responses |

### rag/
| File | Purpose |
|------|---------|
| `rag_loader.py` | RAG context loader for banking terminology |
| `metadata.json` | RAG configuration |

### state/
| File | Purpose |
|------|---------|
| `state_manager.py` | TinyDB persistence for endpoints, beacons, downloads |

**State Tables:**
- `endpoints` - Generated API endpoints
- `objects` - Created objects (users, products)
- `beacons` - File tracking beacons
- `downloads` - File download history

## Dashboard (`dashboard/`)

| File | Purpose |
|------|---------|
| `index.html` | Real-time monitoring UI |
| `monitor.py` | Flask server for dashboard API |

**Dashboard Endpoints:**
- `GET /` - Dashboard UI
- `GET /api/activity` - Recent activity
- `GET /api/new` - New activity since last check
- `GET /api/stats` - Statistics
- `GET /api/downloads` - File download history
- `GET /api/sensitive` - Sensitive file downloads

## Configuration (`config/`)

| File | Purpose |
|------|---------|
| `.env.template` | Environment template |
| `.env` | Your API keys (not in git) |

**Environment Variables:**
```
GEMINI_API_KEY=your-api-key
HONEYPOT_URL=http://localhost:8001
LLM_MODEL=gemini-2.0-flash
```

## Runtime Directories

| Directory | Purpose |
|-----------|---------|
| `databases/` | TinyDB JSON files |
| `generated_files/` | Downloaded bait files |
| `log_files/` | Base64-encoded audit logs |
