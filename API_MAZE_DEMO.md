# API Maze Demo - Shows the realistic interconnected API system

This demo shows how an attacker would navigate through the honeypot's API maze.

## Starting the Honeypot

```bash
python api_honeypot.py
```

The honeypot now runs on **port 8001** with the maze system enabled.

## Attack Flow Simulation

### Level 1: Discovery

```bash
# Attacker finds the root
curl http://localhost:8001/

# Response includes hints to other endpoints:
{
  "endpoints": {
    "authentication": "/api/v1/auth/login",
    "api_v1": "/api/v1/",
    "api_v2": "/api/v2/admin/"
  }
}
```

### Level 2: Hitting Auth Wall

```bash
# Try to access user data without auth
curl http://localhost:8001/api/v1/users

# Gets 401 Unauthorized with hint:
{
  "error": "Unauthorized",
  "hint": "POST /api/v1/auth/login to obtain a token"
}
```

### Level 3: Fake Login

```bash
# Login (always succeeds!)
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"attacker","password":"password"}'

# Gets fake JWT token:
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoidXNlciJ9.fake",
  "hint": "Use this token in Authorization header"
}
```

### Level 4: Authenticated Access

```bash
# Now try users endpoint with token
curl http://localhost:8001/api/v1/users \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoidXNlciJ9.fake"

# Gets realistic user data WITH breadcrumbs:
{
  "users": [...],
  "_links": {
    "related": ["/api/v1/users/{id}/profile", "/api/v2/admin/users"]
  }
}
```

### Level 5: Hitting Permission Wall

```bash
# Try admin endpoint with user token
curl http://localhost:8001/api/v2/admin/users \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoidXNlciJ9.fake"

# Gets 403 Forbidden with hint:
{
  "error": "Forbidden",
  "hint": "Request elevation at /api/v1/auth/elevate"
}
```

### Level 6: Elevation

```bash
# Request admin privileges
curl -X POST http://localhost:8001/api/v1/auth/elevate \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoidXNlciJ9.fake"

# Gets admin token:
{
  "admin_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYWRtaW4ifQ.fake",
  "warning": "Admin endpoints available at /api/v2/admin/*"
}
```

### Level 7: Admin Access

```bash
# Try admin endpoint again with admin token
curl http://localhost:8001/api/v2/admin/users \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYWRtaW4ifQ.fake"

# Gets "sensitive" data with hints to internal endpoints:
{
  "admin_users": [...],
  "_meta": {
    "hint": "Debug information: /internal/debug/trace"
  }
}
```

### Level 8: The Loop

```bash
# Following the breadcrumbs...
curl http://localhost:8001/internal/debug/trace \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJyb2xlIjoiYWRtaW4ifQ.fake"

# Might get 403, suggesting internal token needed
# Or might hint at /internal/config/secrets
# Or /internal/deploy/status
# The maze keeps going...
```

## Key Features

1. **Progressive Disclosure**: Attackers unlock access levels gradually
2. **Breadcrumb System**: Each response hints at 1-2 other endpoints
3. **Fake Authentication**: All auth endpoints succeed, creating illusion of access
4. **Logical Structure**: Endpoints follow realistic corporate API patterns
5. **Gemini Generation**: AI creates context-aware responses with natural hints

## Monitoring

Watch the honeypot console for:
- `[MAZE]` tags showing access level checks
- `✨ [GEMINI+MAZE]` when AI generates interconnected responses
- `[AUTH]` tags for authentication attempts

## Running the Full Demo

Use the automated script:
```bash
python demo_maze_attack.py
```

This simulates a complete attack flow through all 8 levels!
