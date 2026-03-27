#!/bin/bash
set -e

echo "Setting up stay_active..."

python3 -m venv venv
venv/bin/pip install --upgrade pip -q
venv/bin/pip install -r requirements.txt -q

echo ""
echo "Setup complete. Run with:"
echo "  venv/bin/python3 stay_active.py"
