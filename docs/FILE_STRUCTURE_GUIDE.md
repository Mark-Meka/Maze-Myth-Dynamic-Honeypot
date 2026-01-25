# File Structure Guide - Maze-Myth Dynamic Honeypot

> **Complete documentation of every file and folder in the project with importance ratings**

## 📊 Importance Rating Legend

- 🔴 **CRITICAL** - Essential for core functionality, system won't work without it
- 🟠 **HIGH** - Important for major features, significantly impacts functionality
- 🟡 **MEDIUM** - Useful features or enhancements, project works without it
- 🟢 **LOW** - Optional utilities, documentation, or convenience tools

---

## 📁 Root Directory Files

### 🔴 `honeypot.py` - CRITICAL
**Purpose:** Main entry point for the honeypot application  
**Description:** 
- Initializes Flask web server
- Sets up all routes and endpoints
- Integrates all modules (LLM, API Generator, File Generator, State Manager)
- Handles dynamic endpoint generation
- Manages authentication logic
- Configures logging system

**Key Features:**
- Catch-all route for dynamic API generation
- Fake authentication system (login, elevation, internal access)
- File download and tracking
- Tarpit mechanism for directory busters
- Contextual file generation

**Why It's Critical:** This is the heart of the honeypot. Without it, nothing runs.

---

### 🟠 `setup_honeypot.py` - HIGH
**Purpose:** Initial project setup and directory creation  
**Description:**
- Creates required directories (databases, log_files, generated_files, etc.)
- Initializes database files
- Sets up the project structure
- Verifies dependencies

**Key Features:**
- One-time setup automation
- Directory structure creation
- Initial configuration

**Why It's High:** Essential for first-time setup, but only needs to run once.

---

### 🟠 `requirements.txt` - HIGH
**Purpose:** Python package dependencies  
**Description:**
Lists all required Python packages:
- Flask & Flask-CORS (web framework)
- google-generativeai (Gemini AI)
- TinyDB (database)
- ReportLab (PDF generation)
- openpyxl (Excel generation)
- Faker (fake data generation)

**Why It's High:** Required to install all dependencies. Project won't run without these packages.

---

### 🟡 `run_honeypot.bat` - MEDIUM
**Purpose:** Windows launcher script  
**Description:**
- Automated startup for Windows users
- Checks Python installation
- Creates virtual environment if needed
- Installs dependencies
- Runs setup if needed
- Starts the honeypot

**Why It's Medium:** Convenient but not required (can run `python honeypot.py` directly).

---

### 🟡 `run_honeypot.sh` - MEDIUM
**Purpose:** Linux/Mac launcher script  
**Description:**
- Automated startup for Linux/Mac users
- Same functionality as .bat but for Unix-based systems
- Handles virtual environment setup
- Dependency installation
- Launches honeypot

**Why It's Medium:** Convenient but not required (can run `python3 honeypot.py` directly).

---

### 🟢 `README.md` - LOW
**Purpose:** Project documentation and overview  
**Description:**
- Project introduction
- Feature list
- Quick start guide
- Architecture overview
- Documentation links

**Why It's Low:** Important for understanding the project but not required for functionality.

---

### 🟢 `PROJECT_STRUCTURE.md` - LOW
**Purpose:** Quick reference guide for new structure  
**Description:**
- Overview of reorganized structure
- Quick start commands
- How to add new features
- Directory layout

**Why It's Low:** Documentation/reference only.

---

### 🟢 `CLEANUP_SUMMARY.md` - LOW
**Purpose:** Documentation of cleanup process  
**Description:**
- Lists files that were removed
- Shows before/after structure
- Tracks reorganization changes

**Why It's Low:** Historical documentation only.

---

### 🟢 `LICENSE` - LOW
**Purpose:** Legal license file  
**Description:** Educational/research use license terms

**Why It's Low:** Legal documentation, doesn't affect functionality.

---

### 🟡 `api_structure_seed.json` - MEDIUM
**Purpose:** Seed data for API structure  
**Description:**
- Defines API endpoint categories
- Contains fake authentication tokens
- Provides initial API structure templates

**Why It's Medium:** Helpful for initializing API structure but system can work without it.

---

## 📁 `src/` Directory - Source Code

### 📁 `src/api_generator/` - API Maze Generation

#### 🔴 `maze_generator.py` - CRITICAL
**Purpose:** Core API maze logic and breadcrumb system  
**Description:**
- Generates realistic API maze structure
- Determines access levels (public, user, admin, internal)
- Validates endpoints and detects directory busters
- Creates authentication responses
- Adds breadcrumbs to guide attackers between endpoints
- Implements tarpit mechanism

**Key Classes/Functions:**
- `APIMazeGenerator` - Main maze generator class
- `determine_access_level()` - Access control logic
- `is_valid_endpoint()` - Endpoint validation
- `add_breadcrumbs()` - Adds hints to responses
- `generate_auth_response()` - Fake authentication

