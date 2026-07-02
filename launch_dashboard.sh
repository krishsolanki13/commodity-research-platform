#!/bin/bash
# launch_dashboard.sh
# Launch the Commodity Research Platform dashboard.
# Sets PYTHONPATH to the project root so dashboard/components/ imports resolve correctly.
# Usage: ./launch_dashboard.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR"
echo "Starting Commodity Systematic Research Platform..."
echo "PYTHONPATH set to: $PYTHONPATH"
echo "Dashboard will be available at http://localhost:8501"
streamlit run "$SCRIPT_DIR/dashboard/app.py"
