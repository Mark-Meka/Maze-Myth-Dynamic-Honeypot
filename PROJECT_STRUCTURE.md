# New Project Structure - Quick Reference

## 🎯 Main Changes

The project has been reorganized into a modular structure for better maintainability and scalability.

## 🚀 Quick Start

### Run the Honeypot
```bash
# New way (recommended)
python honeypot.py

# Or use the launcher scripts
./run_honeypot.sh    # Linux/Mac
run_honeypot.bat     # Windows
```

### Run Tests
```bash
python tests/test_api_honeypot.py
python tests/demo_maze_attack.py
```

## 📁 New Directory Structure

```
src/                     # All source code
├── api_generator/       # API maze generation
├── llm/                 # AI response generation
├── file_generator/      # Bait file creation
├── state/               # State management
└── fine_tuning/         # Model fine-tuning

tests/                   # Test files
utils/                   # Utility scripts
docs/                    # Documentation
config/                  # Configuration files
```

## 🔧 Adding New Features

1. Create folder: `src/your_feature/`
2. Add your module: `src/your_feature/module.py`
3. Create `src/your_feature/__init__.py`:
   ```python
   from .module import YourClass
   __all__ = ['YourClass']
   ```
4. Import in `honeypot.py`:
   ```python
   from src.your_feature import YourClass
   ```

## 📚 Documentation

All documentation is now in the `docs/` folder:
- `docs/QUICKSTART.md` - Quick setup guide
- `docs/API_MAZE_DEMO.md` - How the maze works
- `docs/GEMINI_USAGE.md` - AI integration
- `docs/TESTING_GUIDE.md` - Testing guide

## 🛠️ Utility Scripts

- `utils/read_logs.py` - Read audit logs
- `utils/verify_gemini.py` - Verify Gemini API

## ⚙️ Configuration

- `config/.env.template` - Environment template

## 🔑 Important Files

- `honeypot.py` - Main entry point (NEW)
- `requirements.txt` - Dependencies
- `setup_honeypot.py` - Initial setup
- `README.md` - Full documentation

---

**Note:** The old `api_honeypot.py` file is still present for reference but is no longer used.
