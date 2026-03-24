"""
Maze Myth — Intelligence Dashboard Backend  (port 8002)
=======================================================
Data sources:
  - databases/honeypot.db  (shared SQLite file) → all persisted events
  - log_files/api_audit.log (shared Base64 log) → live feed
  - HTTP → honeypot:8001   → in-memory CVE intel (active sessions)

API
---
GET /                          Dashboard UI
GET /api/stats                 All counters
GET /api/new                   New log entries since last poll
GET /api/downloads             File download log
GET /api/sensitive             Sensitive file downloads
GET /api/unique_ips            Every unique attacker IP seen
GET /api/intel/summary         CVE attacker intel (proxy → 8001)
GET /api/intel/attackers       All attacker profiles (proxy → 8001)
GET /api/intel/attacker/<ip>   Per-IP profile (proxy → 8001)
GET /api/intel/analyze/<ip>    Gemini analysis of one attacker
GET /api/intel/analyze/all     Gemini cross-attacker analysis
"""

import sys, base64, json, re, os, sqlite3, logging
from pathlib import Path

# Load Environment Variables BEFORE initializing anything else
try:
    from dotenv import load_dotenv
    root_dir = Path(__file__).parent.parent.resolve()
    env_file = root_dir / ".env"
    template_file = root_dir / ".env.template"
    
    if env_file.exists():
        load_dotenv(env_file)
    elif template_file.exists():
        load_dotenv(template_file)
except ImportError:
    pass
from datetime import datetime
from collections import deque

from flask import Flask, jsonify, send_file
from flask_cors import CORS

# ── Paths (absolute — dashboard/ runs from a different CWD) ──────────────────
ROOT     = Path(__file__).parent.parent.resolve()

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass

DB_PATH  = ROOT / "databases" / "honeypot.db"
LOG_FILE = ROOT / "log_files" / "api_audit.log"

app = Flask(__name__)
CORS(app)
log = logging.getLogger(__name__)

HONEYPOT = os.getenv("HONEYPOT_INTERNAL_URL", "http://127.0.0.1:8001")

# Live feed buffer
recent_activity = deque(maxlen=300)
last_position   = 0


# ── SQLite helper (read-only, uses absolute path) ─────────────────────────────

def _db():
    """Return a read-only SQLite connection to the shared honeypot.db."""
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True,
                           check_same_thread=False, timeout=3)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def _query(sql: str, params=()) -> list[dict]:
    """Run a SELECT and return list-of-dicts. Returns [] if DB missing."""
    conn = _db()
    if not conn:
        return []
    try:
        rows = conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]
    except Exception as e:
        log.warning("[DB] query error: %s", e)
        return []
    finally:
        conn.close()


def _scalar(sql: str, params=(), default=0):
    conn = _db()
    if not conn:
        return default
    try:
        r = conn.execute(sql, params).fetchone()
        return r[0] if r else default
    except Exception:
        return default
    finally:
        conn.close()


# ── HTTP proxy to honeypot ────────────────────────────────────────────────────

def _honeypot_get(path: str):
    import urllib.request
    try:
        with urllib.request.urlopen(HONEYPOT.rstrip("/") + path, timeout=4) as r:
            return json.loads(r.read())
    except Exception as e:
        log.warning("[Proxy] %s → %s", path, e)
        return None


# ── Gemini ────────────────────────────────────────────────────────────────────

_gemini = None

def _get_gemini():
    global _gemini
    if _gemini:
        return _gemini
    try:
        import google.generativeai as genai
        key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            return None
        genai.configure(api_key=key)
        _gemini = genai.GenerativeModel(os.getenv("LLM_MODEL", "gemini-2.5-flash"))
        return _gemini
    except Exception as e:
        log.warning("[Gemini] unavailable: %s", e)
        return None


# ── Log file parsing ──────────────────────────────────────────────────────────

def _decode(line: str):
    try:
        return base64.b64decode(line.strip()).decode("utf-8", errors="ignore")
    except Exception:
        return None


def _is_internal(text: str) -> bool:
    """
    Skip werkzeug/Flask access log lines that are internal dashboard polls.
    These look like: - [24/Mar/2026 03:57:43] "GET /api/dashboard/cve/... HTTP/1.1" 200 -
    """
    # werkzeug access log pattern
    if re.search(r'"(GET|POST|PUT|DELETE) /api/(dashboard|new|stats|intel|unique|downloads|sensitive)', text):
        return True
    # anything from 127.0.0.1 that is a Flask access log line
    if '127.0.0.1' in text and ('HTTP/1.' in text or '" 200' in text or '" 404' in text):
        return True
    return False