**Why It's Critical:** Core logic for creating the interconnected API maze that keeps attackers engaged.

---

#### 🟢 `__init__.py` - LOW
**Purpose:** Package initializer  
**Description:** Exports `APIMazeGenerator` for easy imports

**Why It's Low:** Just makes imports cleaner, not functionally critical.

---

### 📁 `src/llm/` - AI Integration

#### 🟠 `llm_integration.py` - HIGH
**Purpose:** Google Gemini AI integration for realistic responses  
**Description:**
- Connects to Google Gemini API
- Generates context-aware, realistic JSON responses
- Creates believable API data based on endpoint paths
- Handles AI failures gracefully

**Key Classes/Functions:**
- `LLMGenerator` - Main AI integration class
- `generate_api_response()` - Generates realistic API responses
- Fallback mechanisms for when AI is unavailable

**Why It's High:** Significantly enhances realism but honeypot can work without it (uses fallback responses).

---

#### 🟢 `__init__.py` - LOW
**Purpose:** Package initializer  
**Description:** Exports `LLMGenerator` for easy imports

**Why It's Low:** Just makes imports cleaner.

---

### 📁 `src/file_generator/` - File Generation

#### 🟠 `generator.py` - HIGH
**Purpose:** Dynamic generation of bait files with tracking beacons  
**Description:**
- Generates PDF files with embedded tracking pixels
- Creates Excel spreadsheets with realistic data
- Produces .env configuration files
- Embeds unique tracking beacons in all files
- Triggers alerts when files are opened

**Key Classes/Functions:**
- `FileGenerator` - Main file generation class
- `generate_pdf()` - PDF with tracking beacon
- `generate_excel()` - Excel with tracking beacon
- `generate_env_file()` - .env configuration file

**Why It's High:** Important feature for tracking attacker behavior, but honeypot works without file downloads.

---

#### 🟢 `__init__.py` - LOW
**Purpose:** Package initializer  
**Description:** Exports `FileGenerator` for easy imports

**Why It's Low:** Just makes imports cleaner.

---

#### 🟠 `sqlite_gen.py` - HIGH
**Purpose:** SQLite database generator for realistic database bait files  
**Description:**
- Creates contextual databases based on endpoint paths
- Generates customer databases with fake PII
- Creates transaction databases with payment records
- Produces account databases with balances
- Generates audit log databases
- Embeds tracking beacons in hidden metadata tables

**Key Classes/Functions:**
- `SQLiteGenerator` - Main database generation class
- `generate_database()` - Creates contextual database
- `_create_customer_db()` - Customer/user tables
- `_create_transaction_db()` - Financial transactions
- `_create_account_db()` - Account information
- `_create_logs_db()` - Audit logs

**Why It's High:** Adds highly realistic database files that attackers will download and analyze.

---

#### 🟠 `txt_gen.py` - HIGH
**Purpose:** Text file generator for configs, logs, and credentials  
**Description:**
- Generates realistic .env files with fake API keys
- Creates system log files with audit entries
- Produces configuration files (YAML, INI style)
- Generates credential files with passwords and secrets
- All files contain believable but fake sensitive data

**Key Classes/Functions:**
- `TextFileGenerator` - Main text file generation class
- `generate_text_file()` - Smart file generation based on endpoint
- `_generate_env_file()` - Environment configuration
- `_generate_log_file()` - System/audit logs
- `_generate_config_file()` - Application configs
- `_generate_credentials_file()` - Secrets and passwords

**Why It's High:** Highly attractive bait for attackers seeking credentials and configuration.

---

### 📁 `src/rag/` - RAG Context Loading

#### 🟠 `rag_loader.py` - HIGH
**Purpose:** Loads RAG documents to provide context for consistent API generation  
**Description:**
- Recursively loads all files from RAG directory
- Categorizes content into API patterns, schemas, sample data
- Provides context summaries for LLM prompts
- Extracts relevant schemas based on endpoint paths
- Supplies sample data for file generation
- Falls back to default banking/financial context

**Key Classes/Functions:**
- `RAGLoader` - Main RAG document loader
- `load_documents()` - Scans and loads all RAG files
- `get_context_summary()` - Provides summary for LLM
- `get_schema_for_endpoint()` - Matches schemas to endpoints
- `get_sample_data()` - Retrieves realistic sample data

**Why It's High:** Ensures consistency and realism across API responses and file generation.

---

#### 🟢 `__init__.py` - LOW
**Purpose:** Package initializer  
**Description:** Exports `RAGLoader` for easy imports

**Why It's Low:** Just makes imports cleaner.

---

### 📁 `src/state/` - State Management

