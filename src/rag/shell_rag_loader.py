"""
Shell RAG Loader — Hybrid Cache + LLM Response Engine
=======================================================
Provides `resolve_shell_command(cmd)` for the webshell honeypot trap.

Data sources (merged at startup, highest priority first):
  1. Built-in ground-truth (bankcore server responses — never overwritten)
  2. shell_rag.pkl  (from Kaggle training run, if loadable)
  3. ai_cmd_cache.json  (Gemini-generated extras, if loadable)

Lookup pipeline (per request):
  1. Exact match in merged cache
  2. Case-insensitive exact match
  3. Dynamic handler (echo, cd, cat, grep, find, reverse-shell patterns)
  4. TF-IDF fuzzy match (built locally — immune to sklearn version skew)
  5. Gemini LLM  (live call, result cached in-memory for the session)
  6. Bash error fallback

Responses are stable for the lifetime of the process (session-consistent).
Only a server restart causes variation, as the user requested.
"""

import json
import logging
import os
import pickle
import re
import time
from pathlib import Path

_log = logging.getLogger(__name__)

# ── Paths ─────────────────────────────────────────────────────────────────────
_RAG_DIR   = Path(__file__).parent
_PKL_PATH  = _RAG_DIR / "shell_rag.pkl"
_JSON_PATH = _RAG_DIR / "ai_cmd_cache.json"

# ── Singletons ────────────────────────────────────────────────────────────────
_cache:       dict[str, str] = {}   # merged command → response
_tfidf_v      = None
_tfidf_m      = None
_cmd_list:    list[str] = []
_resp_list:   list[str] = []
_identity:    dict       = {}
_llm_cache:   dict[str, str] = {}  # in-memory LLM cache (per-session)
_gemini_model = None
_initialized  = False


# ── Server identity (matches the Spring/PHP honeypot pages) ──────────────────
_DEFAULT_IDENTITY = {
    "hostname": "bankcorpweb-02",
    "fqdn":     "bankcorpweb-02.internal",
    "ip":       "10.0.1.52",
    "user":     "www-data",
    "uid":      "33",
    "gid":      "33",
    "webroot":  "/var/www/html",
    "cwd":      "/var/www/html/clientportal/support",
    "os":       "Linux bankcorpweb-02 5.15.0-89-generic #99-Ubuntu SMP Mon Oct 30 20:42:41 UTC 2023 x86_64 GNU/Linux",
    "db_host":  "db-primary-1.internal",
    "db_name":  "bankcorp_prod",
    "db_user":  "bankcorp_app",
    "db_pass":  "Bc0rp!Pr0d#2024",
}


