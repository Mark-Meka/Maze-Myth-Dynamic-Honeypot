"""
BankCorp Real Banking App  — port 8080
=======================================
This is the "legitimate" decoy banking application that sits behind the
OpenResty proxy.  LOW-risk visitors land here; HIGH-risk visitors are
silently redirected to the honeypot by the Lua risk engine.

Intentional vulnerability surface (for honeypot research):
----------------------------------------------------------
V1  SQL Injection      GET /api/users/search?q=
V2  Path Traversal     GET /api/files/view?path=
V3  Unauth Admin       GET /api/v2/admin  (no auth check)
V4  Command Injection  GET /api/system/ping?host=
V5  File Upload (RCE)  GET|POST /api/upload
V6  IDOR               GET /api/accounts/<id>  (no ownership check)

None of these actually execute anything dangerous — they return realistic
fake data.  The Lua risk engine in the proxy detects the exploit payloads
in the URI/body and accumulates a risk score that eventually causes a
silent redirect to the honeypot (port 8001).

Score thresholds (proxy/lua/risk_engine.lua):
  PATH_TRAVERSAL   +25    CMD_INJECTION  +40
  SQLI             +20    WEBSHELL_UPLOAD+40
  ADMIN_ENUM       +20    LOG4SHELL      +35
  REVSHELL         +45    SHELLSHOCK     +35
  SCANNER_UA       +25

Redirect fires at cumulative score >= 100 (per IP, 24-hour sticky).
"""

import os
import html
import json
import random
import logging
import io
import zipfile
from datetime import datetime
from pathlib import Path

from flask import Flask, request, jsonify, render_template, send_file, Response
from flask_cors import CORS
from dotenv import load_dotenv
from faker import Faker

# ── Environment ───────────────────────────────────────────────────────────────
root_dir = Path(__file__).parent.resolve()
env_path = root_dir / ".env"
if env_path.exists():
    load_dotenv(env_path)

# ── App setup ─────────────────────────────────────────────────────────────────
app = Flask(__name__, template_folder="templates")
app.config["JSON_SORT_KEYS"] = False
CORS(app, resources={r"/*": {"origins": "*"}})

fake = Faker()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s")
app.logger.setLevel(logging.INFO)

LOG_DIR = root_dir / "log_files"
LOG_DIR.mkdir(parents=True, exist_ok=True)
REAL_LOG_FILE = LOG_DIR / "real_app.log"
file_handler = logging.FileHandler(REAL_LOG_FILE, encoding="utf-8")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
app.logger.addHandler(file_handler)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr)


def _now():
    return datetime.utcnow().isoformat() + "Z"


def _log_vuln(tag: str, detail: str):
    """Log a vulnerability probe to the shared real_app.log."""
    ip = _client_ip()
    app.logger.warning(
        f"[REALAPP] {_now()} {ip} [VULN:{tag}] {detail}"
    )


def _generate_profile():
    return {
        "name": fake.name(),
        "email": fake.safe_email(),
        "phone": fake.phone_number(),
        "address": fake.address().replace("\n", ", "),
        "customer_id": fake.bothify("CUST-####-??"),
        "joined": fake.date_between(
            start_date="-3y", end_date="today").isoformat(),
        "status": random.choice(["active", "preferred", "gold"]),
    }


def _generate_accounts(count=4):
    accounts = []
    for _ in range(count):
        accounts.append({
            "account_id": fake.bothify("ACC-########"),
            "type": random.choice(["checking", "savings", "credit", "loan"]),
            "balance": float(
                fake.pydecimal(left_digits=5, right_digits=2, positive=True)),
            "currency": "USD",
            "opened": fake.date_between(
                start_date="-5y", end_date="today").isoformat(),
            "status": random.choice(["active", "pending", "closed"]),
        })
    return accounts


def _generate_transactions(count=10):
    txs = []
    for _ in range(count):
        txs.append({
            "transaction_id": fake.bothify("TXN-########"),
            "date": fake.date_time_between(
                start_date="-30d", end_date="now").isoformat(),
            "amount": float(
                fake.pydecimal(left_digits=4, right_digits=2, positive=True)),
            "currency": "USD",
            "description": fake.sentence(nb_words=4),
            "merchant": fake.company(),
            "status": random.choice(["completed", "pending", "failed"]),
            "direction": random.choice(["debit", "credit"]),
        })
    return txs


