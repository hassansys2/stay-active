#!/bin/bash
set -e

# Auto-setup venv if not present
if [ ! -f venv/bin/python3 ]; then
    echo "venv not found — running setup first..."
    bash setup.sh
fi

exec venv/bin/python3 stay_active.py "$@"