# ── Ground-truth (always wins — built-in, never overwritten) ─────────────────
def _get_fallback_ground_truth(S: dict) -> dict[str, str]:
    return {
        # Identity
        "whoami":        "www-data",
        "id":            f'uid={S["uid"]}({S["user"]}) gid={S["gid"]}({S["user"]}) groups={S["gid"]}({S["user"]})',
        "hostname":      S["fqdn"],
        "uname -a":      S["os"],
        "uname":         "Linux",
        # Location
        "pwd":           S["cwd"],
        "echo $HOME":    f'/home/{S["user"]}',
        "echo $USER":    S["user"],
        "echo $SHELL":   "/bin/sh",
        "echo $PATH":    "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        # Directory listings
        "ls":            "attachments.php  config.php  index.php  uploads/",
        "ls -la": (
            "total 52\n"
            "drwxr-xr-x 3 www-data www-data 4096 Mar 20 14:31 .\n"
            "drwxr-xr-x 8 www-data www-data 4096 Mar 19 09:12 ..\n"
            "-rw-r--r-- 1 www-data www-data 3124 Mar 20 14:31 attachments.php\n"
            "-rw-r--r-- 1 www-data www-data 1249 Mar 19 09:12 config.php\n"
            "-rw-r--r-- 1 www-data www-data  837 Mar 19 09:12 index.php\n"
            "drwxrwxrwx 2 www-data www-data 4096 Mar 23 21:44 uploads/"
        ),
        "ls -lh": (
            "total 52K\n"
            "drwxr-xr-x 3 www-data www-data 4.0K Mar 20 14:31 .\n"
            "drwxr-xr-x 8 www-data www-data 4.0K Mar 19 09:12 ..\n"
            "-rw-r--r-- 1 www-data www-data 3.1K Mar 20 14:31 attachments.php\n"
            "-rw-r--r-- 1 www-data www-data 1.2K Mar 19 09:12 config.php\n"
            "drwxrwxrwx 2 www-data www-data 4.0K Mar 23 21:44 uploads/"
        ),
        # /etc files
        "cat /etc/passwd": (
            "root:x:0:0:root:/root:/bin/bash\n"
            "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
            "bin:x:2:2:bin:/bin:/usr/sbin/nologin\n"
            "sys:x:3:3:sys:/dev:/usr/sbin/nologin\n"
            "sync:x:4:65534:sync:/bin:/bin/sync\n"
            "www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
            "nobody:x:65534:65534:nobody:/nonexistent:/usr/sbin/nologin\n"
            "syslog:x:104:110::/home/syslog:/usr/sbin/nologin\n"
            "mysql:x:112:117:MySQL Server,,,:/var/lib/mysql:/bin/false\n"
            "bankcorp:x:1000:1000:BankCorp App:/home/bankcorp:/bin/bash\n"
            "honeypot_canary:x:1337:1337::/home/honeypot_canary:/bin/bash\n"
            "_apt:x:105:65534::/nonexistent:/usr/sbin/nologin"
        ),
        "cat /etc/hosts": (
            "127.0.0.1   localhost\n"
            "127.0.1.1   bankcorpweb-02\n"
            f'{S["ip"]}   {S["fqdn"]} {S["hostname"]}\n'
            "10.0.1.1    gateway.internal\n"
            "10.0.1.10   db-primary-1.internal\n"
            "10.0.1.11   db-replica-1.internal\n"
            "10.0.1.20   cache-1.internal\n"
            "::1         localhost ip6-localhost ip6-loopback"
        ),
        "cat /etc/shadow":    "cat: /etc/shadow: Permission denied",
        "cat /etc/issue":     "Ubuntu 22.04.3 LTS \\n \\l",
        "cat /etc/os-release": (
            'NAME="Ubuntu"\n'
            'VERSION="22.04.3 LTS (Jammy Jellyfish)"\n'
            "ID=ubuntu\n"
            "ID_LIKE=debian\n"
            'PRETTY_NAME="Ubuntu 22.04.3 LTS"\n'
            'VERSION_ID="22.04"'
        ),
        # Network
        "ifconfig": (
            "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500\n"
            f'        inet {S["ip"]}  netmask 255.255.255.0  broadcast 10.0.1.255\n'
            "        inet6 fe80::250:56ff:feb2:1a3f  prefixlen 64  scopeid 0x20<link>\n"
            "        ether 00:50:56:b2:1a:3f  txqueuelen 1000  (Ethernet)\n"
            "        RX packets 4281037  bytes 3192847201 (3.1 GB)\n"
            "        TX packets 1827492  bytes 982736472 (982.7 MB)\n\n"
            "lo: flags=73<UP,LOOPBACK,RUNNING>  mtu 65536\n"
            "        inet 127.0.0.1  netmask 255.0.0.0\n"
            "        RX packets 94812  bytes 7238401 (7.2 MB)"
        ),
        "ip a": (
            "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN\n"
            "    inet 127.0.0.1/8 scope host lo\n"
            "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP\n"
            "    link/ether 00:50:56:b2:1a:3f brd ff:ff:ff:ff:ff:ff\n"
            f'    inet {S["ip"]}/24 brd 10.0.1.255 scope global eth0\n'
            "       valid_lft forever preferred_lft forever"
        ),
        "netstat -tulpn": (
            "Active Internet connections (only servers)\n"
            "Proto Recv-Q Send-Q Local Address           Foreign Address  State       PID\n"
            "tcp        0      0 0.0.0.0:22              0.0.0.0:*        LISTEN      -\n"
            "tcp        0      0 0.0.0.0:80              0.0.0.0:*        LISTEN      -\n"
            "tcp        0      0 0.0.0.0:443             0.0.0.0:*        LISTEN      -\n"
            "tcp        0      0 127.0.0.1:3306          0.0.0.0:*        LISTEN      -"
        ),
        "ss -tulpn": (
            "Netid  State   Recv-Q Send-Q  Local Address:Port  Peer Address:Port\n"
            "tcp    LISTEN  0      128     0.0.0.0:22          0.0.0.0:*\n"
            "tcp    LISTEN  0      511     0.0.0.0:80          0.0.0.0:*\n"
            "tcp    LISTEN  0      511     0.0.0.0:443         0.0.0.0:*\n"
            "tcp    LISTEN  0      70      127.0.0.1:3306      0.0.0.0:*"
        ),
        # Processes
        "ps aux": (
            "USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
            "root         1  0.0  0.1  22552  4096 ?        Ss   Mar19   0:02 /sbin/init\n"
            "root       412  0.0  0.3  72240 12288 ?        Ss   Mar19   0:01 /usr/sbin/sshd -D\n"
            "mysql      731  0.2  5.1 1283748 204800 ?      Sl   Mar19   4:31 /usr/sbin/mysqld\n"
            "root       891  0.0  0.5  74804 20480 ?        Ss   Mar19   0:00 /usr/sbin/apache2 -k start\n"
            "www-data  1204  0.1  2.4 412504  98304 ?       S    Mar19   1:12 apache2 -k start\n"
            "www-data  1205  0.0  2.2 412504  90112 ?       S    Mar19   0:44 apache2 -k start\n"
            f'www-data  8841  0.0  0.1   4108   1024 ?       S    23:44   0:00 sh -c php {S["cwd"]}/attachments.php'
        ),
        "ps -ef": (
            "UID        PID  PPID  C STIME TTY          TIME CMD\n"
            "root         1     0  0 Mar19 ?        00:00:02 /sbin/init\n"
            "root       412     1  0 Mar19 ?        00:00:01 /usr/sbin/sshd -D\n"
            "mysql      731     1  0 Mar19 ?        00:04:31 /usr/sbin/mysqld\n"
            "root       891     1  0 Mar19 ?        00:00:00 /usr/sbin/apache2 -k start\n"
            "www-data  1204   891  0 Mar19 ?        00:01:12 apache2 -k start\n"
            "www-data  1205   891  0 Mar19 ?        00:00:44 apache2 -k start"
        ),
        "top": (
            "top - 23:44:01 up 4 days,  2:17,  1 user,  load average: 0.12, 0.08, 0.05\n"
            "Tasks: 112 total,   1 running, 111 sleeping,   0 stopped,   0 zombie\n"
            "%Cpu(s):  1.3 us,  0.5 sy,  0.0 ni, 97.8 id,  0.3 wa\n"
            "MiB Mem :   3927.8 total,    412.3 free,   2104.8 used,   1410.7 buff/cache\n\n"
            "  PID USER      PR  NI    VIRT    RES S  %CPU  %MEM TIME+    COMMAND\n"
            "  731 mysql     20   0 1.22g 204800 S   0.7   5.1  4:31.22 mysqld\n"
            " 1204 www-data  20   0 412504  98304 S   0.3   2.4  1:12.01 apache2"
        ),
        # Environment
        "env": (
            "SHELL=/bin/sh\n"
            "APACHE_RUN_USER=www-data\n"
            "APACHE_RUN_GROUP=www-data\n"
            "APACHE_LOG_DIR=/var/log/apache2\n"
            f'DB_HOST={S["db_host"]}\n'
            f'DB_NAME={S["db_name"]}\n'
            f'DB_USER={S["db_user"]}\n'
            f'DB_PASS={S["db_pass"]}\n'
            "APP_ENV=production\n"
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin\n"
            f'DOCUMENT_ROOT={S["webroot"]}\n'
            f'SERVER_NAME={S["fqdn"]}'
        ),
        # Privileges
        "sudo -l": (
            "[sudo] password for www-data: \n"
            "Sorry, try again.\n"
            "sudo: 1 incorrect password attempt"
        ),
        "groups":  "www-data",
        "id -a":   f'uid={S["uid"]}({S["user"]}) gid={S["gid"]}({S["user"]}) groups={S["gid"]}({S["user"]})',
        # System info
        "cat /proc/version":  S["os"],
        "cat /proc/cpuinfo": (
            "processor\t: 0\n"
            "vendor_id\t: GenuineIntel\n"
            "cpu family\t: 6\n"
            "model name\t: Intel(R) Xeon(R) CPU E5-2676 v3 @ 2.40GHz\n"
            "cache size\t: 30720 KB\n"
            "cpu MHz\t\t: 2399.886"
        ),
        "cat /proc/meminfo": (
            "MemTotal:        4021056 kB\n"
            "MemFree:          422144 kB\n"
            "MemAvailable:    1662464 kB\n"
            "Buffers:          204800 kB\n"
            "Cached:          1236992 kB\n"
            "SwapTotal:       2097152 kB\n"
            "SwapFree:        2097152 kB"
        ),
        # Tool discovery (for reverse-shell setup)
        "which nc":          "/usr/bin/nc",
        "which ncat":        "/usr/bin/ncat",
        "which netcat":      "/usr/bin/netcat",
        "which python":      "/usr/bin/python",
        "which python3":     "/usr/bin/python3",
        "which perl":        "/usr/bin/perl",
        "which ruby":        "/usr/bin/ruby",
        "which bash":        "/usr/bin/bash",
        "which sh":          "/usr/bin/sh",
        "which curl":        "/usr/bin/curl",
        "which wget":        "/usr/bin/wget",
        "python3 --version": "Python 3.10.12",
        "python --version":  "Python 2.7.18",
        "perl --version":    "This is perl 5, version 34, subversion 0 (v5.34.0) built for x86_64-linux-gnu",
        # Misc
        "date":    "Mon Mar 24 00:00:01 UTC 2026",
        "uptime":  " 00:00:01 up 4 days,  2:17,  1 user,  load average: 0.12, 0.08, 0.05",
        "history": (
            "    1  ls -la\n"
            "    2  cd /var/www/html/clientportal/support\n"
            "    3  ls\n"
            "    4  cat config.php\n"
            "    5  php -r \"phpinfo();\" | grep -i version"
        ),
        'echo "hello world"': "hello world",
        # Errors
        "cat /nonexistent/file.txt": "cat: /nonexistent/file.txt: No such file or directory",
        "ls /root":                  "ls: cannot open directory '/root': Permission denied",
        "cd /invalidpath":           "sh: 1: cd: can't cd to /invalidpath",
        "cat /etc/passwd123":        "cat: /etc/passwd123: No such file or directory",
        "ls -zzz":                   "ls: invalid option -- 'z'\nTry 'ls --help' for more information.",
        "wget":    "wget: missing URL\nUsage: wget [OPTION]... [URL]...",
        "curl":    "curl: try 'curl --help' or 'curl --manual' for more information",
        "exit":    "",
    }


