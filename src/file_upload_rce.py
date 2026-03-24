"""
CVE-2020-36179 — File Upload RCE Deception Module
====================================================
Simulates a vulnerable internal bank document upload endpoint.

CVE:     CVE-2020-36179 (Jackson / Spring multipart file upload RCE)
Type:    Honeypot trap — NO real files are ever written to disk.
Goal:    Detect attackers uploading real webshell payloads, track them,
         and engage them with realistic AI-generated shell output.

Key behaviours
--------------
- Only files that contain REAL webshell/reverse-shell code are registered.
- The /uploads/<filename>?cmd=<cmd> trap only works for filenames that
  were actually uploaded WITH payload code — no random guessing.
- AI-generated shell responses are created once at startup via Gemini and
  cached for the whole session (consistent output, only varies on restart).
- Every response carries fake Spring or PHP server headers.

Routes registered:
  GET  /api/v2/documents/compliance-upload     — Spring upload form
  POST /api/v2/documents/compliance-upload     — Spring upload handler
  GET  /clientportal/support/attachments.php   — PHP upload form
  POST /clientportal/support/attachments.php   — PHP upload handler
  GET  /uploads/<filename>                     — Webshell execution trap
  GET  /api/dashboard/cve/file-upload          — Dashboard data feed

Usage in honeypot.py:
  from src.file_upload_rce import register_file_upload_routes
  register_file_upload_routes(app)
"""

import logging
import random
import re
import time
from datetime import datetime, timezone

from flask import request, jsonify, make_response
from src import attacker_intel as _intel

# ------------------------------------------------------------------
# Module-level state
# ------------------------------------------------------------------
upload_events: list[dict] = []          # every upload and webshell hit

# Registry of uploaded filenames that contained real webshell code.
# Key: filename string, Value: upload event dict
# Only filenames in this dict can trigger the webshell execution trap.
_shell_registry: dict[str, dict] = {}


# ------------------------------------------------------------------
# Deception headers
# ------------------------------------------------------------------
SPRING_HEADERS = {
    "Server":       "Apache-Coyote/1.1",
    "X-Powered-By": "Spring Framework 5.3.9",
}
PHP_HEADERS = {
    "Server":       "Apache/2.4.54 (Debian)",
    "X-Powered-By": "PHP/7.4.33",
}

# ------------------------------------------------------------------
# PHP webshell payload patterns — file content must match at least one
# ------------------------------------------------------------------
_WEBSHELL_PATTERNS = [
    re.compile(rb"<\?php", re.IGNORECASE),
    re.compile(rb"system\s*\(", re.IGNORECASE),
    re.compile(rb"exec\s*\(", re.IGNORECASE),
    re.compile(rb"shell_exec\s*\(", re.IGNORECASE),
    re.compile(rb"passthru\s*\(", re.IGNORECASE),
    re.compile(rb"popen\s*\(", re.IGNORECASE),
    re.compile(rb"proc_open\s*\(", re.IGNORECASE),
    re.compile(rb"eval\s*\(", re.IGNORECASE),
    re.compile(rb"base64_decode\s*\(", re.IGNORECASE),
    re.compile(rb"\$_GET\s*\[", re.IGNORECASE),
    re.compile(rb"\$_POST\s*\[", re.IGNORECASE),
    re.compile(rb"\$_REQUEST\s*\[", re.IGNORECASE),
    re.compile(rb"cmd\s*=", re.IGNORECASE),
]



# ------------------------------------------------------------------
# Lazy references (resolved at registration time)
# ------------------------------------------------------------------
_state  = None
_logger = None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ------------------------------------------------------------------
# Header helpers
# ------------------------------------------------------------------

def _add_spring_headers(response):
    for k, v in SPRING_HEADERS.items():
        response.headers[k] = v
    return response


def _add_php_headers(response):
    for k, v in PHP_HEADERS.items():
        response.headers[k] = v
    return response


# ------------------------------------------------------------------
# Logging helpers
# ------------------------------------------------------------------

