# How to Run the Dynamic API Honeypot

Complete guide to running your honeypot system.

## Quick Start (3 Steps)

### Step 1: Install Dependencies

`ash
pip install -r requirements.txt
`

### Step 2: Setup Directories

`ash
python setup_honeypot.py
`

### Step 3: Start the Honeypot

`ash
python api_honeypot.py
`

You should see:
`
[HONEYPOT] Dynamic API Honeypot with Maze System Started
[LLM] Enabled (Gemini)
[SERVER] http://localhost:8001
`

## Accessing the Honeypot

- **API Documentation:** http://localhost:8001/docs
- **Health Check:** http://localhost:8001/health
- **Root:** http://localhost:8001/

## Testing

### Basic Test
`ash
curl http://localhost:8001/health
`

### Full Test Suite
`ash
python test_api_honeypot.py
`

### Attack Simulation
`ash
python demo_maze_attack.py
`

## Configuration

**Change Port:** Edit api_honeypot.py line 316
**Gemini API Key:** Edit llm_integration.py line 14

## Troubleshooting

**Database Error:** Delete databases/api_state.json and restart
**Port In Use:** Change port or kill existing process
**Module Not Found:** Run pip install -r requirements.txt

## More Info

See README.md for complete documentation.