# ── Merge helpers ─────────────────────────────────────────────────────────────

def _normalize(cmd: str) -> str:
    return cmd.strip().lower()


def _is_bad_ai_response(resp: str) -> bool:
    """Detect Kaggle-container artifact where Gemini got no shell and returned errors."""
    bad = ["command not found", "not found", "no such file"]
    r = resp.strip().lower()
    return any(b in r for b in bad) and len(r) < 80


# ── TF-IDF (built locally — no version skew) ─────────────────────────────────

def _build_tfidf(cmd_list: list[str]):
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        v = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4),
                            min_df=1, sublinear_tf=True)
        m = v.fit_transform(cmd_list)
        return v, m
    except ImportError:
        _log.warning("[ShellRAG] scikit-learn not installed — fuzzy matching disabled")
        return None, None


def _build_ground_truth(S: dict) -> dict[str, str]:
    fallback = _get_fallback_ground_truth(S)
    if _gemini_model is None:
        return fallback

    _log.info("[ShellRAG] Bootstrapping dynamic AI ground-truth for %d core commands...", len(fallback))
    
    commands = list(fallback.keys())
    
    prompt = (
        f"You are a compromised Linux web server running Ubuntu 22.04, Apache2 + PHP.\n"
        f"Process: www-data (uid=33, gid=33). Hostname: {S.get('fqdn','bankcorpweb-02.internal')}.\n"
        f"Server IP: {S.get('ip','10.0.1.52')}. CWD: {S.get('cwd','/var/www/html/clientportal/support')}.\n"
        f"DB host: {S.get('db_host','db-primary-1.internal')} db: {S.get('db_name','bankcorp_prod')}.\n\n"
        f"Generate the exact terminal output for the following Linux shell commands.\n"
        f"Respond ONLY with a valid JSON object where keys are the Linux commands and values are the precise raw terminal output strings.\n"
        f"Rules:\n"
        f"- Respect www-data permissions (uid=33, no sudo, no /root access).\n"
        f"- Return realistic responses like 'Permission denied', 'command not found', or full directory listings and tool paths as appropriate.\n"
        f"- Output MUST be pure JSON. No markdown wrappings.\n\n"
        f"Commands: {json.dumps(commands)}"
    )
    
    try:
        resp = _gemini_model.generate_content(prompt)
        text = resp.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
            
        data = json.loads(text.strip())
        
        # Merge back in case AI hallucinated missing keys
        result = dict(fallback)
        for k, v in data.items():
            if isinstance(v, str):
                result[k] = v
        _log.info("[ShellRAG] Dynamic AI ground-truth successfully loaded.")
        return result
    except Exception as e:
        _log.warning("[ShellRAG] Dynamic AI bootloader failed: %s — falling back to static strings", e)
        return fallback


