# Project Daedalus: Real-Time Honeypot Monitor

**Real-time monitoring dashboard for the Maze Myth API deception honeypot.**

> _Monitor attackers as they fall into the maze—watch every step in real-time._

Simple, clean dashboard that monitors **all honeypot activity in real-time**.

## Features

✅ **Live Activity Feed** - See every action as it happens  
✅ **Auto-Discovery** - Track new API endpoints being found  
✅ **Attack Monitoring** - View all requests and attack attempts  
✅ **File Downloads** - Monitor when bait files are downloaded  
✅ **Beacon Alerts** - Get notified when beacons activate  
✅ **Clean UI** - Cyber-ops aesthetic with color-coded events

## Quick Start

```bash
cd daedalus-dashboard
start.bat
```

This will:
1. Start the honeypot on port 8001
2. Start the dashboard on port 8002
3. Open your browser automatically

## Dashboard Metrics Explained

The dashboard shows **5 real-time counters** at the top:

### 1. **TOTAL ENDPOINTS**
- **What it counts**: Unique API endpoints discovered by attackers
- **When it increments**: When honeypot logs `NEW_ENDPOINT_DISCOVERY` event
- **Example triggers**:
  - First access to `/api/v1/users`
  - First access to `/api/v2/admin/secrets`
  - Any new path that hasn't been seen before
- **Data source**: Parses `endpoint` field from discovery events
- **Note**: Only counts unique endpoints (duplicates ignored)

### 2. **TOTAL ACTIVITY**  
- **What it counts**: All logged events in the activity feed
- **When it increments**: For every decoded log entry added to the feed
- **Example triggers**:
  - Any HTTP request logged
  - File downloads
  - Beacon activations
  - Auth attempts
  - Maze navigation
- **Data source**: Total count of `recent_activity` entries (max 100)
- **Note**: This is the total volume of activity being monitored

### 3. **NEW DISCOVERIES**
- **What it counts**: Number of new endpoint discovery events
- **When it increments**: Same as Total Endpoints but counts occurrences, not unique entries
- **Example triggers**:
  - Every time honeypot logs `[MAZE] NEW endpoint: ...`
  - First attacker finding `/api/users` = +1
  - Second attacker finding same endpoint = +1 (tracked separately from total endpoints)
- **Data source**: Counts `type: 'discovery'` in activity entries
- **Note**: Shows reconnaissance activity volume

### 4. **FILE DOWNLOADS**
- **What it counts**: Bait files downloaded from the honeypot
- **When it increments**: When honeypot logs `file_download` event
- **Example triggers**:
  - Access to `/api/download/secrets.env`
  - Access to `/api/download/admin_keys.pdf`
  - Any file served from download endpoints
- **Data source**: Counts `type: 'download'` in activity entries
- **Note**: Indicates attackers are taking the bait

### 5. **BEACON ACTIVATIONS**
- **What it counts**: Downloaded files that "phone home" when opened
- **When it increments**: When honeypot logs `BEACON_ACTIVATED` event  
- **Example triggers**:
  - Attacker opens downloaded PDF (embedded tracking pixel loads)
  - Attacker opens ENV file with beacon URL
  - Tracking pixel request hits `/track/<beacon_id>`
- **Data source**: Counts `type: 'beacon'` in activity entries
- **Note**: **CRITICAL METRIC** - Confirms attackers opened the bait files

---

## What You'll See in the Activity Feed

The feed displays **real-time** color-coded events:

- 🔍 **New Endpoint Discoveries** (Cyan) - When attackers find new APIs
- 📄 **File Downloads** (Amber) - When bait files (PDFs/ENVs) are accessed
- 🚨 **Beacon Activations** (Red, pulsing) - When downloaded files phone home
- 🔐 **Authentication Attempts** (Default) - Login and elevation requests
- 🌐 **All HTTP Requests** (Default) - Every GET, POST, PUT, DELETE

## Testing

Run the demo attack:
```bash
cd ..
python tests\demo_maze_attack.py
```

Watch your dashboard update in real-time!

## How It Works

1. **Honeypot** runs and logs all activity to `log_files/api_audit.log` (Base64 encoded)
2. **Monitor Backend** (`monitor.py`) reads the log file continuously
3. **Dashboard** polls the backend every 2 seconds for new events
4. **Live Feed** updates automatically with color-coded entries

## Files

- `monitor.py` - Backend server that reads honeypot logs
- `index.html` - Dashboard UI (self-contained)
- `start.bat` - One-click startup script

---

**Status**: ✅ Operational  
**Complexity**: Minimal  
**Dependencies**: Flask, Flask-CORS

Enjoy monitoring your honeypot! 🍯