def _parse(text: str) -> dict | None:
    # Drop internal dashboard poll lines before doing anything else
    if _is_internal(text):
        return None

    e = {"timestamp": "", "level": "INFO", "message": "",
         "type": "general", "event": "", "client_ip": ""}

    m = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", text)
    if m:
        e["timestamp"] = m.group(1)

    for lvl in ("CRITICAL", "WARNING", "INFO", "ERROR"):
        if f" - {lvl} - " in text:
            e["level"] = lvl
            break

    CVE = {
        "CVE_WEBSHELL_HIT":               ("webshell",         "🐚 Webshell cmd executed"),
        "CVE_PHP_WEBSHELL_PAYLOAD":        ("webshell_upload",  "☠️  PHP webshell uploaded"),
        "CVE_SPRING_WEBSHELL_PAYLOAD":     ("webshell_upload",  "☠️  Spring webshell uploaded"),
        "CVE_PHP_WEBSHELL_REGISTERED":     ("webshell_upload",  "🔴 Webshell trap registered"),
        "CVE_SPRING_WEBSHELL_REGISTERED":  ("webshell_upload",  "🔴 Spring trap registered"),
        "CVE_PHP_DANGEROUS_EXT":           ("dangerous_upload", "⚠️  Dangerous extension upload"),
        "CVE_SPRING_DANGEROUS_EXT":        ("dangerous_upload", "⚠️  Dangerous ext (Spring)"),
        "CVE_UPLOAD_FORM":                 ("form_view",        "📋 Upload form viewed"),
        "CVE_PHP_UPLOAD_FORM":             ("form_view",        "📋 PHP form viewed"),
        "CVE_UPLOAD_PROBE":                ("probe",            "🔍 Unregistered path probed"),
    }
    for tag, (etype, label) in CVE.items():
        if tag in text:
            tail = text.split(" - ")[-1].strip()[:100]
            e.update(type=etype, event=tag, message=f"{label} — {tail}")
            ip = re.search(r"from (\d+\.\d+\.\d+\.\d+)", text)
            if ip:
                e["client_ip"] = ip.group(1)
            return e

    if "BEACON_ACTIVATED" in text:
        e.update(type="beacon", message="🚨 " + text.split(" - ")[-1].strip()[:120])
    elif "FILE_DOWNLOAD" in text or "/api/download/" in text:
        e.update(type="download", message="📄 " + text.split(" - ")[-1].strip()[:120])
    elif "[EXPORT]" in text:
        e.update(type="download", message="📦 " + text.split(" - ")[-1].strip()[:120])
    elif "NEW_ENDPOINT_DISCOVERY" in text or "NEW endpoint" in text:
        e.update(type="discovery", message="🔍 " + text.split(" - ")[-1].strip()[:120])
    elif "[AUTH]" in text:
        e.update(type="auth", message="🔑 " + text.split(" - ")[-1].strip()[:120])
    else:
        parts = text.split(" - ")
        e["message"] = (parts[-1].strip() if len(parts) > 1 else text)[:120]

    ip = re.search(r"(\d+\.\d+\.\d+\.\d+)", text)
    if ip:
        e["client_ip"] = ip.group(1)
    return e


def _poll_log() -> list[dict]:
    global last_position
    if not LOG_FILE.exists():
        return []
    new = []
    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
            f.seek(last_position)
            for line in f:
                if line.strip():
                    decoded = _decode(line)
                    if decoded:
                        entry = _parse(decoded)
                        if entry is not None:   # None = filtered internal request
                            new.append(entry)
                            recent_activity.append(entry)
            last_position = f.tell()
    except Exception as ex:
        log.error("[Log] read error: %s", ex)
    return new


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_file("index.html")


@app.route("/api/new")
def get_new():
    return jsonify(_poll_log())


