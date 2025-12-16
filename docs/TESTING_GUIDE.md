# Testing Guide for Dynamic API Honeypot

Comprehensive testing scenarios and validation steps.

## Quick Tests

### 1. Basic Functionality Test

```bash
# Start honeypot
python api_honeypot.py

# In new terminal:
python test_api_honeypot.py
```

Expected output: `✅ ALL TESTS PASSED!`

### 2. Maze Navigation Test

```bash
python demo_maze_attack.py
```

This simulates a complete attacker journey through all 8 levels.

## Manual Testing Scenarios

### Scenario 1: Unauthenticated Access

```bash
# Should return 401
curl http://localhost:8001/api/v1/users
curl http://localhost:8001/api/v1/products
curl http://localhost:8001/api/v2/admin/settings
```

**Expected:**
- Status: 401 Unauthorized
- Response includes `"hint"` field pointing to login

### Scenario 2: Authentication Flow

```bash
# Login
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"hacker","password":"test"}'

# Copy the token from response, then:
curl http://localhost:8001/api/v1/users \
  -H "Authorization: Bearer <TOKEN>"
```

**Expected:**
- Login returns 200 with token
- Users endpoint now returns data (not 401)

### Scenario 3: Privilege Elevation

```bash
# With user token, try admin endpoint
curl http://localhost:8001/api/v2/admin/users \
  -H "Authorization: Bearer <USER_TOKEN>"

# Should get 403, then elevate:
curl -X POST http://localhost:8001/api/v1/auth/elevate \
  -H "Authorization: Bearer <USER_TOKEN>"

# Use admin token
curl http://localhost:8001/api/v2/admin/users \
  -H "Authorization: Bearer <ADMIN_TOKEN>"
```

**Expected:**
- First try: 403 Forbidden with elevation hint
- After elevation: 200 with "sensitive" data

### Scenario 4: Dynamic Endpoint Generation

```bash
# Hit random endpoint
curl http://localhost:8001/api/v99/random/endpoint

# Hit it again
curl http://localhost:8001/api/v99/random/endpoint
```

**Expected:**
- First request: Generates new endpoint
- Second request: Returns same response (persistence)
- Console shows `✨ [GEMINI+MAZE]` tag

### Scenario 5: Breadcrumb Following

```bash
# Get endpoint with breadcrumbs
curl http://localhost:8001/api/v1/products

# Look for "_links" or "_meta.hint" in response
# Follow suggested endpoint
```

**Expected:**
- Response includes hints to related endpoints
- Can navigate the maze by following hints

### Scenario 6: File Download

```bash
# Download bait file
curl http://localhost:8001/api/download/report.pdf -o test.pdf

# Check if file exists
ls -lh test.pdf
```

**Expected:**
- File downloads successfully
- Honeypot logs download event
- Beacon ID embedded in file

## Verification Steps

### Check Logs

```bash
cat log_files/api_audit.log
```

Look for:
```json
{"event":"api_request","ip":"127.0.0.1","method":"GET","path":"/api/v1/users"}
```

### Check Database

```bash
cat databases/api_state.json | python -m json.tool
```

Should show:
- `endpoints` table with generated paths
- `objects` table with created users
- `beacons` table with file downloads

### Check Statistics

```bash
curl http://localhost:8001/health
```

Returns:
```json
{
  "status": "healthy",
  "stats": {
    "total_endpoints": 15,
    "total_objects": 5,
    "total_beacons": 2
  }
}
```

## Performance Tests

### Load Test

```bash
# Hit 50 different endpoints
for i in {1..50}; do
  curl http://localhost:8001/api/test/endpoint_$i &
done
wait
```

**Expected:**
- All requests complete
- No crashes
- All endpoints saved to database

### Gemini Rate Limiting

```bash
# Rapid requests
for i in {1..100}; do
  curl http://localhost:8001/api/unique/path_$i
done
```

**Expected:**
- First ~60 use Gemini
- After quota: Falls back to templates
- No errors or crashes

## Integration Tests

### Swagger UI

Visit: http://localhost:8001/docs

**Expected:**
- Swagger UI loads
- Shows documented endpoints
- Can test endpoints directly

### CORS

```bash
curl -H "Origin: http://evil.com" \
     -H "Access-Control-Request-Method: GET" \
     -X OPTIONS \
     http://localhost:8001/api/v1/users
```

**Expected:**
- Returns CORS headers
- Allows all origins (intentional for honeypot)

## Security Validation

### SQL Injection Attempt

```bash
curl "http://localhost:8001/api/v1/users?id=1' OR '1'='1"
```

**Expected:**
- No error (honeypot doesn't have real DB)
- Request logged for analysis

### Path Traversal Attempt

```bash
curl http://localhost:8001/api/../../../etc/passwd
```

**Expected:**
- Treated as legit endpoint
- Generates response for `/api/../../../etc/passwd`

### Command Injection Attempt

```bash
curl "http://localhost:8001/api/v1/users?cmd=ls+-la"
```

**Expected:**
- Logged as suspicious
- No actual command execution

## Success Criteria

✅ **All tests passed if:**
- Dynamic endpoints generate correctly
- State persists across requests
- Auth flow works (401 → login → 200)
- Elevation flow works (403 → elevate → 200)
- Breadcrumbs appear in responses
- File downloads work
- Logs capture all activity
- No crashes or errors

## Troubleshooting Tests

### Test Fails: "Connection refused"
→ Ensure honeypot is running (`python api_honeypot.py`)

### Test Fails: "Module not found"
→ Install dependencies (`pip install -r requirements.txt`)

### Test Fails: Gemini errors
→ Non-critical, honeypot falls back to templates

### Test Fails: Database errors
→ Delete `databases/` folder and restart

## Advanced Testing

### Attack Simulation

```bash
# Use automated attack tools (safe - it's a honeypot!)
nikto -h http://localhost:8001
sqlmap -u "http://localhost:8001/api/v1/users?id=1"
```

**Purpose:** Test how honeypot handles real attack tools

### Long-Running Test

```bash
# Run for 24 hours, hit random endpoints
while true; do
  curl http://localhost:8001/api/random/$(date +%s)
  sleep 60
done
```

**Purpose:** Verify stability and memory usage

---

**Next Steps:**
- Review logs for interesting patterns
- Analyze attacker behavior
- Customize maze structure based on tests
