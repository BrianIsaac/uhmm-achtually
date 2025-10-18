#!/bin/bash

# Run the WebSocket server for the Uhmm Actually fact-checker

echo "Starting Uhmm Actually WebSocket Server..."
echo "================================================"
echo "WebSocket URL: ws://localhost:8765"
echo "Health check: http://localhost:8765/"
echo "================================================"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install it with:"
    echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Check if .venv exists, create if not
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with uv..."
    uv venv
fi

# Install dependencies using uv
echo "Installing dependencies..."
uv pip install -e ".[llm,search,stt,config,utils,websocket,dev]"

# Run the server with uvicorn through uv
echo "Starting server with uvicorn..."
uv run uvicorn main:app --host localhost --port 8765 --reload