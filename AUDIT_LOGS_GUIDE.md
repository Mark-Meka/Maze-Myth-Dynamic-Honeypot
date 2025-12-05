# Encrypted Audit Logs - Security Feature

## Overview

The honeypot now writes **encoded audit logs** to prevent attackers from easily reading log files if they gain file system access. The logs are obfuscated using Base64 encoding.

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
python read_logs.py
```

**DO NOT** try to read the log file directly with:
- ❌ `type log_files\api_audit.log` - Will show gibberish
- ❌ `cat log_files/api_audit.log` - Will show gibberish
- ❌ Opening in text editor - Will show gibberish

**ONLY USE:**
- ✅ `python read_logs.py` - Properly decodes and displays logs

## Usage

### View All Logs
```bash
python read_logs.py
```

### View Last 50 Lines
```bash
python read_logs.py --tail 50
```

### Search for Specific Events
```bash
python read_logs.py | findstr "ATTACKER"
python read_logs.py | findstr "BEACON"
```

### Save Decoded Logs to File
```bash
python read_logs.py > decoded_logs.txt
```

## Log Format (After Decoding)

Once decoded, logs are in standard format:
```
2025-12-05 01:36:20 - INFO - [MAZE] GET /api/v1/users | Access: public | IP: 127.0.0.1
2025-12-05 01:36:25 - CRITICAL - [ATTACKER] {"event": "NEW_ENDPOINT_DISCOVERY", "ip": "192.168.1.100", ...}
2025-12-05 01:36:30 - CRITICAL - [BEACON_ACTIVATED] Bait file opened!
```

## Security Benefits

1. **Obfuscation** - Attackers cannot easily grep through logs
2. **Tamper Detection** - Modified logs will fail to decode
3. **Privacy** - IP addresses and sensitive data not immediately visible
4. **Defense in Depth** - Adds another layer of protection

## Important Notes

⚠️ **Keep `read_logs.py` secure!** - This is the only way to read the logs

⚠️ **Always use `read_logs.py`** - Direct file reading will show encoded gibberish

✅ **Logs are NOT encrypted** - They are Base64 encoded (obfuscated, not secure encryption)

---

**Generated:** 2025-12-05  
**Honeypot Version:** 1.0  
**Encoding Method:** Base64