def _log_event(severity: str, event_tag: str, message: str, client_ip: str):
    if severity == "CRITICAL":
        _logger.critical(f"[{event_tag}] {message}")
    elif severity == "MEDIUM":
        _logger.warning(f"[{event_tag}] {message}")
    else:
        _logger.info(f"[{event_tag}] {message}")

    level_map = {"CRITICAL": "CRITICAL", "MEDIUM": "WARNING", "INFO": "INFO"}
    _state.log_entry(
        level=level_map.get(severity, "INFO"),
        message=f"[{event_tag}] {message}",
        event=event_tag,
        client_ip=client_ip,
    )


def send_alert(client_ip: str, event_tag: str, details: str):
    _log_event("CRITICAL", event_tag, details, client_ip)


# ------------------------------------------------------------------
# Payload detection
# ------------------------------------------------------------------

def _contains_webshell_code(raw_bytes: bytes) -> bool:
    """Return True if the file bytes contain recognisable webshell patterns."""
    for pattern in _WEBSHELL_PATTERNS:
        if pattern.search(raw_bytes):
            return True
    return False


# ------------------------------------------------------------------
# AI shell-response generation — fully delegated to RAG loader
# ------------------------------------------------------------------


def _get_shell_output(cmd: str) -> tuple[str, bool]:
    """
    Resolve a shell command via the hybrid RAG pipeline:
      1. Exact cache match (Cowrie ground-truth)
      2. Case-insensitive match
      3. Dynamic handler (echo, cd, cat <path>, grep, revshell)
      4. TF-IDF fuzzy match on Cowrie command corpus
      5. Gemini LLM (if configured, cached in-memory per session)
      6. Bash error fallback

    Returns (output_text, found).
    found=False only when the absolute bash-error fallback fires.
    """
    from src.rag import shell_rag_loader as _rag
    output = _rag.resolve_shell_command(cmd)
    found  = not output.startswith("bash: ") or output == ""
    return output, found


# ------------------------------------------------------------------
# Spring upload form — GET /api/v2/documents/compliance-upload
# ------------------------------------------------------------------

