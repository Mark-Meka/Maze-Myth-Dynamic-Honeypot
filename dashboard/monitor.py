"""
Simple Real-Time Honeypot Monitor
Streams honeypot activity to dashboard
"""

from flask import Flask, jsonify, send_file
from flask_cors import CORS
import sys
import base64
import json
import re
from pathlib import Path
from datetime import datetime
from collections import deque

sys.path.insert(0, str(Path(__file__).parent.parent))
from src.state import APIStateManager

app = Flask(__name__)
CORS(app)

state = APIStateManager()
log_file = Path(__file__).parent.parent / "log_files" / "api_audit.log"

# Store recent activity
recent_activity = deque(maxlen=100)
last_position = 0

def decode_log(line):
    """Decode Base64 log entry"""
    try:
        return base64.b64decode(line.strip()).decode('utf-8', errors='ignore')
    except Exception:
        return None

def parse_log_entry(log_text):
    """Extract info from log entry"""
    entry = {'timestamp': '', 'level': '', 'message': '', 'type': 'general', 'data': {}}
    
    # Extract timestamp
    ts_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', log_text)
    if ts_match:
        entry['timestamp'] = ts_match.group(1)
    
    # Extract level
    if ' - WARNING - ' in log_text:
        entry['level'] = 'WARNING'
    elif ' - CRITICAL - ' in log_text:
        entry['level'] = 'CRITICAL'
    elif ' - INFO - ' in log_text:
        entry['level'] = 'INFO'
    elif ' - ERROR - ' in log_text:
        entry['level'] = 'ERROR'
    
    # Try to parse JSON in message
    json_match = re.search(r'\{.*\}', log_text)
    if json_match:
        try:
            data = json.loads(json_match.group())
            entry['data'] = data
            
            # Categorize by JSON event field
            if 'event' in data:
                if data['event'] == 'BEACON_ACTIVATED':
                    entry['type'] = 'beacon'
                    entry['message'] = f"🚨 Bait file opened from {data.get('ip', 'Unknown')}"
                    return entry
                elif data['event'] == 'file_download':
                    entry['type'] = 'download'
                    entry['message'] = f"📄 File download: {data.get('filename', 'unknown')} from {data.get('ip', 'Unknown')}"
                    return entry
                elif data['event'] == 'NEW_ENDPOINT_DISCOVERY':
                    entry['type'] = 'discovery'
                    entry['message'] = f"🔍 New endpoint: {data.get('method', 'GET')} {data.get('endpoint', '/')} from {data.get('ip', 'Unknown')}"
                    return entry
        except:
            pass
    
    # Text-based detection (for logs without JSON or as fallback)
    if 'BEACON_ACTIVATED' in log_text or '[BEACON]' in log_text:
        entry['type'] = 'beacon'
        entry['message'] = log_text.split(' - ')[-1] if ' - ' in log_text else log_text
    elif 'file_download' in log_text or 'File download' in log_text or '/api/download/' in log_text:
        entry['type'] = 'download'
        entry['message'] = log_text.split(' - ')[-1] if ' - ' in log_text else log_text
    elif 'NEW endpoint' in log_text or '[MAZE] NEW endpoint' in log_text or 'NEW_ENDPOINT_DISCOVERY' in log_text:
        entry['type'] = 'discovery'
        entry['message'] = log_text.split(' - ')[-1] if ' - ' in log_text else log_text
        # Try to extract endpoint from message
        endpoint_match = re.search(r'(GET|POST|PUT|DELETE|PATCH)\s+(/[\S]+)', log_text)
        if endpoint_match:
            entry['data']['method'] = endpoint_match.group(1)
            entry['data']['endpoint'] = endpoint_match.group(2)
    elif '[AUTH]' in log_text:
        entry['type'] = 'auth'
        entry['message'] = log_text.split(' - ')[-1] if ' - ' in log_text else log_text
    elif '[MAZE]' in log_text:
        entry['type'] = 'maze'
        entry['message'] = log_text.split(' - ')[-1] if ' - ' in log_text else log_text
    
    # Fallback message
    if not entry['message']:
        parts = log_text.split(' - ')
        entry['message'] = parts[-1] if len(parts) > 1 else log_text
    
    return entry

def check_for_new_logs():
    """Check for new log entries"""
    global last_position
    
    if not log_file.exists():
        return []
    
    new_entries = []
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            f.seek(last_position)
            for line in f:
                if line.strip():
                    decoded = decode_log(line)
                    if decoded:
                        entry = parse_log_entry(decoded)
                        new_entries.append(entry)
                        recent_activity.append(entry)
            last_position = f.tell()
    except Exception as e:
        print(f"[ERROR] Log read failed: {e}")
    
    return new_entries

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/activity')
def get_activity():
    """Get recent activity"""
    return jsonify(list(recent_activity))

@app.route('/api/new')
def get_new():
    """Get new activity since last check"""
    new = check_for_new_logs()
    return jsonify(new)

@app.route('/api/stats')
def get_stats():
    """Get statistics"""
    # Count activity types from actual entries
    type_counts = {'discovery': 0, 'auth': 0, 'download': 0, 'beacon': 0, 'maze': 0}
    unique_endpoints = set()
    
    for entry in recent_activity:
        entry_type = entry.get('type', 'general')
        if entry_type in type_counts:
            type_counts[entry_type] += 1
        
        # Extract endpoint from discovery events
        if entry_type == 'discovery' and 'data' in entry:
            endpoint = entry['data'].get('endpoint', '')
            if endpoint:
                unique_endpoints.add(endpoint)
    
    # Try to get state stats, but use calculated values if it fails
    total_endpoints = len(unique_endpoints)
    try:
        stats = state.get_statistics()
        if stats.get('total_endpoints', 0) > total_endpoints:
            total_endpoints = stats.get('total_endpoints', 0)
    except:
        pass
    
    return jsonify({
        'total_endpoints': total_endpoints,
        'total_entries': len(recent_activity),
        'type_counts': type_counts
    })

if __name__ == '__main__':
    print("\n" + "="*60)
    print("[DAEDALUS] Real-Time Monitor Starting")
    print("="*60)
    print(f"[API] http://localhost:8002")
    print(f"[DASHBOARD] http://localhost:8002")
    print("="*60 + "\n")
    
    # Load existing logs on startup
    if log_file.exists():
        try:
            with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
                for line in lines[-50:]:  # Last 50 entries
                    if line.strip():
                        try:
                            decoded = decode_log(line)
                            if decoded:
                                entry = parse_log_entry(decoded)
                                recent_activity.append(entry)
                        except:
                            continue
                last_position = f.tell()
        except Exception as e:
            print(f"[WARNING] Could not load existing logs: {e}")
            last_position = 0
    
    app.run(host='0.0.0.0', port=8002, debug=False, use_reloader=False)
