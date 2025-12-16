#!/bin/bash

# Run Honeypot (Linux/Mac)
# Quick launcher for the API honeypot system

echo "============================================================"
echo "[HONEYPOT] Starting API Honeypot System"
echo "============================================================"
echo ""

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 is not installed"
    echo "Please install Python 3 from your package manager"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "[INFO] Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "[INFO] Activating virtual environment..."
source venv/bin/activate

# Install requirements if not already installed
python3 -c "import fastapi" 2>/dev/null || {
    echo "[INFO] Installing requirements..."
    pip install -r requirements.txt
}

# Setup directories if needed
if [ ! -d "databases" ]; then
    echo "[INFO] Setting up honeypot directories..."
    python3 setup_honeypot.py
fi

echo ""
echo "============================================================"
echo "[OK] Environment ready!"
echo "============================================================"
echo ""
echo "Starting API Honeypot on http://localhost:8001"
echo ""
echo "Available endpoints:"
echo "  - API Documentation: http://localhost:8001/docs"
echo "  - Health Check: http://localhost:8001/health"
echo "  - Root: http://localhost:8001/"
echo ""
echo "Press Ctrl+C to stop the server"
echo "============================================================"
echo ""

# Run the honeypot
python3 honeypot.py

# Deactivate on exit
deactivate
