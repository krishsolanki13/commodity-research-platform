"""RunManager: run ID assignment and BacktestResult persistence.

Consolidates ADR-009's RunManager (assign/save) and RunRegistry
(list/load/compare/delete) responsibilities into one class. See Module 5
Transfer Package Section 8 for the resolved-ambiguity rationale.

NOTE: This file currently contains only generate_run_id(). The full
RunManager class is added in Increment 4.
"""

from __future__ import annotations

import datetime


def generate_run_id(strategy_name: str, asset: str) -> str:
    """Generate a run_id in the format YYYYMMDD_HHMMSS_{strategy}_{asset}.

    Args:
        strategy_name: Strategy identifier (e.g., "ema_crossover").
        asset: Asset identifier (e.g., "gold").

    Returns:
        run_id string. See ADR-009.
    """
    timestamp = datetime.datetime.now(tz=datetime.UTC).strftime("%Y%m%d_%H%M%S")
    return f"{timestamp}_{strategy_name}_{asset}"