@app.route("/api/stats")
def get_stats():
    """
    All counters from SQLite (shared file) + CVE intel from honeypot proxy.
    Downloads, beacons, endpoints, unique IPs — all from SQLite.
    """
    # SQLite (always accurate, persisted across restarts)
    total_endpoints    = _scalar("SELECT COUNT(*) FROM endpoints")
    total_downloads    = _scalar("SELECT COUNT(*) FROM downloads")
    total_beacons      = _scalar("SELECT COUNT(*) FROM beacons")
    activated_beacons  = _scalar("SELECT COUNT(*) FROM beacons WHERE accessed_at IS NOT NULL")
    unique_visitor_ips = _scalar("SELECT COUNT(DISTINCT client_ip) FROM logs WHERE client_ip != ''")

    # Every unique IP in the downloads table
    download_ips = {r["client_ip"] for r in _query("SELECT DISTINCT client_ip FROM downloads WHERE client_ip != ''")}
    # Every unique IP in the logs table
    log_ips      = {r["client_ip"] for r in _query("SELECT DISTINCT client_ip FROM logs WHERE client_ip != ''")}
    all_ips      = sorted(download_ips | log_ips)

    # CVE intel (honeypot process in-memory, may not be populated on restart)
    intel     = _honeypot_get("/api/dashboard/cve/file-upload") or {}
    cve_stats = intel.get("stats", {})

    return jsonify({
        # SQLite counts
        "total_endpoints":   total_endpoints,
        "total_downloads":   total_downloads,
        "total_beacons":     total_beacons,
        "activated_beacons": activated_beacons,
        "unique_visitor_ips": len(all_ips),
        "all_ips":           all_ips,
        # CVE intel
        "unique_attackers":  cve_stats.get("unique_attackers", 0),
        "webshell_uploads":  cve_stats.get("webshell_uploads",  0),
        "total_uploads":     cve_stats.get("total_uploads",     0),
        "total_commands":    cve_stats.get("total_commands",    0),
        "revshell_attempts": cve_stats.get("revshell_attempts", 0),
    })


@app.route("/api/unique_ips")
def unique_ips():
    """All unique IPs seen across downloads table and logs table."""
    dl_ips  = {r["client_ip"] for r in _query("SELECT DISTINCT client_ip FROM downloads WHERE client_ip != ''")}
    log_ips = {r["client_ip"] for r in _query("SELECT DISTINCT client_ip FROM logs WHERE client_ip != ''")}
    ips     = sorted(dl_ips | log_ips)
    return jsonify({"count": len(ips), "ips": ips})


@app.route("/api/downloads")
def get_downloads():
    rows = _query("SELECT filename, client_ip, user_agent, timestamp, is_sensitive FROM downloads ORDER BY timestamp DESC LIMIT 200")
    return jsonify({"downloads": rows, "total": len(rows),
                    "sensitive_count": sum(1 for r in rows if r.get("is_sensitive"))})


@app.route("/api/sensitive")
def get_sensitive():
    rows = _query("SELECT filename, client_ip, user_agent, timestamp FROM downloads WHERE is_sensitive=1 ORDER BY timestamp DESC")
    return jsonify({"downloads": rows, "total": len(rows)})


# ── Intel proxy ───────────────────────────────────────────────────────────────

@app.route("/api/intel/summary")
def intel_summary():
    data = _honeypot_get("/api/dashboard/cve/file-upload")
    if data is None:
        return jsonify({"error": "Honeypot not reachable on port 8001",
                        "stats": {}, "top_attackers": [],
                        "phase_distribution": {}, "recent_events": [],
                        "top_dangerous_commands": []}), 503
    return jsonify(data)


@app.route("/api/intel/attackers")
def intel_attackers():
    data = _honeypot_get("/api/dashboard/cve/file-upload/attackers")
    return jsonify(data or {"count": 0, "attackers": []})


@app.route("/api/intel/attacker/<path:ip>")
def intel_attacker(ip):
    data = _honeypot_get(f"/api/dashboard/cve/file-upload/attacker/{ip}")
    if not data:
        return jsonify({"error": "No data"}), 404
    return jsonify(data)


# ── AI behavior analysis ──────────────────────────────────────────────────────

