local ngx = ngx
local shdict_scores = ngx.shared.risk_scores
local shdict_sessions = ngx.shared.ip_sessions

local uri = ngx.var.request_uri or ""
local method = ngx.req.get_method() or ""
local headers = ngx.req.get_headers() or {}
ngx.req.read_body()
local body = ngx.req.get_body_data() or ""
local ip = ngx.var.remote_addr or "unknown"
local now = ngx.time()

local function lower(s)
    if not s then
        return ""
    end
    return string.lower(s)
end

local function add_reason(reasons, delta, tag)
    if delta == 0 then
        return
    end
    table.insert(reasons, tag)
    return delta
end

local function contains(subject, pattern)
    subject = lower(subject)
    return subject:find(pattern, 1, true) ~= nil
end

local score = shdict_scores:get(ip) or 0
local reasons = {}
local uri_lower = lower(uri)
local body_lower = lower(body)
local ua_lower = lower(headers["User-Agent"] or "")

-- Detection rules
if contains(uri_lower, "../") or contains(uri_lower, "%2e%2e") or contains(body_lower, "../") or contains(body_lower, "%2e%2e") then
    score = score + add_reason(reasons, 25, "PATH_TRAVERSAL")
end
if contains(uri_lower, "${jndi:") or contains(body_lower, "${jndi:") then
    score = score + add_reason(reasons, 35, "LOG4SHELL")
end
if contains(uri_lower, "() { ") or contains(body_lower, "() { ") or contains(uri_lower, "(){") or contains(body_lower, "(){") then
    score = score + add_reason(reasons, 35, "SHELLSHOCK")
end
if contains(uri_lower, "/dev/tcp/") or contains(body_lower, "/dev/tcp/") or contains(uri_lower, "bash -i") or contains(body_lower, "bash -i") or contains(uri_lower, "nc -e") or contains(body_lower, "nc -e") then
    score = score + add_reason(reasons, 45, "REVSHELL")
end
if contains(uri_lower, "|") or contains(uri_lower, ";") or contains(uri_lower, "&&") or contains(uri_lower, "`") or contains(body_lower, "|") or contains(body_lower, ";") or contains(body_lower, "&&") or contains(body_lower, "`") then
    score = score + add_reason(reasons, 40, "CMD_INJECTION")
end
if contains(uri_lower, "select ") or contains(uri_lower, "union ") or contains(uri_lower, "insert ") or contains(uri_lower, "update ") or contains(uri_lower, "delete ") or contains(uri_lower, "drop ") or contains(uri_lower, "--") or contains(uri_lower, "/*") or contains(body_lower, "select ") or contains(body_lower, "union ") or contains(body_lower, "insert ") or contains(body_lower, "update ") or contains(body_lower, "delete ") or contains(body_lower, "drop ") or contains(body_lower, "--") or contains(body_lower, "/*") then
    score = score + add_reason(reasons, 20, "SQLI")
end
if contains(uri_lower, "<script>") or contains(uri_lower, "<img src=") or contains(uri_lower, "javascript:") or contains(body_lower, "<script>") or contains(body_lower, "<img src=") or contains(body_lower, "javascript:") then
    score = score + add_reason(reasons, 15, "XSS")
end
if contains(ua_lower, "nmap") or contains(ua_lower, "sqlmap") or contains(ua_lower, "nikto") or contains(ua_lower, "gobuster") or contains(ua_lower, "ffuf") or contains(ua_lower, "dirbuster") or contains(ua_lower, "masscan") or contains(ua_lower, "zgrab") then
    score = score + add_reason(reasons, 25, "SCANNER_UA")
end
if contains(uri_lower, "/admin") or contains(uri_lower, "/wp-admin") or contains(uri_lower, "/.env") or contains(uri_lower, "/.git") or contains(uri_lower, "/config") or contains(uri_lower, "/backup") or contains(uri_lower, "/console") or contains(uri_lower, "/shell") then
    score = score + add_reason(reasons, 20, "ADMIN_ENUM")
end
if contains(uri_lower, "/nmaplowercheck") or contains(uri_lower, "/HNAP1") or contains(uri_lower, "/sdk") or contains(uri_lower, "/_vti_bin") then
    score = score + add_reason(reasons, 15, "NSE_PROBE")
end
if contains(uri_lower, "/nmap") or contains(uri_lower, "/nmaplowercheck") then
    score = score + add_reason(reasons, 25, "NMAP_PROBE")
end
if method == "OPTIONS" then
    score = score + add_reason(reasons, 5, "OPTIONS_PROBE")
end
if headers["User-Agent"] == nil or headers["User-Agent"] == "" then
    score = score + add_reason(reasons, 5, "NO_UA")
end
if method == "POST" and (contains(uri_lower, ".php") or contains(uri_lower, ".jsp") or contains(uri_lower, ".aspx") or contains(uri_lower, ".sh")) then
    score = score + add_reason(reasons, 40, "WEBSHELL_UPLOAD")
end

local last_clean_key = ip .. ":last_clean"
local last_clean = tonumber(shdict_sessions:get(last_clean_key))

if #reasons == 0 then
    if last_clean then
        local elapsed = now - last_clean
        local decay = math.floor(elapsed / 600) * 5
        if decay > 0 then
            score = score - decay
            if score < 0 then
                score = 0
            end
        end
    end
    shdict_sessions:set(last_clean_key, tostring(now))
end

-- ── Per-request cap: no single request can contribute more than 80 pts ──
local request_delta = score - (shdict_scores:get(ip .. ":prev") or 0)
if request_delta > 80 then
    score = (shdict_scores:get(ip .. ":prev") or 0) + 80
end
shdict_scores:set(ip .. ":prev", score, 3600)

if score < 0 then
    score = 0
end
shdict_scores:set(ip, score, 3600)
ngx.var.risk_score = tostring(score)

local reason_text = "none"
if #reasons > 0 then
    reason_text = table.concat(reasons, ",")
    ngx.log(ngx.WARN, string.format("[RISK] ip=%s score=%s reasons=%s uri=%s", ip, score, reason_text, uri))
end

if shdict_sessions:get(ip) == "honeypot" then
    return ngx.exec("@honeypot")
end

if score >= 150 then
    shdict_sessions:set(ip, "honeypot", 86400)
    ngx.log(ngx.CRIT, string.format("[REDIRECT] ip=%s score=%s → HONEYPOT", ip, score))
    return ngx.exec("@honeypot")
end

return