def _generate_payments(count=6):
    payments = []
    for _ in range(count):
        payments.append({
            "payment_id": fake.bothify("PAY-########"),
            "amount": float(
                fake.pydecimal(left_digits=4, right_digits=2, positive=True)),
            "currency": "USD",
            "payee": fake.company(),
            "scheduled": fake.date_time_between(
                start_date="now", end_date="+30d").date().isoformat(),
            "status": random.choice(["scheduled", "sent", "failed"]),
        })
    return payments


def _fake_users(count=8):
    """Generate fake internal user records for SQLi / admin bait."""
    roles = ["admin", "auditor", "support", "analyst", "readonly"]
    depts = ["Engineering", "Finance", "Compliance", "Operations", "Security"]
    users = []
    for i in range(count):
        users.append({
            "user_id":    f"USR-{random.randint(1000, 9999)}",
            "username":   fake.user_name(),
            "email":      fake.company_email(),
            "role":       random.choice(roles),
            "department": random.choice(depts),
            "last_login": fake.date_time_between(
                start_date="-7d", end_date="now").isoformat(),
            "mfa_enabled": random.choice([True, False]),
        })
    # Always include a juicy-looking admin row to bait the attacker
    users.insert(0, {
        "user_id":    "USR-0001",
        "username":   "sysadmin",
        "email":      "sysadmin@bankcorp.internal",
        "role":       "admin",
        "department": "Security",
        "last_login": _now(),
        "mfa_enabled": False,
    })
    return users


# ── Global request logger ─────────────────────────────────────────────────────

@app.before_request
def log_request():
    app.logger.info(
        f"[REALAPP] {_now()} {_client_ip()} {request.method} {request.path}"
    )


# ── Original pages ────────────────────────────────────────────────────────────

@app.route("/")
def login_page():
    return render_template("login.html")


@app.route("/dashboard")
def dashboard_page():
    profile  = _generate_profile()
    accounts = _generate_accounts(3)
    recent   = _generate_transactions(5)
    return render_template("dashboard.html",
                           profile=profile,
                           accounts=accounts,
                           recent=recent)


@app.route("/profile")
def profile_page():
    profile = _generate_profile()
    return render_template("profile.html", profile=profile)


@app.route("/files")
def files_page():
    files = [
        {"name": "statement_2025_09.pdf", "size": "187 KB", "type": "statement"},
        {"name": "tax_summary_2024.xlsx", "size": "92 KB",  "type": "report"},
        {"name": "loan_agreement.pdf",    "size": "204 KB", "type": "document"},
    ]
    return jsonify({"files": files, "count": len(files)})


@app.route("/admin")
def admin_page():
    return render_template("admin.html")


@app.route("/config")
def config_page():
    config_lines = [
        "DATABASE_URL=postgresql://bankadmin:Password123@db.bankcorp.local:5432/bankdb",
        "ADMIN_EMAIL=security@bankcorp.local",
        "SECRET_KEY=ChangeMeNow123!",
        "DEBUG=false",
        "LOG_LEVEL=INFO",
    ]
    return render_template("config.html", config_lines=config_lines)


@app.route("/backup")
def backup_page():
    return render_template("backup.html")


@app.route("/download/backup.zip")
def download_backup():
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("credentials.txt",
                    "admin:Admin1234\nsupport:SupportM0re!\n")
        zf.writestr("notes.txt",
                    "Database dump and audit logs are stored separately.\n"
                    "Do not expose this file.\n")
    data.seek(0)
    return send_file(data, download_name="backup.zip",
                     as_attachment=True, mimetype="application/zip")


@app.route("/shell.php")
def shell_page():
    return ("<html><body><h1>PHP Shell</h1>"
            "<p>PHP shell placeholder. Upload or execute commands here.</p>"
            "</body></html>"), 200, {"Content-Type": "text/html"}


@app.route("/upload.php", methods=["GET", "POST"])
def upload_page():
    if request.method == "POST":
        return jsonify({
            "status": "error",
            "message": "Upload denied: insufficient permissions.",
        }), 403
    return ("<html><body><h1>Upload</h1>"
            "<p>File upload interface is not available.</p>"
            "</body></html>"), 200, {"Content-Type": "text/html"}


@app.route("/secret.txt")
def secret_page():
    return ("DB_PASSWORD=BankCorp2026!\nAPI_TOKEN=abcdef123456\n",
            200, {"Content-Type": "text/plain"})


