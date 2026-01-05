#!/bin/bash
# Run E2E tests with real LLM calls
#
# This script:
# 1. Activates the virtual environment
# 2. Loads environment variables from .env
# 3. Runs E2E tests with --run-slow flag
#
# Usage:
#   ./scripts/run_e2e_tests.sh                    # Run all E2E tests
#   ./scripts/run_e2e_tests.sh -k "narrator"      # Run only narrator tests
#   ./scripts/run_e2e_tests.sh --tb=long          # Run with detailed tracebacks

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"

cd "$BACKEND_DIR"

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
else
    echo "Error: Virtual environment not found at $BACKEND_DIR/venv"
    echo "Run: python -m venv venv && pip install -r requirements.txt"
    exit 1
fi

# Load environment variables (dotenv also loads in conftest.py, but this ensures shell has them)
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(grep -v '^#' "$PROJECT_ROOT/.env" | grep -v '^$' | xargs)
fi

# Run E2E tests with --run-slow and any additional arguments
echo "Running E2E tests..."
python -m pytest tests/e2e/ -v --run-slow "$@"