_SPRING_FORM_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>BankCorp Compliance Portal — Document Submission</title>
  <style>
    body { font-family: 'Segoe UI', Arial, sans-serif; background: #f0f2f5; margin: 0; }
    .topbar {
      background: #0a2540; color: #fff; padding: 13px 32px;
      display: flex; align-items: center; gap: 14px;
    }
    .topbar .logo { font-size: 18px; font-weight: 700; letter-spacing: .5px; }
    .topbar .sub  { font-size: 11px; opacity: .65; margin-top: 2px; }
    .topbar .badge {
      background: #d62828; color: #fff; border-radius: 3px;
      padding: 2px 8px; font-size: 10px; margin-left: auto;
    }
    .wrap { max-width: 600px; margin: 48px auto; }
    .card {
      background: #fff; border-radius: 8px;
      box-shadow: 0 2px 14px rgba(0,0,0,.09); overflow: hidden;
    }
    .card-hdr {
      background: #0a2540; color: #fff; padding: 20px 28px 15px;
    }
    .card-hdr h1 { margin: 0; font-size: 18px; font-weight: 600; }
    .card-hdr p  { margin: 5px 0 0; font-size: 12px; opacity: .75; }
    .card-body { padding: 28px; }
    .notice {
      background: #e8f0fe; border-left: 4px solid #0a2540;
      padding: 11px 15px; font-size: 12px; border-radius: 0 4px 4px 0;
      margin-bottom: 22px; color: #333;
    }
    label { display: block; font-size: 12px; font-weight: 600;
            color: #555; margin-bottom: 5px; }
    input[type="file"] {
      width: 100%; border: 1px dashed #b0bec5; border-radius: 5px;
      padding: 18px; background: #fafcff; font-size: 13px;
      cursor: pointer; box-sizing: border-box;
    }
    .fmt { font-size: 11px; color: #999; margin-top: 6px; }
    .btn {
      margin-top: 20px; width: 100%; background: #0a2540; color: #fff;
      border: none; border-radius: 5px; padding: 12px;
      font-size: 14px; font-weight: 600; cursor: pointer;
    }
    .btn:hover { background: #0d3060; }
    .card-ftr {
      background: #f0f2f5; border-top: 1px solid #e0e4ea;
      padding: 12px 28px; font-size: 10px; color: #aaa;
      display: flex; justify-content: space-between;
    }
  </style>
</head>
<body>
  <div class="topbar">
    <div>
      <div class="logo">&#127968; BankCorp Financial Group</div>
      <div class="sub">Compliance &amp; Risk Management Portal &mdash; Internal</div>
    </div>
    <div class="badge">RESTRICTED</div>
  </div>
  <div class="wrap">
    <div class="card">
      <div class="card-hdr">
        <h1>&#128196; Compliance Document Submission</h1>
        <p>Upload regulatory filings, audit reports, and policy documents for review.</p>
      </div>
      <div class="card-body">
        <div class="notice">
          &#128274;&nbsp; Access is restricted to Compliance and Risk Management personnel.
          All uploads are version-controlled and subject to ISO 27001 audit logging.
        </div>
        <form method="POST" action="/api/v2/documents/compliance-upload"
              enctype="multipart/form-data">
          <label for="doc">Select Compliance Document</label>
          <input type="file" id="doc" name="file" required>
          <div class="fmt">Accepted formats: PDF, DOCX, XLSX &mdash; Max 50 MB</div>
          <button type="submit" class="btn">&#128228; Submit for Review</button>
        </form>
      </div>
      <div class="card-ftr">
        <span>BankCorp Compliance Portal v3.1.2 &mdash; Spring Framework 5.3.9</span>
        <span>Build: 2024.03.15-RELEASE</span>
      </div>
    </div>
  </div>
</body>
</html>
"""


def _route_spring_upload_get():
    client_ip = request.remote_addr
    _log_event("INFO", "CVE_UPLOAD_FORM",
               f"Spring compliance upload form accessed from {client_ip}", client_ip)
    _intel.record_form_view(client_ip, "/api/v2/documents/compliance-upload")
    resp = make_response(_SPRING_FORM_HTML, 200)
    resp.content_type = "text/html; charset=utf-8"
    return _add_spring_headers(resp)


# ------------------------------------------------------------------
# Shared upload handler (used by both Spring and PHP endpoints)
# ------------------------------------------------------------------

def _handle_upload(client_ip: str, user_agent: str, source_label: str,
                   success_url_template: str, header_fn):
    """
    Core upload logic shared by both Spring and PHP routes.
    - Reads ≤ 512 bytes, NEVER writes to disk.
    - If file contains webshell code → registers filename in _shell_registry.
    """
    uploaded_file = request.files.get("file")
    if not uploaded_file or not uploaded_file.filename:
        resp = make_response(
            jsonify({"status": "error", "code": 400, "message": "No file provided."}), 400
        )
        return header_fn(resp)

    filename  = uploaded_file.filename
    safe_name = filename.replace("/", "_").replace("\\", "_")
    extension = ("." + filename.rsplit(".", 1)[-1].lower()) if "." in filename else ""

    # Read first 512 bytes — NOTHING written to disk
    raw_bytes  = uploaded_file.read(512)
    raw_sample = raw_bytes[:100].decode("utf-8", errors="replace").strip()

    has_payload  = _contains_webshell_code(raw_bytes)
    is_dangerous = extension in _DANGEROUS_EXTENSIONS

    if has_payload and is_dangerous:
        severity  = "CRITICAL"
        event_tag = f"CVE_{source_label}_WEBSHELL_PAYLOAD"
    elif is_dangerous:
        severity  = "CRITICAL"
        event_tag = f"CVE_{source_label}_DANGEROUS_EXT"
    else:
        severity  = "MEDIUM"
        event_tag = f"CVE_{source_label}_SAFE"

    detail = (
        f"{source_label} upload from {client_ip} | "
        f"file={safe_name} | ext={extension or 'none'} | "
        f"has_payload={has_payload} | snippet={repr(raw_sample[:60])}"
    )
    _log_event(severity, event_tag, detail, client_ip)

    # ── Intelligence: record upload with full file analysis ──
    _intel.record_upload(client_ip, safe_name, raw_bytes,
                         endpoint=f"/{source_label.lower()}")

    if has_payload:
        send_alert(
            client_ip, f"CVE_{source_label}_WEBSHELL_REGISTERED",
            f"Webshell payload detected in '{safe_name}' from {client_ip} — "
            f"file registered for execution trap at /uploads/{safe_name}",
        )

    fake_file_id = f"{source_label.lower()[:3]}-{random.randint(100000, 999999)}"
    event = {
        "timestamp":       _now(),
        "ip":              client_ip,
        "user_agent":      user_agent[:200],
        "filename":        safe_name,
        "extension":       extension,
        "severity":        severity,
        "dangerous":       is_dangerous,
        "has_payload":     has_payload,
        "content_preview": raw_sample[:100],
        "event":           event_tag,
        "file_id":         fake_file_id,
        "type":            "upload",
        "source":          source_label,
        "webshell_hit":    False,
        "commands_tried":  [],
    }
    upload_events.append(event)

    # Register file so the webshell trap knows it's real
    if has_payload:
        _shell_registry[safe_name] = event

    return event, safe_name, fake_file_id


# ------------------------------------------------------------------
# Dangerous extensions
# ------------------------------------------------------------------
_DANGEROUS_EXTENSIONS = {".php", ".jsp", ".asp", ".aspx", ".py", ".sh", ".rb", ".phtml"}


# ------------------------------------------------------------------
# Spring POST handler
# ------------------------------------------------------------------

def _route_spring_upload_post():
    client_ip  = request.remote_addr
    user_agent = request.headers.get("User-Agent", "")

    event, safe_name, fake_file_id = _handle_upload(
        client_ip, user_agent, "SPRING",
        success_url_template="/uploads/{filename}",
        header_fn=_add_spring_headers,
    )

    payload = {
        "status":    "success",
        "file_id":   fake_file_id,
        "filename":  safe_name,
        "url":       f"/uploads/{safe_name}",
        "message":   "Document received and queued for compliance review.",
        "timestamp": _now(),
    }
    resp = make_response(jsonify(payload), 200)
    return _add_spring_headers(resp)


# ------------------------------------------------------------------
# PHP upload form — GET /clientportal/support/attachments.php
# ------------------------------------------------------------------

def _php_form_html():
    ts = __import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>BankCorp Client Portal &mdash; Support Ticket Attachment</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: Tahoma, Arial, sans-serif; background: #dde1e7; }}
    #wrap {{ width: 540px; margin: 55px auto; }}
    #hdr {{
      background: #1c3f6e; color: #fff; padding: 11px 18px;
      font-size: 15px; font-weight: bold;
      border-bottom: 3px solid #142d50;
    }}
    #hdr span {{ font-weight: normal; font-size: 11px; opacity: .75; margin-left: 10px; }}
    #panel {{
      background: #fff; border: 1px solid #b0b8c4; border-top: none;
      padding: 24px 22px 20px;
    }}
    .row {{ margin-bottom: 16px; }}
    label {{ display: block; font-size: 12px; color: #555; margin-bottom: 4px; }}
    input[type="file"] {{
      width: 100%; padding: 9px; border: 1px solid #b0b8c4;
      background: #f6f8fa; font-size: 13px;
    }}
    .note {{ font-size: 11px; color: #999; margin-top: 5px; }}
    input[type="text"] {{
      width: 100%; padding: 7px; border: 1px solid #b0b8c4; font-size: 13px;
    }}
    .btn {{
      background: #1c3f6e; color: #fff; border: 1px solid #142d50;
      padding: 9px 24px; font-size: 13px; font-weight: bold; cursor: pointer;
    }}
    .btn:hover {{ background: #142d50; }}
    #ftr {{
      background: #eaecef; border: 1px solid #b0b8c4; border-top: none;
      padding: 8px 18px; font-size: 10px; color: #999; text-align: right;
    }}
  </style>
</head>
<body>
  <div id="wrap">
    <div id="hdr">
      &#128194; BankCorp Client Portal &mdash; Support Attachment Upload
      <span>Ticket System v4.8</span>
    </div>
    <div id="panel">
      <form method="POST" action="/clientportal/support/attachments.php"
            enctype="multipart/form-data">
        <div class="row">
          <label for="ticketid">Support Ticket ID</label>
          <input type="text" id="ticketid" name="ticket_id"
                 placeholder="TKT-XXXXXXX" required>
        </div>
        <div class="row">
          <label for="ufile">Attach File</label>
          <input type="file" id="ufile" name="file" required>
          <div class="note">
            Accepted: jpg, jpeg, png, gif, pdf, doc, docx, xls, xlsx, txt, zip
          </div>
        </div>
        <input type="submit" class="btn" value="Upload Attachment">
      </form>
    </div>
    <div id="ftr">
      PHP/7.4.33 &nbsp;|&nbsp; Apache/2.4.54 (Debian)
      &nbsp;|&nbsp; Server time: {ts}
    </div>
  </div>
</body>
</html>
"""


def _route_php_upload_get():
    client_ip = request.remote_addr
    _log_event("INFO", "CVE_PHP_UPLOAD_FORM",
               f"PHP upload form accessed from {client_ip}", client_ip)
    _intel.record_form_view(client_ip, "/clientportal/support/attachments.php")
    resp = make_response(_php_form_html(), 200)
    resp.content_type = "text/html; charset=utf-8"
    return _add_php_headers(resp)


def _route_php_upload_post():
    client_ip  = request.remote_addr
    user_agent = request.headers.get("User-Agent", "")

    event, safe_name, fake_file_id = _handle_upload(
        client_ip, user_agent, "PHP",
        success_url_template="/uploads/{filename}",
        header_fn=_add_php_headers,
    )

    ticket_id = request.form.get("ticket_id", "TKT-0000000").strip()
    pub_url   = f"/uploads/{safe_name}"

    result_block = (
        f"<b style='color:#2a7a2a'>&#10003; Attachment uploaded successfully.</b><br><br>"
        f"Ticket: <code>{ticket_id}</code><br>"
        f"File: <code>{safe_name}</code><br>"
        f"Access: <a href='{pub_url}'>{pub_url}</a>"
    )

    page = f"""\
<!DOCTYPE html><html><head><meta charset='UTF-8'>
<title>Upload Result &mdash; BankCorp Client Portal</title>
<style>
  body{{font-family:Tahoma,Arial,sans-serif;background:#dde1e7;}}
  #box{{width:540px;margin:55px auto;background:#fff;border:1px solid #b0b8c4;padding:22px;}}
  #hdr{{background:#1c3f6e;color:#fff;padding:9px 18px;font-weight:bold;
        border-bottom:3px solid #142d50;margin:-22px -22px 18px;}}
</style></head><body>
<div id='box'>
  <div id='hdr'>&#128194; BankCorp Client Portal &mdash; Attachment Upload</div>
  {result_block}
  <br><br><a href='/clientportal/support/attachments.php'>&larr; Upload another file</a>
</div></body></html>"""

    resp = make_response(page, 200)
    resp.content_type = "text/html; charset=utf-8"
    return _add_php_headers(resp)


# ------------------------------------------------------------------
# Webshell execution trap — GET /uploads/<filename>
# ------------------------------------------------------------------

def _route_webshell_get(filename: str):
    """
    Only responds to filenames that were actually uploaded WITH real webshell code.
    Any other filename → realistic 403 or 404.
    """
    client_ip = request.remote_addr
    cmd       = request.args.get("cmd", "").strip()

    # ── Guard: filename must be in registry (i.e. uploaded with real payload) ──
    if filename not in _shell_registry:
        # Plausible Apache "forbidden" — doesn't hint at the trap
        _log_event("MEDIUM", "CVE_UPLOAD_PROBE",
                   f"Probe of unregistered path /uploads/{filename} from {client_ip}",
                   client_ip)
        resp = make_response(
            "<html><head><title>403 Forbidden</title></head>"
            "<body><h1>Forbidden</h1>"
            "<p>You don't have permission to access this resource.</p>"
            "<hr><address>Apache/2.4.54 (Debian) Server at bankcorpweb-02.internal Port 80</address>"
            "</body></html>",
            403,
        )
        resp.content_type = "text/html; charset=utf-8"
        return _add_php_headers(resp)

    # ── Registered webshell hit ──
    time.sleep(random.uniform(0.05, 0.30))  # realistic delay

    send_alert(
        client_ip, "CVE_WEBSHELL_HIT",
        f"Webshell executed: /uploads/{filename} | cmd={repr(cmd) if cmd else '<browse>'} "
        f"| from {client_ip}"
    )

    # Update event record
    ev = _shell_registry[filename]
    ev["webshell_hit"] = True
    if cmd and cmd not in ev["commands_tried"]:
        ev["commands_tried"].append(cmd)

    # ── Build response ──
    if not cmd:
        output = "<?php system($_GET['cmd']); ?>"
        resp = make_response(output + "\n", 200)
    else:
        out_text, found = _get_shell_output(cmd)
        # ── Intelligence: record every command with its output ──
        _intel.record_webshell_access(client_ip, filename, cmd, out_text)
        resp = make_response(out_text + "\n", 200)

    resp.content_type = "text/plain; charset=utf-8"
    return _add_php_headers(resp)


# ------------------------------------------------------------------
# Dashboard data — GET /api/dashboard/cve/file-upload
# ------------------------------------------------------------------

def _route_dashboard_summary():
    """
    Professional intelligence dashboard for the File Upload CVE module.
    Combines per-attacker profiling, geo, phase classification,
    command risk scoring, file analysis, and deception advisor.
    """
    intel  = _intel.dashboard_summary()
    # Inject active webshell count from local registry
    intel["stats"]["active_webshells"] = len(_shell_registry)
    intel["stats"]["total_upload_events"] = len(upload_events)

    # Enrich with CVE identity
    payload = {
        "cve":         "CVE-2020-36179",
        "description": "File Upload RCE — BankCorp Dynamic Honeypot",
        "module":      "file_upload_rce",
        "endpoints": [
            "GET|POST /api/v2/documents/compliance-upload",
            "GET|POST /clientportal/support/attachments.php",
            "GET /uploads/<filename>?cmd=<command>",
        ],
        "registered_shells": list(_shell_registry.keys()),
        **intel,
    }
    resp = make_response(jsonify(payload), 200)
    return _add_spring_headers(resp)


# ------------------------------------------------------------------
# Registration
# ------------------------------------------------------------------

def register_file_upload_routes(app, state_manager=None, app_logger=None):
    """
    Register all File Upload RCE deception routes on the given Flask app.

    Usage in honeypot.py:
        from src.file_upload_rce import register_file_upload_routes
        register_file_upload_routes(app, state_manager=state, app_logger=logger)
    """
    global _state, _logger

    if state_manager is not None:
        _state = state_manager
    else:
        from src.state import APIStateManager
        _state = APIStateManager()

    _logger = app_logger or logging.getLogger(__name__)

    # Generate AI shell responses once at startup
    api_key = None
    try:
        import os
        from pathlib import Path
        from dotenv import load_dotenv
        load_dotenv(Path(__file__).parent.parent.resolve() / ".env")
        api_key = (
            os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        if not api_key:
            import google.generativeai as _g
            api_key = getattr(_g, "_DefaultApiKey", None)
    except Exception:
        pass

    # Init the RAG shell response engine (loads shell_rag.pkl + Gemini fallback)
    # All command responses are served dynamically — no static pre-generation.
    from src.rag import shell_rag_loader as _rag_mod
    _rag_mod.init(api_key=api_key)
    _logger.info("[CVE-2020-36179] RAG shell engine ready — %s",
                 _rag_mod.get_metadata())

    # Routes are registered as explicit shims in honeypot.py (before the
    # /<path:full_path> catch-all). The dashboard route is registered here
    # because it doesn't conflict with any catch-all pattern.

    @app.route("/api/dashboard/cve/file-upload", methods=["GET"])
    def dashboard_file_upload():
        return _route_dashboard_summary()

    @app.route("/api/dashboard/cve/file-upload/attacker/<path:ip>", methods=["GET"])
    def dashboard_attacker_detail(ip):
        """Deep profile for a single attacker IP."""
        data = _intel.get_session(ip)
        if not data:
            return make_response(jsonify({"error": "No data for this IP"}), 404)
        return make_response(jsonify(data), 200)

    @app.route("/api/dashboard/cve/file-upload/attackers", methods=["GET"])
    def dashboard_all_attackers():
        """List all known attacker IPs with summary stats."""
        all_s = _intel.get_all_sessions()
        return make_response(jsonify({
            "count":     len(all_s),
            "attackers": all_s,
        }), 200)

    _logger.info(
        "[CVE-2020-36179] File Upload RCE module initialised — "
        "Spring: GET|POST /api/v2/documents/compliance-upload | "
        "PHP: GET|POST /clientportal/support/attachments.php | "
        "Trap: GET /uploads/<file> | "
        "Dashboard: GET /api/dashboard/cve/file-upload"
    )