# ── Original API ──────────────────────────────────────────────────────────────

@app.route("/api/admin/users")
def api_admin_users():
    return jsonify({
        "users": [
            {"username": "admin",   "role": "administrator"},
            {"username": "auditor", "role": "readonly"},
        ]
    })


@app.route("/api/admin/credentials")
def api_admin_credentials():
    return jsonify({
        "status": "error",
        "message": "Access denied. Administrator credentials are protected.",
    }), 403


@app.route("/api/backup")
def api_backup():
    return jsonify({
        "backup_files": [
            {"name": "db_dump.sql",    "date": "2026-06-10", "size": "12MB"},
            {"name": "audit_log.zip",  "date": "2026-06-11", "size": "3MB"},
        ]
    })


@app.route("/api")
def api_root():
    return jsonify({
        "service":  "BankCorp Real Banking API",
        "version":  "1.0",
        "endpoints": {
            "user":         "/api/user",
            "profile":      "/api/user/profile",
            "accounts":     "/api/accounts",
            "transactions": "/api/transactions",
            "payments":     "/api/payments",
            "login":        "/api/auth/login",
            "logout":       "/api/auth/logout",
            # ── Vulnerable surface (discoverable by enumeration) ──────────
            "user_search":  "/api/users/search?q=<query>",
            "file_view":    "/api/files/view?path=<filename>",
            "admin_v2":     "/api/v2/admin",
            "system_ping":  "/api/system/ping?host=<host>",
            "upload":       "/api/upload",
        },
    })


@app.route("/api/user")
def api_user():
    profile = _generate_profile()
    return jsonify({
        "user": {
            "customer_id": profile["customer_id"],
            "name":        profile["name"],
            "email":       profile["email"],
            "status":      profile["status"],
        }
    })


@app.route("/api/user/profile")
def api_user_profile():
    profile = _generate_profile()
    return jsonify({"user_profile": profile})


@app.route("/api/accounts")
def api_accounts():
    accounts = _generate_accounts(5)
    return jsonify({"accounts": accounts, "total": len(accounts)})


@app.route("/api/transactions")
def api_transactions():
    return jsonify({
        "transactions": _generate_transactions(10), "total": 10
    })


@app.route("/api/payments")
def api_payments():
    return jsonify({"payments": _generate_payments(6), "total": 6})


@app.route("/api/auth/login", methods=["POST"])
def api_login():
    credentials = request.get_json(silent=True)
    if not credentials:
        credentials = request.form.to_dict() or {}
    username = credentials.get("username", "")
    password = credentials.get("password", "")
    if username == "admin" and password == "admin":
        return jsonify({
            "status":  "success",
            "message": "Authentication successful",
            "token":   fake.uuid4(),
        })
    return jsonify({
        "status":  "error",
        "message": "Invalid username or password",
    }), 401


@app.route("/api/auth/logout", methods=["POST"])
def api_logout():
    return jsonify({"status": "success", "message": "Logged out"})


# ═════════════════════════════════════════════════════════════════════════════
# INTENTIONAL VULNERABILITY SURFACE
# Each endpoint is deliberately exploitable in a way that the Lua risk engine
# detects and scores, eventually redirecting the attacker to the honeypot.
# ═════════════════════════════════════════════════════════════════════════════


# ── V1: SQL Injection — GET /api/users/search?q= ─────────────────────────────
# Attacker sends:  ?q=' OR 1=1--
# Lua rule:  SQLI  → +20 per request
# After ~4 requests with SQLi payload the score reaches 80; one more
# admin/path probe tips it over 100.

