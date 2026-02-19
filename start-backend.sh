#!/bin/bash
# STELLAR OUTREACH — Backend API Server
# Starts the Python API on port 8080
# The React Native mobile app connects to this.

AMBER='\033[38;5;208m'
GREEN='\033[0;32m'
RESET='\033[0m'
BOLD='\033[1m'

echo -e "${BOLD}${AMBER}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  STELLAR OUTREACH — Backend"
echo "  API Server starting on port 8080"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${RESET}"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 not found. Install Python 3.11+."
    exit 1
fi

# Install dependencies if needed
echo -e "${GREEN}[1/2]${RESET} Checking dependencies..."
pip3 install -r requirements.txt -q

# Run first-time config if needed
CONFIG_FILE="$HOME/.nexus_station/config.json"
if [ ! -f "$CONFIG_FILE" ]; then
    echo -e "${GREEN}[2/2]${RESET} First-time setup — configuring API keys..."
    cd src/narrative_agentic && python3 setup.py && cd ../..
fi

echo -e "${GREEN}[2/2]${RESET} Starting API server on http://localhost:8080 ..."
echo ""
cd src/narrative_agentic && python3 api_server.py
