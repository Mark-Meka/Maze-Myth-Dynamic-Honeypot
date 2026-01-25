# Audit Logs Guide

## Log Location
All logs are stored in `log_files/api_audit.log` as Base64-encoded entries.

## Log Levels

| Level | Meaning | Examples |
|-------|---------|----------|
| `INFO` | Normal API access | GET /api/v1/accounts |
| `WARNING` | Suspicious access | Admin endpoints, internal paths |
| `CRITICAL` | High-value targets | Secrets, credentials, file downloads |
| `ERROR` | System errors | Failed generations |

## Event Types

### API Access Events
```json
{
  "event": "NEW_ENDPOINT_DISCOVERY",
  "endpoint": "/api/v1/accounts",
  "method": "GET",
  "ip": "192.168.1.100",
  "timestamp": "2024-12-20T14:30:00Z"
}
```

### File Download Events
```json
{
  "event": "FILE_DOWNLOAD",
  "filename": "customer_data.db",
  "ip": "192.168.1.100",
  "user_agent": "curl/7.68.0",
  "timestamp": "2024-12-20T14:30:00Z"
}
```

### Beacon Activation
```json
{
  "event": "BEACON_ACTIVATED",
  "beacon_id": "abc123-def456",
  "file_type": "pdf",
  "ip": "192.168.1.100",
  "timestamp": "2024-12-20T14:30:00Z"
}
```

## High-Value Alerts

The following trigger **CRITICAL** alerts:

| Access Type | Endpoint Pattern |
|-------------|-----------------|
| Admin secrets | `/api/v2/admin/secrets` |
| API credentials | `/companies/*/apiCredentials` |
| Internal config | `/internal/config/*` |
| Database config | `/internal/config/database` |
| Backups | `/internal/backups` |

### Sensitive File Downloads
Any file containing these keywords triggers alerts:
- `credential`, `secret`, `key`, `password`
- `backup`, `config`, `db`, `sqlite`

## Reading Logs

### Decode Single Entry
```python
import base64

with open("log_files/api_audit.log", "r") as f:
    for line in f:
        decoded = base64.b64decode(line.strip()).decode('utf-8')
        print(decoded)
```

### Using Dashboard
The dashboard at `http://localhost:8002` automatically:
- Decodes and displays logs in real-time
- Categorizes by event type
- Highlights critical events
- Shows download statistics

## Log Format
Each log line contains:
```
TIMESTAMP - LEVEL - MESSAGE
```

Example decoded:
```
2024-12-20 14:30:00 - CRITICAL - {"event": "FILE_DOWNLOAD", "ip": "192.168.1.100", "filename": "database_credentials.txt"}
```

## Console Output

The honeypot also prints notable events to console:

```
============================================================
[FILE DOWNLOAD]
  File:    customer_data.db
  Type:    sqlite
  IP:      192.168.1.100
  Beacon:  abc123de...
  Time:    2024-12-20 14:30:00 UTC
============================================================
```

## Monitoring Downloads

### Via API
```bash
# All downloads
curl http://localhost:8002/api/downloads

# Sensitive only
curl http://localhost:8002/api/sensitive
```

### Response Format
```json
{
  "downloads": [
    {
      "filename": "database_credentials.txt",
      "client_ip": "192.168.1.100",
      "timestamp": "2024-12-20T14:30:00Z",
      "is_sensitive": true
    }
  ],
  "total": 1,
  "sensitive_count": 1
}
```

## Best Practices

1. **Monitor CRITICAL logs** - These indicate active attacks
2. **Track file downloads** - Attackers downloading files = high intent
3. **Check beacon activations** - Shows files were actually opened
4. **Review unique IPs** - Identify distinct attackers
5. **Watch for patterns** - Multiple admin attempts = targeted attack