#### 🔴 `state_manager.py` - CRITICAL
**Purpose:** Database persistence and state tracking  
**Description:**
- Manages TinyDB database
- Stores generated endpoints for consistency
- Tracks user objects and their states
- Manages file download beacons
- Records beacon activations (when files are opened)
- Provides statistics

**Key Classes/Functions:**
- `APIStateManager` - Main state management class
- `save_endpoint()` - Persist endpoint responses
- `get_endpoint()` - Retrieve saved endpoints
- `save_beacon()` - Track file downloads
- `activate_beacon()` - Record file openings
- `get_statistics()` - System statistics

**Why It's Critical:** Essential for endpoint persistence (same path returns same response) which makes the honeypot feel real.

---

#### 🟢 `__init__.py` - LOW
**Purpose:** Package initializer  
**Description:** Exports `APIStateManager` for easy imports

**Why It's Low:** Just makes imports cleaner.

---

### 📁 `src/fine_tuning/` - Model Fine-Tuning

#### 🟡 `train_fixed.py` - MEDIUM
**Purpose:** Fixed/updated version of model fine-tuning script  
**Description:**
- Fine-tunes AI models with custom data
- Trains models to generate better API responses
- Uses the fine-tuning dataset

**Why It's Medium:** Optional advanced feature for improving AI responses.

---

#### 🟡 `train_original.py` - MEDIUM
**Purpose:** Original version of fine-tuning script  
**Description:**
- Original fine-tuning implementation
- Kept for reference/comparison

**Why It's Medium:** Reference/backup version, not actively used.

---

#### 🟡 `fine_tuning_data.jsonl` - MEDIUM
**Purpose:** Training data for model fine-tuning  
**Description:**
- Dataset of example API requests/responses
- Used to train custom AI models
- JSONL format (JSON Lines)

**Why It's Medium:** Only needed if fine-tuning AI models.

---

#### 🟢 `__init__.py` - LOW
**Purpose:** Package initializer  
**Description:** Makes fine_tuning a Python package

**Why It's Low:** Package structure only.

---

## 📁 `tests/` Directory - Testing

### 🟡 `test_api_honeypot.py` - MEDIUM
**Purpose:** Comprehensive test suite for the honeypot  
**Description:**
- Tests server availability
- Validates dynamic endpoint generation
- Checks state management/persistence
- Tests file generation
- Verifies health endpoints
- Validates documentation endpoints

**Test Coverage:**
- Server running check
- Dynamic endpoint generation
- State persistence
- File downloads (PDF, Excel, .env)
- Health check and statistics
- API documentation

**Why It's Medium:** Important for validation but not required for running the honeypot.

---

### 🟡 `demo_maze_attack.py` - MEDIUM
**Purpose:** Simulated attacker scenario demonstration  
**Description:**
- Demonstrates how an attacker navigates the maze
- Shows the progression through access levels
- Tests the full authentication flow
- Educational/demonstration tool

**Flow:**
1. Discovery (root endpoint)
2. Hit authentication wall
3. Fake login
4. User-level access
5. Permission wall
6. Privilege elevation
7. Admin access
8. Internal access

**Why It's Medium:** Demonstration/educational tool, not required for functionality.

---

### 🟢 `__init__.py` - LOW
**Purpose:** Package initializer  
**Description:** Makes tests a Python package

**Why It's Low:** Package structure only.

---

## 📁 `utils/` Directory - Utilities

### 🟡 `read_logs.py` - MEDIUM
**Purpose:** Audit log reader and decoder  
**Description:**
- Reads base64-encoded audit logs
- Decodes log messages
- Displays attacker activities
- Shows endpoint discoveries, file downloads, beacon activations

**Features:**
- Decodes base64 encoded logs
- Formats output for readability
- Filters by event type
- Timestamps analysis

**Why It's Medium:** Very useful for monitoring but not required for honeypot operation.

---

### 🟡 `verify_gemini.py` - MEDIUM
**Purpose:** Gemini API connection tester  
**Description:**
- Verifies Google Gemini API key is working
- Tests AI response generation
- Helps troubleshoot LLM integration issues
- Validates configuration

**Why It's Medium:** Helpful diagnostic tool but not required for operation.

---

### 🟢 `__init__.py` - LOW
**Purpose:** Package initializer  
**Description:** Makes utils a Python package

**Why It's Low:** Package structure only.

---

## 📁 `docs/` Directory - Documentation

### 🟢 `QUICKSTART.md` - LOW
**Purpose:** Quick 5-minute setup guide  
**Description:** Fast-track installation and first run instructions

---

### 🟢 `API_MAZE_DEMO.md` - LOW
**Purpose:** Demonstrates how the API maze works  
**Description:** Shows attacker journey through the maze with examples

---

### 🟢 `GEMINI_USAGE.md` - LOW
**Purpose:** AI integration guide  
**Description:** How to set up and configure Google Gemini API