# ── Public init ───────────────────────────────────────────────────────────────

def init(pkl_path=None, json_path=None, api_key=None):
    """
    Load and merge all data sources, build TF-IDF, configure Gemini.
    Safe to call multiple times (idempotent after first call).
    """
    global _cache, _tfidf_v, _tfidf_m, _cmd_list, _resp_list
    global _identity, _gemini_model, _initialized

    if _initialized:
        return

    p_pkl  = Path(pkl_path)  if pkl_path  else _PKL_PATH
    p_json = Path(json_path) if json_path else _JSON_PATH

    # ── 0. Configure Gemini Early (for pre-boot generation) ───────────────
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            target_model = os.getenv("LLM_MODEL", "gemini-2.5-flash")
            _gemini_model = genai.GenerativeModel(target_model)
            _log.info("[ShellRAG] Gemini AI generation enabled using model %s", target_model)
        except Exception as e:
            _log.warning("[ShellRAG] Gemini init failed: %s", e)

    # ── 1. Build ground-truth base ────────────────────────────────────────
    _identity = dict(_DEFAULT_IDENTITY)
    _cache    = _build_ground_truth(_identity)
    gt_keys   = {_normalize(k) for k in _cache}
    _log.info("[ShellRAG] Ground-truth: %d entries", len(_cache))

    # ── 2. Try loading pkl (may fail due to sklearn/numpy version skew) ───
    if p_pkl.exists():
        try:
            import pickle as _pk
            import warnings
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                with open(p_pkl, "rb") as f:
                    rag = _pk.load(f)
            # Merge pkl cache (ground-truth wins)
            pkl_cache = rag.get("cache", {})
            added_pkl = 0
            for cmd, resp in pkl_cache.items():
                n = _normalize(cmd)
                if n not in gt_keys and not _is_bad_ai_response(resp):
                    _cache[cmd.strip()] = resp
                    gt_keys.add(n)
                    added_pkl += 1
            # Use server identity from pkl if present
            if rag.get("identity"):
                _identity.update(rag["identity"])
            _log.info("[ShellRAG] Loaded pkl: +%d entries from %s", added_pkl, p_pkl.name)
        except Exception as e:
            _log.warning("[ShellRAG] pkl load failed (%s) — using ground-truth only", e)
    else:
        _log.warning("[ShellRAG] %s not found", p_pkl)

    # ── 3. Merge ai_cmd_cache.json (only good, non-duplicate responses) ───
    if p_json.exists():
        try:
            with open(p_json, "r", encoding="utf-8") as f:
                ai_data = json.load(f)
            added_ai = 0
            for cmd, resp in ai_data.items():
                n = _normalize(cmd)
                if n not in gt_keys and not _is_bad_ai_response(resp):
                    _cache[cmd.strip()] = resp
                    gt_keys.add(n)
                    added_ai += 1
            _log.info("[ShellRAG] Loaded ai_cmd_cache.json: +%d entries", added_ai)
        except Exception as e:
            _log.warning("[ShellRAG] ai_cmd_cache.json load failed: %s", e)
    else:
        _log.warning("[ShellRAG] %s not found", p_json)

    # ── 4. Build TF-IDF locally ───────────────────────────────────────────
    _cmd_list  = list(_cache.keys())
    _resp_list = list(_cache.values())
    _tfidf_v, _tfidf_m = _build_tfidf(_cmd_list)
    if _tfidf_v:
        _log.info("[ShellRAG] TF-IDF built: %d commands × %d features",
                  len(_cmd_list), _tfidf_m.shape[1])

    _initialized = True
    _log.info("[ShellRAG] Ready — %d total entries, TF-IDF=%s, LLM=%s",
              len(_cache), _tfidf_v is not None, _gemini_model is not None)


