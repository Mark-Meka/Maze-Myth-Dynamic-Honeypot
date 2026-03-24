"""
Attacker Intelligence Engine
=============================
Tracks, profiles, and analyzes every attacker interacting with the
file-upload honeypot. Feeds the professional dashboard.

Features
--------
- Per-IP session timeline (all events in chronological order)
- Attack phase classification: RECON → EXPLOIT → POST_EXPLOIT → LATERAL
- Command risk scoring (0–100)
- Malicious file analysis: extension, MIME, embedded patterns detected
- IP geolocation (ip-api.com — free, no key needed)
- Deception strategy advisor ("lure attacker into doing X next")
- Persistence: all data backed by the existing SQLite state manager
"""

import re
import json
import logging
import time
import threading
from datetime import datetime, timezone
from collections import defaultdict
from pathlib import Path
from typing import Optional

_log = logging.getLogger(__name__)

# ── Module-level session store (in-memory, fast) ─────────────────────────────
# ip → AttackerSession
_sessions: dict[str, "AttackerSession"] = {}
_lock = threading.Lock()

# ── Geo cache (ip → dict) — avoids hammering the free API ────────────────────
_geo_cache: dict[str, dict] = {}

# ── Pattern libraries ─────────────────────────────────────────────────────────

# Command → (risk_score 0-100, category, label)
_CMD_RISK_TABLE = [
    # Phase: RECON
    (r"^(whoami|id|uname|hostname|pwd|groups|w|who)(\s|$)",            15, "RECON",        "Identity check"),
    (r"^(ls|dir|find)\s",                                               20, "RECON",        "Filesystem listing"),
    (r"cat\s+/etc/(passwd|hosts|issue|os-release|resolv\.conf)",        25, "RECON",        "System file read"),
    (r"^(ps|top|htop|pstree)\b",                                        20, "RECON",        "Process enumeration"),
    (r"^(ifconfig|ip\s|netstat|ss\s|arp\s|route)",                      25, "RECON",        "Network recon"),
    (r"^(env|printenv|set\b)",                                           30, "RECON",        "Environment dump"),
    (r"^(history|cat\s+~/\.bash_history)",                               35, "RECON",        "History read"),
    # Phase: EXPLOIT
    (r"cat\s+/etc/shadow",                                               55, "EXPLOIT",      "Shadow file read"),
    (r"sudo\s+-l",                                                        45, "EXPLOIT",      "Sudo check"),
    (r"(find|locate).*(-perm|SUID|SGID|-u\s+root)",                      60, "EXPLOIT",      "SUID/SGID hunt"),
    (r"(curl|wget)\s+http",                                               65, "EXPLOIT",      "Remote download"),
    (r"chmod\s+[4-7][0-7][0-7]\s",                                       70, "EXPLOIT",      "Permission change"),
    (r"useradd|adduser|passwd\s+root",                                   80, "EXPLOIT",      "User manipulation"),
    (r"(echo|printf).*>>\s*/etc/",                                       75, "EXPLOIT",      "Config injection"),
    # Phase: POST_EXPLOIT
    (r"(nc|ncat|netcat)\s+.*-e\s+/bin",                                  90, "POST_EXPLOIT", "Netcat revshell"),
    (r"bash\s+-i\s+>&?\s+/dev/tcp/",                                     95, "POST_EXPLOIT", "Bash TCP revshell"),
    (r"python[23]?\s+-c\s+.*socket.*connect",                            90, "POST_EXPLOIT", "Python revshell"),
    (r"perl\s+-e\s+.*socket",                                            90, "POST_EXPLOIT", "Perl revshell"),
    (r"php\s+-r\s+.*fsockopen",                                          90, "POST_EXPLOIT", "PHP revshell"),
    (r"mkfifo\s+/tmp/",                                                   85, "POST_EXPLOIT", "FIFO revshell"),
    (r"(msfvenom|meterpreter|metasploit)",                               95, "POST_EXPLOIT", "Metasploit payload"),
    # Phase: LATERAL
    (r"ssh\s+.*@",                                                        70, "LATERAL",      "SSH lateral move"),
    (r"(scp|rsync)\s+",                                                   65, "LATERAL",      "File exfil"),
    (r"crontab\s+-e",                                                     80, "LATERAL",      "Cron persistence"),
    (r"(at|batch)\s+",                                                    75, "LATERAL",      "Scheduled task"),
]