@app.route("/api/users/search")
def api_users_search():
    """
    [VULN-V1] Simulated SQL Injection endpoint.
    The query parameter is 'reflected' into the response so the attacker
    believes they can control the query.  The Lua engine detects SQL
    keywords (select, union, --, etc.) in the URI and adds +20 per hit.
    Browser requests → HTML page; automated tools → JSON.
    """
    q = request.args.get("q", "").strip()

    # Detect and log the probe
    sql_keywords = ["select", "union", "insert", "update", "delete",
                    "drop", "--", "/*", "1=1", "or 1", "sleep("]
    is_sqli = any(kw in q.lower() for kw in sql_keywords)
    if is_sqli:
        _log_vuln("SQLI",
                  f"Possible SQL injection in /api/users/search?q={q!r}")

    users = _fake_users(count=random.randint(3, 8))
    show_hash = False

    if is_sqli:
        show_hash = True
        users.append({
            "user_id":       "USR-0000",
            "username":      "db_service",
            "email":         "db@bankcorp.internal",
            "role":          "DBA",
            "department":    "Infrastructure",
            "last_login":    _now(),
            "mfa_enabled":   False,
            "password_hash": "$2b$12$Kx3nJfRtLmPqW8sYvU6OBuN7dCeQhR5xTgVwYoA4bZXlMjKpIDs1e",
        })

    debug_block = {
        "sql":  f"SELECT * FROM users WHERE username LIKE '%{q}%' OR email LIKE '%{q}%'",
        "note": "Debug mode active — raw query exposed",
    }

    # Browser request → render HTML
    accept = request.headers.get("Accept", "")
    if "text/html" in accept:
        return render_template(
            "vuln_search.html",
            q=q,
            results=users if q else [],
            show_hash=show_hash,
            debug=debug_block if q else None,
        )

    # Tool / curl request → JSON
    return jsonify({
        "query":   q,
        "results": users,
        "total":   len(users),
        "debug":   debug_block,
        "_links":  {
            "admin":  "/api/v2/admin",
            "export": f"/api/users/export?filter={q}",
        },
    })


# ── V2: Path Traversal — GET /api/files/view?path= ───────────────────────────
# Attacker sends:  ?path=../../../etc/passwd
# Lua rule:  PATH_TRAVERSAL → +25 per request
# Two hits = 50 pts; combine with ADMIN_ENUM (+20) and CMD_INJECTION (+40)
# to cross 100.

@app.route("/api/files/view")
def api_files_view():
    """
    [VULN-V2] Simulated Path Traversal endpoint.
    The `path` parameter is reflected in the response.  When traversal
    sequences are detected, the response returns realistic fake file
    content (passwd-style, shadow-style, config-style) so the attacker
    thinks the vulnerability is real.
    Lua rule PATH_TRAVERSAL fires at +25 per hit.
    Browser requests → HTML file-browser page; automated tools → JSON.
    """
    path = request.args.get("path", "").strip()

    is_traversal = "../" in path or "%2e%2e" in path.lower()
    if is_traversal:
        _log_vuln("PATH_TRAVERSAL",
                  f"Path traversal attempt in /api/files/view?path={path!r}")

    # Decide what fake content to return based on the requested path
    path_lower = path.lower()
    content, mime = "", "text/plain"

    if "passwd" in path_lower:
        content = (
            "root:x:0:0:root:/root:/bin/bash\n"
            "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
            "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
            "bankapp:x:1001:1001:BankCorp App:/home/bankapp:/bin/bash\n"
            "postgres:x:117:125:PostgreSQL administrator:/var/lib/postgresql:/bin/bash\n"
            "sysadmin:x:1002:1002:System Administrator:/home/sysadmin:/bin/bash\n"
        )
    elif "shadow" in path_lower:
        content = (
            "root:$6$rounds=5000$usesomesillystri$D4DVEtPr.otFpuHHDjMGtD4Dvr7fEWyVf2s"
            "EMsTxT.dKKO7kJ3hHa1FRHWNl4w.Y8LB.M9i5bxXJVYhA.zAEi/:18895:0:99999:7:::\n"
            "bankapp:$6$salt$encryptedhashhere:19000:0:99999:7:::\n"
            "sysadmin:$6$another$hash2:19100:0:99999:7:::\n"
        )
    elif ".env" in path_lower or "config" in path_lower:
        content = (
            "# BankCorp Application Config\n"
            "DB_HOST=db-primary-1.internal\n"
            "DB_PORT=5432\n"
            "DB_NAME=bankcorp_prod\n"
            "DB_USER=bankcorp_app\n"
            "DB_PASS=Bc0rp!Pr0d#2024\n"
            "SECRET_KEY=s3cur3-jwt-k3y-d0-n0t-sh4re\n"
            "REDIS_URL=redis://cache-01.internal:6379/0\n"
            "GEMINI_API_KEY=AIzaSy-FAKE-KEY-for-demo-purposes\n"
            "SENTRY_DSN=https://fake@sentry.io/123456\n"
        )
    elif "id_rsa" in path_lower or "ssh" in path_lower:
        content = (
            "-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW\n"
            "QyNTUxOQAAACBFAKEKEYHEREFAKEKEYHEREFAKEKEYHEREFAKEKEYHERE\n"
            "FAKEKEYHEREXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX\n"
            "-----END OPENSSH PRIVATE KEY-----\n"
        )
    elif "hosts" in path_lower:
        content = (
            "127.0.0.1       localhost\n"
            "10.0.0.2        bankcorp-web-01 bankcorp-web-01.internal\n"
            "10.0.0.3        bankcorp-api-01 bankcorp-api-01.internal\n"
            "10.0.1.10       db-primary-1    db-primary-1.internal\n"
            "10.0.1.11       db-replica-1    db-replica-1.internal\n"
            "10.0.1.20       cache-01        cache-01.internal\n"
            "10.0.1.30       vault-01        vault-01.internal\n"
        )
        mime = "text/plain"
    else:
        # Generic file listing / fake document
        content = (
            f"BankCorp Internal Document\n"
            f"Path: {path}\n"
            f"Generated: {_now()}\n"
            f"Size: {random.randint(1, 200)} KB\n\n"
            f"[Document content not available for preview]\n"
        )
        mime = "text/plain"

    return jsonify({
        "path":    path,
        "content": content,
        "size":    len(content),
        "mime":    mime,
        "_links":  {
            "admin":   "/api/v2/admin",
            "secrets": "/api/files/view?path=../../.env",
        },
    })