---

### 🟢 `TESTING_GUIDE.md` - LOW
**Purpose:** Testing scenarios and guide  
**Description:** How to test the honeypot and validate functionality

---

### 🟢 `HOW_TO_RUN.md` - LOW
**Purpose:** Detailed running instructions  
**Description:** Step-by-step guide to start the honeypot

---

### 🟢 `AUDIT_LOGS_GUIDE.md` - LOW
**Purpose:** Log format and analysis guide  
**Description:** How to read and interpret audit logs

---

**All docs rated LOW:** Documentation is helpful but doesn't affect functionality.

---

## 📁 `config/` Directory - Configuration

### 🟡 `.env.template` - MEDIUM
**Purpose:** Environment variable template  
**Description:**
- Template for API keys and configuration
- Shows required environment variables
- Users copy this to `.env` and fill in values

**Typical Contents:**
- `GEMINI_API_KEY` - Google Gemini API key
- Other configuration variables

**Why It's Medium:** Important for configuration but system has fallbacks if API key is missing.

---

## 📁 Data Directories

### 📁 `databases/` - CRITICAL (Directory)
**Purpose:** TinyDB database storage  
**Contains:**
- `api_state.json` - Stores all generated endpoints, objects, and beacons

**Why It's Critical:** Without this, endpoints won't persist (each request would generate new responses).

---

### 📁 `datasets/` - MEDIUM (Directory)
**Purpose:** Dataset storage  
**Contains:** Training data, sample data, etc.

**Why It's Medium:** Used for fine-tuning and testing.

---

### 📁 `generated_files/` - MEDIUM (Directory)
**Purpose:** Storage for dynamically generated files  
**Contains:** PDFs, Excel files, .env files generated for attackers

**Why It's Medium:** Important for file tracking feature but honeypot works without it.

---

### 📁 `log_files/` - HIGH (Directory)
**Purpose:** Audit logs and activity tracking  
**Contains:**
- `api_audit.log` - Base64-encoded audit trail

**Key Events Logged:**
- Endpoint discoveries
- Authentication attempts
- File downloads
- Beacon activations
- Attacker activity

**Why It's High:** Critical for monitoring attacker behavior (main purpose of honeypot).

---

### 📁 `static/` - MEDIUM (Directory)
**Purpose:** Static assets  
**Contains:**
- `tracking_pixel.png` - Transparent 1x1 pixel for file tracking

**Why It's Medium:** Only needed for beacon tracking feature.

---

## 📋 Summary by Importance

### 🔴 CRITICAL (3 files)
1. `honeypot.py` - Main application
2. `src/api_generator/maze_generator.py` - Maze logic
3. `src/state/state_manager.py` - State persistence

### 🟠 HIGH (4 files)
1. `requirements.txt` - Dependencies
2. `setup_honeypot.py` - Initial setup
3. `src/llm/llm_integration.py` - AI responses
4. `src/file_generator/generator.py` - Bait files

### 🟡 MEDIUM (11 files)
1. `run_honeypot.bat` - Windows launcher
2. `run_honeypot.sh` - Linux launcher
3. `api_structure_seed.json` - API templates
4. `src/fine_tuning/train_fixed.py`
5. `src/fine_tuning/train_original.py`
6. `src/fine_tuning/fine_tuning_data.jsonl`
7. `tests/test_api_honeypot.py` - Test suite
8. `tests/demo_maze_attack.py` - Demo
9. `utils/read_logs.py` - Log reader
10. `utils/verify_gemini.py` - API tester
11. `config/.env.template` - Config template

### 🟢 LOW (13 files)
- All documentation files (6 in `docs/`)
- All `__init__.py` files (6 total)
- `README.md`
- `PROJECT_STRUCTURE.md`
- `CLEANUP_SUMMARY.md`
- `LICENSE`

---

## 🎯 Minimum Files to Run

To run a basic honeypot, you **absolutely need**:

1. ✅ `honeypot.py`
2. ✅ `src/api_generator/maze_generator.py`
3. ✅ `src/state/state_manager.py`
4. ✅ `src/file_generator/generator.py`
5. ✅ `src/llm/llm_integration.py` (can run without, uses fallbacks)
6. ✅ All `__init__.py` files
7. ✅ `requirements.txt` (for dependencies)
8. ✅ `databases/` directory (created automatically)

**Everything else enhances the experience but is optional!**

---

## 📊 File Count Summary

```
Total Project Files: ~40+ files

By Type:
- Python Source: 13 files
- Documentation: 13 files
- Configuration: 2 files
- Scripts: 3 files
- Data: 2+ files
- Package Files: 6 __init__.py files

---

**This guide gives you a complete understanding of every file's purpose and importance in the Maze-Myth Dynamic Honeypot project!** 🎉