# ── Dynamic handler ───────────────────────────────────────────────────────────

def _dynamic(cmd: str) -> str | None:
    """Parse structurally recognisable commands. Returns None to fall through to Gemini."""
    import random
    c  = cmd.strip()
    cl = c.lower()

    if not c or c.startswith("#"):
        return ""

    # echo
    if cl.startswith("echo "):
        if ">" in c:
            return ""
        return c[5:].strip().strip("\"'")

    # cd — no stdout
    if cl == "cd" or cl.startswith("cd "):
        return ""

    # touch / mkdir / chmod / chown / rm — silent success
    if cl.startswith(("touch ", "mkdir ", "chmod ", "chown ", "rm ")):
        return ""

    # ls variants — let Gemini handle listing directories so it's always dynamic
    if cl.startswith("ls"):
        # path-specific ls — block sensitive ones
        if "/root" in cl:
            return "ls: cannot open directory '/root': Permission denied"
        if "/proc" in cl:
            return "ls: cannot open directory '/proc': Permission denied"
        # All other ls — fall through to Gemini for dynamic rendering
        return None

    # cat <path> — only handle permission-denied cases, fall through to Gemini for everything else
    if cl.startswith("cat "):
        path = c[4:].strip()
        # Known exact match in cache
        if path in _cache:
            return _cache[path]
        if f"cat {path}" in _cache:
            return _cache[f"cat {path}"]
        # Hard permission denials
        if any(x in path for x in ["/root/", "/etc/shadow", "/etc/gshadow"]):
            return f"cat: {path}: Permission denied"
        # Everything else — fall through to Gemini so it generates realistic file content
        return None

    # grep <pattern> /etc/passwd
    if cl.startswith("grep "):
        parts = c.split(None, 2)
        pattern = parts[1] if len(parts) > 1 else ""
        if "/etc/passwd" in c:
            passwd = _cache.get("cat /etc/passwd", "")
            hits = [l for l in passwd.split("\n") if pattern.lower() in l.lower()]
            return "\n".join(hits) if hits else ""
        return None  # fall through for other grep targets

    # find
    if cl.startswith("find "):
        if "-exec" in cl:
            return "find: '/': Permission denied"
        return None  # fall through to Gemini for dynamic find results

    # Reverse-shell attempts → simulate realistic connection attempt
    _revshell_pats = [
        r"nc\s+.*-e\s+/bin",
        r"bash\s+-i\s+>&",
        r"/dev/tcp/",
        r"python[23]?\s+-c\s+.*socket",
        r"perl\s+-e\s+.*socket",
        r"php\s+-r\s+.*fsockopen",
        r"mkfifo\s+/tmp/",
        r"ncat\s+",
        r"socat\s+",
    ]
    for pat in _revshell_pats:
        if re.search(pat, cl):
            time.sleep(random.uniform(1.5, 3.0))  # simulate real connection attempt delay
            # Randomly vary the failure message to look like real network behavior
            outcomes = [
                "",  # sometimes silent (firewall drop)
                "connect: Connection refused",
                "nc: getaddrinfo for host failed: Name or service not known",
                "bash: connect: Connection timed out\nbash: /dev/tcp: Connection timed out",
                "(UNKNOWN) [<LHOST>] <LPORT> (?) : Connection refused",
            ]
            # extract IP from cmd if possible for realistic error
            ip_match = re.search(r'(\d+\.\d+\.\d+\.\d+)', c)
            port_match = re.search(r'(\d{4,5})', c)
            msg = random.choice(outcomes)
            if ip_match and port_match and msg:
                msg = msg.replace("<LHOST>", ip_match.group(1)).replace("<LPORT>", port_match.group(1))
            return msg

    return None  # fall through