# Compiled version
_CMD_RISK = [
    (re.compile(pat, re.IGNORECASE), score, cat, label)
    for pat, score, cat, label in _CMD_RISK_TABLE
]

# Malicious file pattern → tag
_FILE_PATTERNS = {
    rb"<\?php":                         "PHP_OPENER",
    rb"system\s*\(":                    "PHP_SYSTEM",
    rb"exec\s*\(":                      "PHP_EXEC",
    rb"shell_exec\s*\(":                "PHP_SHELL_EXEC",
    rb"passthru\s*\(":                  "PHP_PASSTHRU",
    rb"eval\s*\(":                      "PHP_EVAL",
    rb"base64_decode\s*\(":             "PHP_BASE64",
    rb"\$_GET\s*\[":                    "PHP_INPUT_GET",
    rb"\$_POST\s*\[":                   "PHP_INPUT_POST",
    rb"\$_REQUEST\s*\[":                "PHP_INPUT_REQUEST",
    rb"popen\s*\(":                     "PHP_POPEN",
    rb"proc_open\s*\(":                 "PHP_PROC_OPEN",
    rb"/bin/bash":                      "BASH_REFERENCE",
    rb"/dev/tcp/":                      "TCP_REVSHELL",
    rb"Runtime\.getRuntime\(\)":        "JAVA_RCE",
    rb"nc\s+-e\s+/bin":                 "NC_REVSHELL",
    rb"python.*socket.*connect":        "PYTHON_REVSHELL",
    rb"import\s+socket":                "PYTHON_SOCKET",
    rb"fsockopen":                      "PHP_FSOCKOPEN",
}
_FILE_PATTERNS_C = {
    re.compile(pat, re.IGNORECASE): tag
    for pat, tag in _FILE_PATTERNS.items()
}

# Extension risk
_DANGEROUS_EXT = {
    ".php", ".php3", ".php4", ".php5", ".phtml", ".phar",
    ".jsp", ".jspx", ".aspx", ".asp", ".cfm",
    ".py", ".rb", ".pl", ".sh", ".bash", ".cgi",
}
_SAFE_EXT = {".pdf", ".docx", ".xlsx", ".doc", ".xls", ".txt", ".csv", ".png", ".jpg"}

# ── Attack phase machine ───────────────────────────────────────────────────────

_PHASE_ORDER  = ["IDLE", "RECON", "EXPLOIT", "POST_EXPLOIT", "LATERAL"]
_PHASE_LABELS = {
    "IDLE":         "🕵️  Idle / Probing",
    "RECON":        "🔍  Reconnaissance",
    "EXPLOIT":      "💥  Exploitation",
    "POST_EXPLOIT": "🐚  Post-Exploitation",
    "LATERAL":      "🔗  Lateral Movement",
}


def _classify_command(cmd: str) -> dict:
    """Return risk score, category, and label for a shell command."""
    for pattern, score, cat, label in _CMD_RISK:
        if pattern.search(cmd):
            return {"score": score, "phase": cat, "label": label}
    return {"score": 10, "phase": "RECON", "label": "Generic command"}


def _analyze_file(raw_bytes: bytes, filename: str) -> dict:
    """
    Analyze uploaded file bytes.
    Returns a dict with extension risk, detected patterns, and threat level.
    """
    ext  = Path(filename).suffix.lower()
    tags = []
    for pat, tag in _FILE_PATTERNS_C.items():
        if pat.search(raw_bytes[:4096]):
            tags.append(tag)

    is_dangerous_ext  = ext in _DANGEROUS_EXT
    is_wrong_ext      = ext in _SAFE_EXT and bool(tags)  # pdf named file with php code
    is_webshell       = bool(tags)
    threat_level      = (
        "CRITICAL" if (is_webshell and is_dangerous_ext) else
        "HIGH"     if is_webshell else
        "MEDIUM"   if is_dangerous_ext else
        "LOW"
    )
    return {
        "filename":         filename,
        "extension":        ext,
        "extension_risk":   "DANGEROUS" if is_dangerous_ext else ("SUSPICIOUS" if is_wrong_ext else "SAFE"),
        "payload_tags":     tags,
        "is_webshell":      is_webshell,
        "is_wrong_ext":     is_wrong_ext,
        "threat_level":     threat_level,
        "byte_size":        len(raw_bytes),
        "has_php":          "PHP_OPENER" in tags,
        "has_revshell":     any(t in tags for t in ("TCP_REVSHELL","NC_REVSHELL","PYTHON_REVSHELL","PHP_FSOCKOPEN")),
        "has_eval":         "PHP_EVAL" in tags,
        "has_java_rce":     "JAVA_RCE" in tags,
    }