@app.route("/api/intel/analyze/<path:ip>")
def analyze_attacker(ip):
    session = _honeypot_get(f"/api/dashboard/cve/file-upload/attacker/{ip}")
    if not session:
        return jsonify({"error": "No session data — attacker may not have interacted with CVE trap"}), 404

    # Pull download history + log events from SQLite for this IP
    dl_rows  = _query("SELECT filename, timestamp FROM downloads WHERE client_ip=? ORDER BY timestamp DESC LIMIT 30", (ip,))
    log_rows = _query("SELECT message, level, timestamp FROM logs WHERE client_ip=? ORDER BY timestamp ASC LIMIT 50", (ip,))

    analysis = _rule_based(session, dl_rows)
    method   = "rule_based"
    model    = _get_gemini()

    if model:
        geo   = session.get("geo", {})
        cmds  = session.get("top_commands", [])[:15]
        files = session.get("uploaded_files", [])
        dl_summary  = "\n".join(f"  • {r['filename']} @ {r['timestamp'][:16]}" for r in dl_rows) or "  None"
        log_summary = "\n".join(f"  [{r['level']}] {r['timestamp'][:16]} {r['message'][:80]}" for r in log_rows) or "  None"
        cmd_sequence = "\n".join(f"  {i+1:02d}. [{c['risk']}/100 risk] {c['cmd']}  ({c.get('phase','?')} phase, {c.get('label','unlabeled')})"
                                  for i, c in enumerate(cmds)) or "  None"
        file_detail  = "\n".join(f"  • {f['filename']} | threat:{f.get('threat_level','?')} | patterns:{f.get('patterns',[])}"
                                  for f in files) or "  None"

        prompt = f"""You are a senior threat intelligence analyst producing a deep behavioral profile of a honeypot intruder.
This attacker interacted with a fake banking portal (BankCorp) simulating CVE-2020-36179 (Spring/PHP file upload RCE).

=== ATTACKER PROFILE ===
IP: {ip}
Location: {geo.get("city","?")} · {geo.get("country","?")} · {geo.get("region","?")}
ISP/ASN: {geo.get("isp","?")} / {geo.get("asn","?")}
VPN: {'YES ⚠️' if geo.get("is_proxy") or geo.get("is_vpn") else 'No'} | Hosting/Cloud: {'YES ⚠️' if geo.get("is_hosting") else 'No'}

=== SESSION METRICS ===
Phase reached: {session.get("phase_label", session.get("current_phase","?"))}
Engagement score: {session.get("engagement_score",0)}/100
Session duration: {session.get("session_duration_s",0)}s
Commands executed: {session.get("commands_run",0)}
Webshells uploaded: {session.get("webshells_uploaded",0)}
Reverse shell attempts: {session.get("revshell_attempts",0)}

=== COMMAND SEQUENCE (chronological, with risk score) ===
{cmd_sequence}

=== UPLOADED FILES ===
{file_detail}

=== BAIT FILES DOWNLOADED ===
{dl_summary}

=== LOG TRAIL ===
{log_summary}

=== INTELLIGENCE REPORT (be specific, data-driven, and actionable) ===

**1. Skill Assessment**
Rate as: Script Kiddie / Intermediate / Advanced / Nation-State. Cite specific evidence from commands, tools, and techniques. Note any automation signatures or manual keyboard patterns.

**2. Attack Kill Chain**
Map the session to MITRE ATT&CK stages (Reconnaissance → Weaponization → Delivery → Exploitation → Installation → C2 → Exfiltration). Which stages did they reach? What did they skip?

**3. Tool & Technique Fingerprint**
Identify specific tools (Metasploit, SQLmap, Burp, custom scripts, etc.) inferred from command patterns. Note any unique signatures, timing patterns, or encoding quirks that could be a fingerprint.

**4. Objective Analysis**
What was their primary goal? Data exfiltration? Persistence? Lateral movement? Ransomware staging? Provide evidence-based conclusion.

**5. Behavioral Psychology**
How methodical vs. rushed? Did they adapt when commands failed? Did they notice deception artifacts? What does their patience level suggest?

**6. Deception Effectiveness**
Which deception elements kept them engaged? What did they believe that was false? What would have caused them to leave?

**7. Predicted Next Actions**
If this attacker returns: what would they try next? What credentials, files, or IPs would they target?

**8. Counter-Deception Recommendations**
Precisely name 3 changes to the honeypot that would: (a) extend time-on-target, (b) gather more intelligence, (c) escalate their commitment further into the trap."""

        try:
            resp = model.generate_content(prompt)
            analysis = resp.text
            method   = "gemini"
        except Exception as ex:
            log.warning("[Analyze] Gemini: %s", ex)

    return jsonify({"ip": ip, "geo": session.get("geo", {}),
                    "phase": session.get("current_phase", "?"),
                    "engagement": session.get("engagement_score", 0),
                    "analysis": analysis, "method": method,
                    "analyzed_at": datetime.utcnow().isoformat() + "Z"})