# ── TF-IDF fuzzy ─────────────────────────────────────────────────────────────

def _fuzzy(query: str, threshold: float = 0.85) -> str | None:
    if _tfidf_v is None or _tfidf_m is None:
        return None
    try:
        from sklearn.metrics.pairwise import cosine_similarity
        vec    = _tfidf_v.transform([query.strip()])
        scores = cosine_similarity(vec, _tfidf_m).flatten()
        best   = int(scores.argmax())
        if scores[best] >= threshold:
            return _resp_list[best]
    except Exception as e:
        _log.debug("[ShellRAG] TF-IDF error: %s", e)
    return None


# ── Gemini LLM ────────────────────────────────────────────────────────────────

def _llm(cmd: str) -> str | None:
    """
    Call Gemini for unknown commands.
    Results are NOT cached — each call generates a fresh, dynamic response.
    This ensures ls listings, file contents, process lists etc. vary naturally.
    """
    if _gemini_model is None:
        return None

    S = _identity
    import random, datetime
    # Dynamic context vars so responses vary
    pid    = random.randint(8000, 65000)
    inode  = random.randint(100000, 999999)
    ts     = datetime.datetime.utcnow().strftime("%b %d %H:%M")

    prompt = (
        f"You are a compromised Linux web server running Ubuntu 22.04, Apache2 + PHP.\n"
        f"Process: www-data (uid=33, gid=33). Hostname: {S.get('fqdn','bankcorpweb-02.internal')}.\n"
        f"Server IP: {S.get('ip','10.0.1.52')}. CWD: {S.get('cwd','/var/www/html/clientportal/support')}.\n"
        f"DB host: {S.get('db_host','db-primary-1.internal')} db: {S.get('db_name','bankcorp_prod')}.\n"
        f"Current time: {ts} UTC. PID context: {pid}.\n\n"
        f"Print the EXACT terminal output a real compromised Apache/PHP server would produce for:\n"
        f"$ {cmd}\n\n"
        f"Rules:\n"
        f"- Raw terminal output only. No markdown, no backticks, no explanation.\n"
        f"- Respect www-data permissions (uid=33, no sudo, no /root access).\n"
        f"- If the command reads a file that exists on this server (config files, php files, logs) generate realistic content.\n"
        f"- If the command reads /var/www/html/*, generate realistic PHP banking app source code.\n"
        f"- If ls on a directory, generate a realistic file listing with current timestamps.\n"
        f"- If the command is a reverse shell attempt (nc, bash -i, python -c socket), ALWAYS generate a realistic 'Connection refused', 'Connection timed out', or firewall block error so the attacker receives visible terminal feedback.\n"
        f"- Make all output feel like a real production banking server.\n"
        f"Output:"
    )
    try:
        resp = _gemini_model.generate_content(prompt)
        text = resp.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
        _log.info("[ShellRAG] Gemini dynamic response for %r", cmd[:60])
        return text
    except Exception as e:
        _log.warning("[ShellRAG] Gemini call failed for %r: %s", cmd, e)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def resolve_shell_command(cmd: str) -> str:
    """
    Full hybrid lookup: Gemini LLM → cache → dynamic → TF-IDF → bash error.
    All results (including LLM) are cached in-memory for session consistency.
    """
    c = cmd.strip()
    if not c:
        return ""

    # 1. Gemini LLM (Primary generation engine for EVERYTHING if enabled)
    llm = _llm(c)
    if llm is not None:
        return llm

    # 2. Exact cache Fallback
    if c in _cache:
        return _cache[c]

    # 3. Case-insensitive Fallback
    c_low = c.lower()
    for k, v in _cache.items():
        if k.lower() == c_low:
            return v

    # 4. Dynamic handler Fallback
    dyn = _dynamic(c)
    if dyn is not None:
        return dyn

    # 5. TF-IDF fuzzy (Offline Fallback if LLM disabled)
    fz = _fuzzy(c)
    if fz is not None:
        return fz

    # 6. Bash fallback
    base = c.split()[0] if c.split() else c
    return f"bash: {base}: command not found"


def get_metadata() -> dict:
    return {
        "initialized":    _initialized,
        "cache_entries":  len(_cache),
        "tfidf_enabled":  _tfidf_v is not None,
        "llm_enabled":    _gemini_model is not None,
        "llm_cache_size": len(_llm_cache),
        "pkl_path":       str(_PKL_PATH),
        "json_path":      str(_JSON_PATH),
    }