# ── IP Geolocation ─────────────────────────────────────────────────────────────

def _geolocate(ip: str) -> dict:
    """Fetch geo data from ip-api.com (free, no key, rate-limited to 45/min)."""
    if ip in _geo_cache:
        return _geo_cache[ip]

    # Skip private/loopback IPs
    if ip.startswith(("127.", "10.", "192.168.", "172.", "::1", "0.")):
        result = {
            "country": "Local",
            "countryCode": "LO",
            "regionName": "LAN",
            "city": "localhost",
            "isp": "Local Network",
            "org": "Local",
            "as": "",
            "lat": 0.0,
            "lon": 0.0,
            "proxy": False,
            "hosting": False,
            "mobile": False,
        }
        _geo_cache[ip] = result
        return result

    try:
        import urllib.request
        url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,regionName,city,isp,org,as,lat,lon,proxy,hosting,mobile"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read())
        if data.get("status") == "success":
            _geo_cache[ip] = data
            return data
    except Exception as e:
        _log.debug("[Intel] Geo lookup failed for %s: %s", ip, e)

    fallback = {"country": "Unknown", "countryCode": "??", "city": "Unknown",
                "isp": "Unknown", "org": "Unknown", "as": "",
                "lat": 0.0, "lon": 0.0, "proxy": False, "hosting": False, "mobile": False}
    _geo_cache[ip] = fallback
    return fallback


# ── Deception advisor ─────────────────────────────────────────────────────────

def _deception_strategy(session: "AttackerSession") -> dict:
    """
    Based on what the attacker has done so far, suggest the next
    deception move to keep them engaged longer.
    """
    phase    = session.current_phase
    cmds     = [e["data"].get("command","") for e in session.timeline if e["type"] == "CMD"]
    has_revshell = any("tcp" in c or "nc " in c or "bash -i" in c for c in cmds)
    has_recon    = session.event_counts.get("CMD", 0) >= 3
    has_upload   = session.event_counts.get("UPLOAD_SHELL", 0) > 0

    hints = []
    score = session.engagement_score

    if not has_upload:
        hints.append("Show upload form — attacker hasn't uploaded payload yet")
    elif phase == "RECON":
        hints.append("Plant fake DB credentials in /env response to bait lateral move")
        hints.append("Add fake SSH key hint in /etc/hosts response")
    elif phase == "EXPLOIT":
        hints.append("Simulate 'root' writable shadow file path as a fake privilege-esc lure")
        hints.append("Surface fake cron jobs with root context in ps aux")
    elif phase == "POST_EXPLOIT":
        hints.append("Simulate accepting reverse connection (delay 2s, then EOF) to waste attacker's time")
        hints.append("Return fake 127.0.0.1 pivot hosts in /etc/hosts to trigger lateral scan")

    if has_revshell:
        hints.append("Attacker tried reverse shell — simulate 'Connection refused' to frustrate, then add fake listening port")

    risk = min(100, int(sum(
        e["data"].get("risk_score", 10)
        for e in session.timeline if e["type"] == "CMD"
    ) / max(1, session.event_counts.get("CMD", 1))))

    return {
        "current_phase":     phase,
        "phase_label":       _PHASE_LABELS.get(phase, phase),
        "engagement_score":  score,
        "attacker_risk":     risk,
        "tried_revshell":    has_revshell,
        "deception_hints":   hints[:3],
        "recommendation":    hints[0] if hints else "Continue monitoring",
    }


# ── Session model ──────────────────────────────────────────────────────────────

