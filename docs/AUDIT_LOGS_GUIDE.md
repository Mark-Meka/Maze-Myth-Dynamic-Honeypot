# Audit Logs Guide - Security & Monitoring

## Overview

The honeypot writes **Base64-encoded audit logs** to prevent attackers from easily reading log files if they gain file system access. All honeypot activity is logged with detailed information.

## How It Works

### 1. Log Generation (Automatic)

When the honeypot runs, all events are encoded before being written to:
```
log_files/api_audit.log
```

The file will look like gibberish:
```
MjAyNS0xMi0wNSAwMTozNjoyMCAtIElORk8gLSBbTUFaRV0gR0VUIC9hcGkvdjEvdXNlcnMgfCBBY2Nlc3M6IHB1YmxpYyB8IElQOiAxMjcuMC4wLjE=
```

### 2. Reading Logs (Manual)

To decode and read the logs, you **MUST** use the provided script:

```bash
python utils/read_logs.py
```

**DO NOT** try to read the log file directly with:
- ❌ `type log_files\api_audit.log` - Will show gibberish
- ❌ `cat log_files/api_audit.log` - Will show gibberish
- ❌ Opening in text editor - Will show gibberish

**ONLY USE:**
- ✅ `python utils/read_logs.py` - Properly decodes and displays logs
- ✅ **Dashboard** - http://localhost:8002 for real-time viewing

## Real-Time Monitoring (Recommended)

### Using the Dashboard

The **easiest way** to view logs is through the real-time dashboard:

```bash
cd dashboard
python monitor.py
```

Then open: **http://localhost:8002**

**Dashboard Features:**
- 🔴 Live activity feed (updates every 2 seconds)
- 📊 Real-time counters
- 🔍 Endpoint discoveries
- 📄 File downloads with IP addresses
- 🚨 Beacon activations
- Color-coded event types

## Manual Log Reading

### View All Logs
```bash
python utils/read_logs.py
```

### View Last 50 Lines
```bash
python utils/read_logs.py --tail 50
```

### Search for Specific Events
```bash
# Windows
python utils/read_logs.py | findstr "BEACON"
python utils/read_logs.py | findstr "file_download"
python utils/read_logs.py | findstr "NEW_ENDPOINT"

# Linux/Mac
python utils/read_logs.py | grep "BEACON"
python utils/read_logs.py | grep "file_download"
python utils/read_logs.py | grep "NEW_ENDPOINT"
```

### Save Decoded Logs to File
```bash
python utils/read_logs.py > decoded_logs.txt
```

## Log Events and Format

### After Decoding

Once decoded, logs are in standard format with timestamps and event types:

```
2025-12-05 01:36:20 - INFO - [MAZE] GET /api/v1/users | Access: public | IP: 127.0.0.1
2025-12-05 01:36:25 - CRITICAL - [ATTACKER] {"event": "NEW_ENDPOINT_DISCOVERY", "ip": "192.168.1.100", ...}
2025-12-05 01:36:30 - CRITICAL - [BEACON_ACTIVATED] Bait file opened! IP: 45.33.32.156
2025-12-05 01:36:35 - WARNING - {"event": "file_download", "filename": "customers.db", "ip": "192.168.1.100", "endpoint": "/api/v1/data/export"}
```

### Event Types

The honeypot logs various event types:

#### 1. Endpoint Discoveries
```json
{
  "event": "NEW_ENDPOINT_DISCOVERY",
  "ip": "192.168.1.100",
  "method": "GET",
  "endpoint": "/api/v1/users",
  "timestamp": "2025-12-05T01:36:25Z"
}
```

#### 2. File Downloads
```json
{
  "event": "file_download",
  "ip": "45.33.32.156",
  "filename": "production.env",
  "file_type": "txt",
  "endpoint": "/api/config/secrets",
  "beacon_id": "a1b2c3d4-e5f6...",
  "timestamp": "2025-12-05T01:36:30Z"
}
```

#### 3. Beacon Activations
```json
{
  "event": "BEACON_ACTIVATED",
  "ip": "45.33.32.156",
  "beacon_id": "a1b2c3d4-e5f6...",
  "file_type": "pdf",
  "original_download_ip": "45.33.32.156",
  "timestamp": "2025-12-05T01:36:35Z"
}
```

#### 4. Authentication Attempts
```
[AUTH] Login attempt: username=admin, from IP: 192.168.1.100
[AUTH] Privilege elevation attempt from IP: 192.168.1.100
```

#### 5. API Navigation
```
[MAZE] GET /api/v1/users | Access: public | IP: 127.0.0.1
[MAZE] POST /api/v1/auth/login | Access: public | IP: 127.0.0.1
```

## Dashboard Event Categories

The dashboard categorizes events by type:

- **🔍 Discovery (Cyan)** - New endpoint found
- **📄 Download (Amber)** - File downloaded
- **🚨 Beacon (Red, Pulsing)** - Bait file opened
- **🔐 Auth (Default)** - Authentication attempts
- **🌐 Maze (Default)** - API navigation

## What Gets Tracked

### For Every Request:
- IP address
- Timestamp
- HTTP method
- Endpoint path
- Access level
- Response status

### For File Downloads:
- Downloader IP
- Filename and type (SQLite, PDF, TXT, ENV)
- Source endpoint
- Beacon ID
- File size
- Timestamp

### For Beacon Activations:
- IP address that opened the file
- Original download IP
- File type
- Beacon ID
- Time elapsed since download
- Timestamp

## Security Benefits

1. **Obfuscation** - Attackers cannot easily grep through logs
2. **Tamper Detection** - Modified logs will fail to decode
3. **Privacy** - IP addresses and sensitive data not immediately visible
4. **Defense in Depth** - Adds another layer of protection
5. **Real-Time Alerting** - Dashboard shows activity instantly

## Important Notes

⚠️ **Keep `utils/read_logs.py` secure!** - This is the only manual way to read the logs

⚠️ **Use Dashboard for monitoring** - Much easier than manual log reading

✅ **Logs are NOT encrypted** - They are Base64 encoded (obfuscated, not secure encryption)

✅ **Dashboard reads logs automatically** - No need to decode manually

## Analyzing Attack Patterns

### Using Dashboard

The dashboard automatically tracks:
- **Total Activity** - All logged events
- **Total Endpoints** - Unique API paths discovered
- **New Discoveries** - Reconnaissance attempts
- **File Downloads** - Bait files accessed
- **Beacon Activations** - Files opened by attackers

### Manual Analysis

Search for patterns in decoded logs:

```bash
# Find all file downloads
python utils/read_logs.py | findstr "file_download"

# Find all discoveries
python utils/read_logs.py | findstr "NEW_ENDPOINT"

# Find beacon activations
python utils/read_logs.py | findstr "BEACON_ACTIVATED"

# Find specific IP
python utils/read_logs.py | findstr "192.168.1.100"
```

## Log Rotation

Logs are appended to `log_files/api_audit.log`. For production:

1. Implement log rotation (size-based or time-based)
2. Archive old logs
3. Keep dashboard database small (it only loads recent activity)

---

**Pro Tip:** Use the dashboard (http://localhost:8002) for real-time monitoring. It's much easier than reading logs manually and provides instant visual feedback!

**Generated:** 2026-01-25  
**Honeypot Version:** 2.0  
**Encoding Method:** Base64  
**New Features:** RAG-based generation, SQLite/PDF/TXT files, Real-time dashboard
