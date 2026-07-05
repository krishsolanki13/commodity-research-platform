#!/bin/bash
# launch_dashboard.sh
# Commodity Systematic Research Platform — macOS/Linux dashboard launcher.
#
# Calls .venv/bin/streamlit directly rather than relying on PATH resolution.
# Sets PYTHONPATH so dashboard/components/ imports resolve correctly.
#
# Usage: ./launch_dashboard.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR"

STREAMLIT="$SCRIPT_DIR/.venv/bin/streamlit"

if [ ! -f "$STREAMLIT" ]; then
    echo "ERROR: streamlit not found at $STREAMLIT"
    echo "Set up the virtual environment first:"
    echo "  python -m venv .venv && source .venv/bin/activate && pip install -e '.[dev]'"
    exit 1
fi

echo "Commodity Systematic Research Platform"
echo "Python:    $SCRIPT_DIR/.venv/bin/python"
echo "Dashboard: http://localhost:8501"
echo ""

export MLFLOW_ALLOW_FILE_STORE="true"
"$STREAMLIT" run "$SCRIPT_DIR/dashboard/app.py"