# ── V3: Unauthenticated Admin Panel — GET /api/v2/admin ──────────────────────
# No auth check.  Lua rule: ADMIN_ENUM → +20 per hit.
# Hitting this + SQLi probes easily reaches 100.

@app.route("/api/v2/admin")
def api_v2_admin():
    """
    [VULN-V3] Unauthenticated admin panel.
    No authorization check.  Returns fake admin user list and internal
    links designed to bait further enumeration.
    Lua ADMIN_ENUM rule fires at +20.
    """
    ip = _client_ip()
    _log_vuln("UNAUTH_ADMIN", f"Unauthenticated access to /api/v2/admin from {ip}")

    users = _fake_users(count=6)
    return jsonify({
        "admin_panel": "BankCorp Internal Administration",
        "version":     "v2.4.1",
        "build":       "2026-01-15-RELEASE",
        "users":       users,
        "total_users": len(users),
        "system": {
            "db_host":  "db-primary-1.internal",
            "db_port":  5432,
            "db_name":  "bankcorp_prod",
            "uptime":   f"{random.randint(10, 200)} days",
            "env":      "production",
        },
        "_links": {
            "users":        "/api/v2/admin/users",
            "secrets":      "/api/v2/admin/secrets",
            "config":       "/api/v2/admin/config",
            "audit":        "/api/v2/admin/audit",
            "backup":       "/api/v2/admin/backup",
            "upload":       "/api/upload",
            "file_browser": "/api/files/view?path=.",
        },
        "warning": "This endpoint should be protected — report to security@bankcorp.internal",
    })


@app.route("/api/v2/admin/users")
def api_v2_admin_users():
    """Extended admin user list with password hashes."""
    _log_vuln("ADMIN_USERS", f"Admin user list accessed from {_client_ip()}")
    users = _fake_users(count=10)
    # Add fake password hashes to make it look like a real DB dump
    for u in users:
        u["password_hash"] = f"$2b$12${fake.md5()[:22]}{fake.md5()[:31]}"
        u["api_key"] = fake.uuid4()
    return jsonify({"users": users, "total": len(users)})


@app.route("/api/v2/admin/secrets")
def api_v2_admin_secrets():
    """Fake secrets vault."""
    _log_vuln("ADMIN_SECRETS", f"Admin secrets accessed from {_client_ip()}")
    return jsonify({
        "secrets": [
            {"key": "DB_MASTER_PASSWORD",  "value": "Pr0d!Master#2024",  "env": "production"},
            {"key": "JWT_SECRET",           "value": "jwt-s3cr3t-k3y-xyz", "env": "production"},
            {"key": "STRIPE_SECRET_KEY",    "value": "sk_live_FAKEKEYHERE", "env": "production"},
            {"key": "AWS_SECRET_ACCESS_KEY","value": "wJalrXUtnFEMI/K7MDENGbPxRfiCYEXAMPLEKEY", "env": "production"},
            {"key": "GEMINI_API_KEY",       "value": "AIzaSy-FAKE-DEMO-KEY", "env": "production"},
        ],
        "total":   5,
        "warning": "Audit logged",
    })