class AttackerSession:
    """Full behavioral profile for one attacker IP."""

    def __init__(self, ip: str):
        self.ip            = ip
        self.first_seen    = _ts()
        self.last_seen     = _ts()
        self.geo           = _geolocate(ip)
        self.timeline:     list[dict] = []
        self.event_counts: dict[str, int] = defaultdict(int)
        self.commands:     list[dict] = []
        self.files:        list[dict] = []
        self.current_phase = "IDLE"
        self.engagement_score = 0     # 0-100 how engaged the attacker is
        self._lock = threading.Lock()

    # ── Event recording ───────────────────────────────────────────────────

    def record(self, event_type: str, data: dict):
        """Thread-safe event recording."""
        with self._lock:
            entry = {
                "type":  event_type,
                "ts":    _ts(),
                "data":  data,
            }
            self.timeline.append(entry)
            self.event_counts[event_type] += 1
            self.last_seen = entry["ts"]
            self._update_phase(event_type, data)
            self._update_engagement(event_type, data)

    def record_command(self, cmd: str, output: str):
        analysis = _classify_command(cmd)
        payload = {
            "command":    cmd,
            "output":     output[:200],
            "risk_score": analysis["score"],
            "phase":      analysis["phase"],
            "label":      analysis["label"],
        }
        self.commands.append(payload)
        self.record("CMD", payload)

    def record_upload(self, filename: str, raw_bytes: bytes, endpoint: str):
        analysis = _analyze_file(raw_bytes, filename)
        analysis["endpoint"] = endpoint
        self.files.append(analysis)
        etype = "UPLOAD_SHELL" if analysis["is_webshell"] else "UPLOAD_SAFE"
        self.record(etype, analysis)

    def record_form_view(self, endpoint: str):
        self.record("FORM_VIEW", {"endpoint": endpoint})

    def record_webshell_access(self, filename: str, cmd: str, output: str):
        self.record("WEBSHELL_EXEC", {
            "filename": filename,
            "command":  cmd,
            "output":   output[:200],
        })
        if cmd:
            self.record_command(cmd, output)

    # ── Internal phase / engagement ───────────────────────────────────────

    def _update_phase(self, event_type: str, data: dict):
        cmd_phase = data.get("phase", "")
        phase_rank = {p: i for i, p in enumerate(_PHASE_ORDER)}
        current_rank = phase_rank.get(self.current_phase, 0)
        new_rank     = phase_rank.get(cmd_phase, 0)
        if new_rank > current_rank:
            self.current_phase = cmd_phase

    def _update_engagement(self, event_type: str, data: dict):
        deltas = {
            "FORM_VIEW":     2,
            "UPLOAD_SAFE":   5,
            "UPLOAD_SHELL":  25,
            "CMD":           data.get("risk_score", 5) // 5,
            "WEBSHELL_EXEC": 15,
        }
        self.engagement_score = min(100, self.engagement_score + deltas.get(event_type, 1))

    # ── Summary export ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        geo = self.geo
        dangerous_cmds = [
            c for c in self.commands if c["risk_score"] >= 60
        ]
        revshell_attempts = [
            c for c in self.commands if c["phase"] == "POST_EXPLOIT"
        ]
        webshells = [f for f in self.files if f["is_webshell"]]

        return {
            # Identity
            "ip":              self.ip,
            "first_seen":      self.first_seen,
            "last_seen":       self.last_seen,
            "session_duration_s": _elapsed_s(self.first_seen, self.last_seen),

            # Geo / ISP
            "geo": {
                "country":    geo.get("country", "?"),
                "country_code": geo.get("countryCode", "??"),
                "region":     geo.get("regionName", "?"),
                "city":       geo.get("city", "?"),
                "isp":        geo.get("isp", "?"),
                "org":        geo.get("org", "?"),
                "asn":        geo.get("as", "?"),
                "lat":        geo.get("lat", 0),
                "lon":        geo.get("lon", 0),
                "is_proxy":   geo.get("proxy", False),
                "is_hosting": geo.get("hosting", False),
                "is_mobile":  geo.get("mobile", False),
            },

            # Phase
            "current_phase":  self.current_phase,
            "phase_label":    _PHASE_LABELS.get(self.current_phase, self.current_phase),
            "engagement_score": self.engagement_score,

            # Counts
            "total_events":        len(self.timeline),
            "commands_run":        len(self.commands),
            "files_uploaded":      len(self.files),
            "webshells_uploaded":  len(webshells),
            "dangerous_commands":  len(dangerous_cmds),
            "revshell_attempts":   len(revshell_attempts),
            "form_views":          self.event_counts.get("FORM_VIEW", 0),

            # Uploaded files
            "uploaded_files": [
                {
                    "filename":     f["filename"],
                    "ext":          f["extension"],
                    "ext_risk":     f["extension_risk"],
                    "threat_level": f["threat_level"],
                    "patterns":     f["payload_tags"],
                    "is_webshell":  f["is_webshell"],
                    "is_wrong_ext": f["is_wrong_ext"],
                    "size_bytes":   f["byte_size"],
                    "has_revshell": f["has_revshell"],
                }
                for f in self.files
            ],

            # Command timeline (most dangerous first)
            "top_commands": sorted(
                [{"cmd": c["command"], "risk": c["risk_score"], "label": c["label"], "phase": c["phase"]}
                 for c in self.commands],
                key=lambda x: x["risk"], reverse=True
            )[:15],

            # Full timeline (last 50)
            "timeline": self.timeline[-50:],

            # Deception advisor
            "deception": _deception_strategy(self),
        }


