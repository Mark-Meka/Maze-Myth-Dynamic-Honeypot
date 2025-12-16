# Quick Start Guide

Get your honeypot running in 5 minutes!

## Prerequisites

- Python 3.8+
- Internet connection (for Gemini API)

## Step 1: Setup (30 seconds)

```bash
python setup_honeypot.py
```

This creates necessary directories and tracking pixel.

## Step 2: Install Dependencies (2 minutes)

```bash
pip install -r requirements.txt
```

**Note:** On Windows, if you get memory errors:
```bash
pip install --no-cache-dir google-generativeai
```

## Step 3: Gemini API Key (1 minute)

1. Get free key: https://makersuite.google.com/app/apikey
2. Open `llm_integration.py`
3. Replace the API key on line 14

## Step 4: Start Honeypot (1 second)

```bash
python api_honeypot.py
```

You should see:
```
[HONEYPOT] Dynamic API Honeypot with Maze System Started
[LLM] Enabled (Gemini)
[MAZE] Realistic interconnected API structure
```

## Step 5: Test It (1 minute)

Open another terminal:

```bash
# Test root
curl http://localhost:8001/

# Try a dynamic endpoint
curl http://localhost:8001/api/v1/users

# See the 401 error with hint to login!
```

## 🎉 Success!

Your honeypot is running! 

**Next steps:**
- Read [API_MAZE_DEMO.md](API_MAZE_DEMO.md) to understand the maze
- Run `python demo_maze_attack.py` for full simulation
- Check `log_files/api_audit.log` for activity

## Common Issues

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Port 8001 already in use"
Change port in `api_honeypot.py` line 316

### Gemini API errors
- Check your API key is correct
- Verify internet connection
- Honeypot works without AI (uses fallbacks)

## What's Next?

- **Testing:** See [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **Understanding Gemini:** See [GEMINI_USAGE.md](GEMINI_USAGE.md)
- **Full documentation:** See [README.md](README.md)