@app.route("/api/v2/admin/config")
def api_v2_admin_config():
    """Fake internal config."""
    _log_vuln("ADMIN_CONFIG", f"Admin config accessed from {_client_ip()}")
    return jsonify({
        "database": {
            "primary":  "db-primary-1.internal:5432",
            "replica":  "db-replica-1.internal:5432",
            "name":     "bankcorp_prod",
            "ssl_mode": "verify-full",
        },
        "cache":  {"host": "cache-01.internal:6379", "ttl": 3600},
        "vault":  {"host": "vault-01.internal:8200", "auth": "approle"},
        "s3":     {"bucket": "bankcorp-backups-prod", "region": "us-east-1"},
    })


# ── V4: Command Injection — GET /api/system/ping?host= ───────────────────────
# Attacker sends:  ?host=127.0.0.1;id  or  ?host=127.0.0.1|cat /etc/passwd
# Lua rule:  CMD_INJECTION (`;`, `|`, `` ` ``, `&&`) → +40 per request.
# A single hit + ADMIN_ENUM + any SQLi probe = 20+20+40 = 80; one more
# path traversal = 105 → redirect.

@app.route("/api/system/ping")
def api_system_ping():
    """
    [VULN-V4] Simulated Command Injection endpoint.
    The `host` parameter is echoed into a fake ping response.  Injection
    characters (;, |, &&, backtick) trigger CMD_INJECTION +40 in the Lua
    engine.  The response includes fake shell output so the attacker
    believes the injection succeeded.
    """
    host = request.args.get("host", "127.0.0.1").strip()
    ip   = _client_ip()

    injection_chars = [";", "|", "&&", "`", "$(",
                       "||", ">>", ">", "bash", "sh ", "cmd"]
    is_injection = any(c in host for c in injection_chars)

    if is_injection:
        _log_vuln("CMD_INJECTION",
                  f"Command injection attempt in /api/system/ping?host={host!r}")
        # Simulate that the injection "worked" — return fake command output
        injected_cmd = host.split(";")[-1].strip() if ";" in host \
                  else host.split("|")[-1].strip() if "|" in host \
                  else host.split("&&")[-1].strip() if "&&" in host \
                  else "id"
        fake_output = _fake_cmd_output(injected_cmd.strip())
        return jsonify({
            "host":   host.split(";")[0].split("|")[0].split("&&")[0].strip(),
            "status": "success",
            "output": (
                f"PING 127.0.0.1 (127.0.0.1) 56(84) bytes of data.\n"
                f"64 bytes from 127.0.0.1: icmp_seq=1 ttl=64 time=0.041 ms\n\n"
                f"--- command injection output ---\n"
                f"{fake_output}"
            ),
            "_hint":  "Internal diagnostic tool — not for external use",
            "_links": {
                "file_browser": "/api/files/view?path=/var/www/html",
                "admin":        "/api/v2/admin",
            },
        })

    # Normal ping response
    latency = round(random.uniform(0.1, 4.5), 3)
    return jsonify({
        "host":    host,
        "status":  "success",
        "latency_ms": latency,
        "output":  (
            f"PING {host} ({host}) 56(84) bytes of data.\n"
            f"64 bytes from {host}: icmp_seq=1 ttl=64 time={latency} ms\n"
            f"64 bytes from {host}: icmp_seq=2 ttl=64 time={latency + 0.01} ms\n"
            f"\n--- {host} ping statistics ---\n"
            f"2 packets transmitted, 2 received, 0% packet loss\n"
        ),
    })