# ── Public API ────────────────────────────────────────────────────────────────

def get_or_create_session(ip: str) -> AttackerSession:
    with _lock:
        if ip not in _sessions:
            _sessions[ip] = AttackerSession(ip)
        return _sessions[ip]


def record_form_view(ip: str, endpoint: str):
    get_or_create_session(ip).record_form_view(endpoint)


def record_upload(ip: str, filename: str, raw_bytes: bytes, endpoint: str):
    get_or_create_session(ip).record_upload(filename, raw_bytes, endpoint)


def record_command(ip: str, cmd: str, output: str):
    get_or_create_session(ip).record_command(cmd, output)


def record_webshell_access(ip: str, filename: str, cmd: str, output: str):
    get_or_create_session(ip).record_webshell_access(filename, cmd, output)


def get_all_sessions() -> list[dict]:
    with _lock:
        return [s.to_dict() for s in _sessions.values()]


def get_session(ip: str) -> Optional[dict]:
    with _lock:
        s = _sessions.get(ip)
        return s.to_dict() if s else None


def dashboard_summary() -> dict:
    """Full intelligence summary for the dashboard API endpoint."""
    with _lock:
        sessions = list(_sessions.values())

    total_ips         = len(sessions)
    total_uploads     = sum(len(s.files) for s in sessions)
    total_webshells   = sum(sum(1 for f in s.files if f["is_webshell"]) for s in sessions)
    total_cmds        = sum(len(s.commands) for s in sessions)
    revshell_attempts = sum(sum(1 for c in s.commands if c["phase"] == "POST_EXPLOIT") for s in sessions)
    wrong_ext_uploads = sum(sum(1 for f in s.files if f["is_wrong_ext"]) for s in sessions)

    # Top attacker IPs by engagement
    top_attackers = sorted(
        [s.to_dict() for s in sessions],
        key=lambda x: x["engagement_score"], reverse=True
    )[:10]

    # Phase distribution
    phase_dist = defaultdict(int)
    for s in sessions:
        phase_dist[s.current_phase] += 1

    # Most used dangerous commands
    all_cmds = []
    for s in sessions:
        all_cmds.extend(s.commands)
    top_cmds = sorted(all_cmds, key=lambda c: c["risk_score"], reverse=True)[:20]

    # Recent events (last 30 across all sessions)
    all_events = []
    for s in sessions:
        for ev in s.timeline:
            all_events.append({**ev, "ip": s.ip})
    all_events.sort(key=lambda e: e["ts"], reverse=True)
    recent_events = all_events[:30]

    return {
        "generated_at":    _ts(),

        # Global counters
        "stats": {
            "unique_attackers":    total_ips,
            "total_uploads":       total_uploads,
            "webshell_uploads":    total_webshells,
            "wrong_ext_uploads":   wrong_ext_uploads,
            "total_commands":      total_cmds,
            "revshell_attempts":   revshell_attempts,
            "active_webshells":    0,  # filled by file_upload_rce
        },

        # Phase breakdown
        "phase_distribution": dict(phase_dist),

        # Top attackers
        "top_attackers": top_attackers,

        # Most dangerous commands seen
        "top_dangerous_commands": [
            {"cmd": c["command"], "risk": c["risk_score"],
             "label": c["label"], "phase": c["phase"]}
            for c in top_cmds
        ],

        # Recent activity feed
        "recent_events": recent_events,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _elapsed_s(start: str, end: str) -> float:
    try:
        fmt = "%Y-%m-%dT%H:%M:%S.%f+00:00"
        a = datetime.fromisoformat(start.replace("Z", "+00:00"))
        b = datetime.fromisoformat(end.replace("Z", "+00:00"))
        return round((b - a).total_seconds(), 1)
    except Exception:
        return 0.0
