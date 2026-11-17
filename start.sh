#!/bin/bash
set -e

# CodeSentinel - Startup Script
echo "=================================================="
echo "  🛡️  CodeSentinel - Autonomous Codebase Auditor  "
echo "=================================================="

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT"

# Check Python environment
if [ -d "backend/venv" ]; then
    echo "Using existing virtual environment at backend/venv..."
    PYTHON="backend/venv/bin/python3"
else
    echo "Creating virtual environment..."
    python3 -m venv backend/venv
    PYTHON="backend/venv/bin/python3"
    echo "Installing backend dependencies..."
    $PYTHON -m pip install -r requirements.txt
fi

# Build frontend if dist doesn't exist
if [ ! -d "frontend/dist" ]; then
    echo "Building frontend dashboard..."
    cd frontend
    if [ ! -d "node_modules" ]; then
        npm install
    fi
    npm run build
    cd "$PROJECT_ROOT"
fi

echo ""
echo "🚀 Starting CodeSentinel on http://localhost:8000"
echo "   - Web Dashboard: http://localhost:8000"
echo "   - Interactive API Docs: http://localhost:8000/docs"
echo ""

export PYTHONPATH="$PROJECT_ROOT/backend"
exec $PYTHON -m uvicorn app.main:app --host 0.0.0.0 --port 8000