def _fake_cmd_output(cmd: str) -> str:
    """Return plausible-looking shell output for a given command."""
    cmd_lower = cmd.lower().strip()
    if cmd_lower in ("id", "whoami"):
        return "uid=33(www-data) gid=33(www-data) groups=33(www-data)"
    if cmd_lower.startswith("ls"):
        return (
            "total 64\n"
            "drwxr-xr-x  5 www-data www-data  4096 Jun 16 08:00 .\n"
            "drwxr-xr-x 12 root     root      4096 Jun 10 12:00 ..\n"
            "-rw-r--r--  1 www-data www-data  9312 Jun 16 07:55 app.py\n"
            "-rw-r--r--  1 www-data www-data   312 Jun  1 09:00 .env\n"
            "drwxr-xr-x  2 www-data www-data  4096 Jun 10 10:00 templates\n"
            "drwxr-xr-x  2 www-data www-data  4096 Jun 10 10:00 log_files\n"
            "-rw-r--r--  1 www-data www-data   512 Jun 10 10:00 requirements.txt\n"
        )
    if "uname" in cmd_lower:
        return "Linux bankcorp-web-01 5.15.0-89-generic #99-Ubuntu SMP x86_64 GNU/Linux"
    if "hostname" in cmd_lower:
        return "bankcorp-web-01.internal"
    if "ifconfig" in cmd_lower or "ip a" in cmd_lower:
        return (
            "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
            "        inet 10.0.0.2  netmask 255.255.255.0  broadcast 10.0.0.255\n"
            "        ether 02:42:0a:00:00:02  txqueuelen 0  (Ethernet)\n"
        )
    if "cat" in cmd_lower and ".env" in cmd_lower:
        return (
            "DB_HOST=db-primary-1.internal\n"
            "DB_PASS=Bc0rp!Pr0d#2024\n"
            "SECRET_KEY=s3cur3-jwt-k3y\n"
        )
    if "ps" in cmd_lower:
        return (
            "  PID TTY          TIME CMD\n"
            "    1 ?        00:00:01 python3\n"
            "   42 ?        00:00:00 gunicorn\n"
            "  100 ?        00:00:00 ps aux\n"
        )
    # Generic fallback
    return f"sh: 1: {cmd}: executed\n"


# ── V5: Unrestricted File Upload — GET|POST /api/upload ──────────────────────
# Attacker POSTs a shell.php / webshell.jsp
# Lua rule: WEBSHELL_UPLOAD (POST to *.php/*.jsp/*.sh) → +40
# Combined with any one other probe = 60+; two probes → 100.

@app.route("/api/upload", methods=["GET", "POST"])
def api_upload():
    """
    [VULN-V5] Simulated unrestricted file upload.
    GET  → returns a convincing upload portal HTML page.
    POST → accepts any file, returns a fake success with an /uploads/ URL.
    The Lua engine detects POST to paths containing script extensions
    uploaded by the attacker (WEBSHELL_UPLOAD +40).
    Nothing is ever written to disk.
    """
    if request.method == "GET":
        return render_template("upload_portal.html")

    # POST handler
    ip          = _client_ip()
    ufile       = request.files.get("file")
    filename    = ufile.filename if ufile and ufile.filename else "unknown.bin"
    safe_name   = filename.replace("/", "_").replace("\\", "_")
    extension   = Path(safe_name).suffix.lower()
    ticket_id   = request.form.get("ticket_id", fake.bothify("TKT-#######"))

    danger_exts = {".php", ".jsp", ".asp", ".aspx", ".sh", ".py", ".rb", ".phtml"}
    is_dangerous = extension in danger_exts

    if is_dangerous:
        _log_vuln("WEBSHELL_UPLOAD",
                  f"Dangerous file upload: {safe_name} from {ip}")

    # Read first 512 bytes — NEVER written to disk
    raw_bytes  = b""
    raw_sample = ""
    if ufile:
        raw_bytes  = ufile.read(512)
        raw_sample = raw_bytes[:80].decode("utf-8", errors="replace").strip()

    fake_file_id = fake.bothify("UPL-########")
    pub_url      = f"/uploads/{safe_name}"

    return jsonify({
        "status":    "success",
        "file_id":   fake_file_id,
        "filename":  safe_name,
        "ticket_id": ticket_id,
        "url":       pub_url,
        "size":      len(raw_bytes),
        "message":   "File received successfully. Processing queued.",
        "_links": {
            "view":   pub_url,
            "delete": f"/api/upload/{fake_file_id}",
            "admin":  "/api/v2/admin",
        },
    })


# ── V6: IDOR — GET /api/accounts/<account_id> ────────────────────────────────
# No ownership check — any account_id returns data.
# Not a Lua-scoring route by itself, but the response embeds links to
# /api/v2/admin (ADMIN_ENUM +20) and /api/users/search which baits SQLi.

