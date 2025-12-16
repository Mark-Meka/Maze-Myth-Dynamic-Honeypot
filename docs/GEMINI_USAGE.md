# 🧠 How to Use Gemini AI in Your Honeypot

Your honeypot is now supercharged with Google Gemini AI! 🚀

## 1. Start the Honeypot

Open your terminal and run:

```bash
python api_honeypot.py
```

You should see:
```
[LLM] Enabled (Gemini)
[MAZE] Realistic interconnected API structure
```

## 2. Trigger the AI (The Fun Part)

The AI only activates when someone visits a **NEW** endpoint that doesn't exist yet. This is the "Infinite Maze" feature.

### Try these commands (in a new terminal):

**1. Generate a fake user profile:**
```bash
curl http://localhost:8001/api/v1/employees/executive/john_doe
```
*Gemini will invent a profile for "John Doe" with executive details.*

**2. Generate a fake secret project:**
```bash
curl http://localhost:8001/api/internal/projects/project_chimera/status
```
*Gemini will invent a status report for "Project Chimera".*

**3. Generate a fake error message:**
```bash
curl -X POST http://localhost:8001/admin/database/reset
```
*Gemini will invent a realistic "Permission Denied" or database error.*

## 3. Watch the Console

Look at the terminal where `api_honeypot.py` is running. You will see:

```
✨ [GEMINI+MAZE] GET /api/v1/employees/executive/john_doe | Level: authenticated
```

This confirms the AI created the response on-the-fly with maze context!

## 4. Verify Persistence

Run the **SAME** command again:
```bash
curl http://localhost:8001/api/v1/employees/executive/john_doe
```

You will get the **EXACT SAME** response. The honeypot remembered the AI's creation and saved it to the database. It won't call Gemini again for this specific path.

## 5. The Maze Effect

Notice that responses include **breadcrumbs**:

```json
{
  "employee": {...},
  "_links": {
    "related": [
      "/api/v1/employees/executive/john_doe/profile",
      "/api/v2/admin/employees"
    ]
  }
}
```

These hints guide attackers to explore more endpoints, keeping them in the loop!

## 6. Troubleshooting

If you see `⚠️ [FALLBACK] Used template`, it means:
1. The API key might be invalid (check `llm_integration.py`)
2. Internet connection issue
3. Google API quota exceeded (unlikely for free tier)

Run `python verify_gemini.py` to diagnose issues.

## 7. How the AI Helps

Gemini makes each response:
- **Unique** - Not templated
- **Contextual** - Matches the endpoint purpose
- **Interconnected** - Includes hints to other endpoints
- **Realistic** - Feels like a real corporate API

## 8. Monitoring AI Usage

Check logs:
```bash
cat log_files/api_audit.log | grep "GEMINI"
```

You'll see which endpoints triggered AI generation.

## Advanced: Customizing Prompts

Edit `api_maze_generator.py` method `enhance_prompt_with_context()` to customize how the AI generates responses.

Example: Make it sound like a banking API, healthcare system, etc.
