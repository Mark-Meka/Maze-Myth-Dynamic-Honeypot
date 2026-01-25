# Quick Start Guide

Get your honeypot running in 5 minutes!

## Prerequisites

- Python 3.8+
- Internet connection (for Gemini API)
- Google Gemini API key (free)

## Step 1: Setup (30 seconds)

```bash
python setup_honeypot.py
```

This creates necessary directories, tracking pixel, and file storage.

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
2. Set environment variable:
   ```bash
   # Windows
   set GEMINI_API_KEY=your-key-here
   
   # Linux/Mac
   export GEMINI_API_KEY=your-key-here
   ```

## Step 4: Start Honeypot (1 second)

```bash
python honeypot.py
```

You should see:
```
[HONEYPOT] Dynamic API Honeypot with Maze System Started
[RAG] Loaded context: Banking API
[LLM] Enabled (Gemini)
[FILE_GEN] SQLite, PDF, TXT generators ready
[MAZE] Realistic interconnected API structure
[SERVER] http://localhost:8001
```

## Step 5: Start Real-Time Dashboard (Optional)

In a new terminal:

```bash
cd dashboard
python monitor.py
```

Then open http://localhost:8002 in your browser to see live activity!

## Step 6: Test It (1 minute)

Open another terminal:

```bash
# Test root
curl http://localhost:8001/

# Try a dynamic endpoint
curl http://localhost:8001/api/v1/users

# Download a bait file (SQLite database)
curl http://localhost:8001/api/v1/data/export -o data.db

# See the 401 error with hint to login!
```

## 🎉 Success!

Your honeypot is running with:
- ✅ RAG-based realistic API responses
- ✅ Dynamic SQLite, PDF, and TXT file generation
- ✅ Real-time monitoring dashboard
- ✅ Download tracking with IP logging

**Next steps:**
- Open dashboard: http://localhost:8002
- Read [API_MAZE_DEMO.md](API_MAZE_DEMO.md) to understand the maze
- Run `python tests/demo_maze_attack.py` for full simulation
- Check dashboard for real-time activity logs

## Common Issues

### "Module not found"
```bash
pip install -r requirements.txt
```

### "Port 8001 already in use"
Change port in `honeypot.py` (search for `port=8001`)

### Gemini API errors
- Check your API key is correct
- Verify internet connection
- Honeypot works without AI (uses fallback responses)

### Dashboard not showing data
- Make sure honeypot is running first
- Check that monitor.py is running on port 8002
- Verify logs exist in `log_files/api_audit.log`

## What's Next?

- **Dashboard:** Open http://localhost:8002 for real-time monitoring
- **Testing:** See [TESTING_GUIDE.md](TESTING_GUIDE.md)
- **Understanding Features:** See [README.md](../README.md)
- **Logs:** Use `python utils/read_logs.py` to view audit logs