@app.route("/api/accounts/<account_id>")
def api_account_detail(account_id):
    """
    [VULN-V6] Insecure Direct Object Reference (IDOR).
    No auth check — any account_id returns account data.
    The response contains breadcrumbs to the admin panel and user search,
    baiting the attacker into scoring-triggering probes.
    """
    ip = _client_ip()
    _log_vuln("IDOR",
              f"Unauthenticated account access: /api/accounts/{account_id} from {ip}")

    owner = _generate_profile()
    account = {
        "account_id":  account_id,
        "owner_name":  owner["name"],
        "owner_email": owner["email"],
        "owner_id":    owner["customer_id"],
        "type":        random.choice(["checking", "savings", "credit", "loan"]),
        "balance":     float(
            fake.pydecimal(left_digits=6, right_digits=2, positive=True)),
        "available":   float(
            fake.pydecimal(left_digits=5, right_digits=2, positive=True)),
        "currency":    "USD",
        "iban":        fake.iban(),
        "swift":       fake.bothify("BANK??##"),
        "opened":      fake.date_between(
            start_date="-5y", end_date="today").isoformat(),
        "status":      "active",
        "statements":  f"/api/accounts/{account_id}/statements",
        "transactions": f"/api/accounts/{account_id}/transactions",
    }
    return jsonify({
        "account": account,
        "_note":   "IDOR: No ownership verification performed",
        "_links":  {
            "all_accounts":  "/api/accounts",
            "user_search":   "/api/users/search?q=" + owner["customer_id"],
            "admin":         "/api/v2/admin",
            "file_browser":  "/api/files/view?path=.",
        },
    })


@app.route("/api/accounts/<account_id>/transactions")
def api_account_transactions(account_id):
    """IDOR sub-resource: transactions for any account, no auth."""
    _log_vuln("IDOR_TXN",
              f"Unauthenticated transaction access: /api/accounts/{account_id}/transactions")
    txs = _generate_transactions(random.randint(8, 25))
    return jsonify({
        "account_id":   account_id,
        "transactions": txs,
        "total":        len(txs),
        "export":       f"/api/accounts/{account_id}/transactions/export",
    })


@app.route("/api/accounts/<account_id>/statements")
def api_account_statements(account_id):
    """IDOR sub-resource: statements for any account, no auth."""
    _log_vuln("IDOR_STMT",
              f"Unauthenticated statement access: /api/accounts/{account_id}/statements")
    stmts = []
    for i in range(random.randint(4, 12)):
        year  = 2025 - (i // 12)
        month = 12 - (i % 12)
        period = f"{year}-{month:02d}"
        stmts.append({
            "period": period,
            "file":   f"/api/files/view?path=statements/{account_id}_{period}.pdf",
        })
    return jsonify({"account_id": account_id, "statements": stmts})


# ── Fake uploaded shell placeholder ──────────────────────────────────────────
# When an attacker GETs /uploads/<filename> after uploading via V5,
# the proxy should already have their score >= 100 and they will be
# silently redirected to the honeypot.  This route is a safety net for
# the case where the real-app serves them before the score flips.

@app.route("/uploads/<path:filename>")
def fake_uploaded_file(filename):
    """
    Placeholder for uploaded files.  If the proxy hasn't redirected yet,
    return a plausible-looking 403.  Normally the attacker will never
    see this — they'll be on the honeypot already.
    """
    _log_vuln("UPLOAD_ACCESS",
              f"Access to uploaded file /uploads/{filename} from {_client_ip()}")
    return (
        "<html><head><title>403 Forbidden</title></head><body>"
        "<h1>Forbidden</h1>"
        "<p>You don't have permission to access this resource.</p>"
        "<hr><address>Apache/2.4.54 (Debian) Server at bankcorp-web-01 Port 80</address>"
        "</body></html>"
    ), 403, {"Content-Type": "text/html",
              "Server": "Apache/2.4.54 (Debian)",
              "X-Powered-By": "PHP/7.4.33"}


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("  BankCorp Real-App  :8080  (with intentional vuln surface)")
    print("=" * 60)
    print("  V1 SQLi          GET /api/users/search?q=")
    print("  V2 Path Traversal GET /api/files/view?path=")
    print("  V3 Unauth Admin  GET /api/v2/admin")
    print("  V4 CMDi          GET /api/system/ping?host=")
    print("  V5 File Upload   GET|POST /api/upload")
    print("  V6 IDOR          GET /api/accounts/<id>")
    print("=" * 60 + "\n")
    app.run(host="0.0.0.0", port=8080)