@app.route("/api/intel/analyze/all")
def analyze_all():
    data     = _honeypot_get("/api/dashboard/cve/file-upload/attackers")
    sessions = (data or {}).get("attackers", [])

    phases = {}
    total_ws = total_rs = 0
    summaries = []
    for s in sessions[:20]:
        p = s.get("current_phase", "IDLE")
        phases[p] = phases.get(p, 0) + 1
        total_ws += s.get("webshells_uploaded", 0)
        total_rs += s.get("revshell_attempts", 0)
        cmds = [c["cmd"] for c in s.get("top_commands", [])[:3]]
        summaries.append(f"IP={s['ip']} country={s.get('geo',{}).get('country','?')} "
                         f"phase={p} eng={s.get('engagement_score',0)} "
                         f"ws={s.get('webshells_uploaded',0)} rs={s.get('revshell_attempts',0)} "
                         f"cmds=[{', '.join(cmds)}]")

    analysis = (f"Analyzed {len(sessions)} attackers. "
                f"{total_ws} webshell uploads, {total_rs} reverse shell attempts. "
                f"Phase distribution: {json.dumps(phases)}")
    method = "rule_based"
    model  = _get_gemini()

    if model and sessions:
        prompt = f"""Threat intelligence report for {len(sessions)} honeypot attacker sessions.

GLOBAL: webshell_uploads={total_ws} revshell_attempts={total_rs} phases={json.dumps(phases)}

SESSIONS:
{chr(10).join(summaries)}

Report (concise, data-driven, markdown bold headers):
1. **Population Profile** — skill distribution, geographic patterns
2. **Common Attack Chains** — typical sequence of actions
3. **Tool & Technique Patterns** — shared payloads? automated scanners?
4. **Most Sophisticated Sessions** — who stood out
5. **Deception Effectiveness** — what worked, what didn't
6. **Recommendations** — how to attract more advanced attackers"""
        try:
            resp = model.generate_content(prompt)
            analysis = resp.text
            method   = "gemini"
        except Exception as ex:
            log.warning("[AnalyzeAll] Gemini: %s", ex)

    return jsonify({"total_attackers": len(sessions), "total_webshells": total_ws,
                    "total_revshells": total_rs, "phase_distribution": phases,
                    "analysis": analysis, "method": method,
                    "analyzed_at": datetime.utcnow().isoformat() + "Z"})


def _rule_based(s: dict, dl_rows: list) -> str:
    geo  = s.get("geo", {})
    cmds = s.get("top_commands", [])
    rev  = s.get("revshell_attempts", 0)
    ws   = s.get("webshells_uploaded", 0)
    nc   = s.get("commands_run", 0)
    dur  = s.get("session_duration_s", 0)
    skill = ("Advanced" if rev >= 3 or any(c["risk"] > 85 for c in cmds)
             else "Intermediate" if ws >= 1 or nc >= 8 else "Script Kiddie")
    lines = [
        f"**Skill Level**: {skill}",
        f"- Origin: {geo.get('city','?')}, {geo.get('country','?')} | ISP: {geo.get('isp','?')}",
        f"- VPN/Hosting: {'Yes ⚠️' if geo.get('is_proxy') or geo.get('is_hosting') else 'No'}",
        "",
        f"**Attack Strategy**: Reached {s.get('current_phase','?')} in {dur}s with {nc} commands.",
        f"Uploaded {ws} webshell(s), attempted {rev} reverse shell(s).",
    ]
    if dl_rows:
        lines += ["", "**Downloaded Bait Files**:"] + [f"  • {r['filename']} @ {r['timestamp'][:16]}" for r in dl_rows]
    if cmds:
        lines += ["", "**Top Commands by Risk**:"] + [f"  [{c['risk']}/100] {c['cmd']} → {c.get('label','')}" for c in cmds[:6]]
    rec = s.get("deception", {}).get("recommendation", "")
    if rec:
        lines += ["", f"**Deception Recommendation**: {rec}"]
    return "\n".join(lines)


# ── Startup ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "="*60)
    print("  MAZE MYTH — Intelligence Dashboard  :8002")
    print("="*60)
    print(f"  DB:      {DB_PATH}")
    print(f"  Log:     {LOG_FILE}")
    print(f"  Honeypot: {HONEYPOT}")
    print("="*60 + "\n")
    if not DB_PATH.exists():
        print("[WARNING] honeypot.db not found — start the honeypot first!")

    # Preload last 100 lines from log file
    if LOG_FILE.exists():
        try:
            with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
            for line in lines[-100:]:
                d = _decode(line)
                if d:
                    recent_activity.append(_parse(d))
            last_position = LOG_FILE.stat().st_size
        except Exception as ex:
            print(f"[WARNING] Could not load log: {ex}")

    app.run(host="0.0.0.0", port=8002, debug=False, use_reloader=False)
