"""FixedNotionalSizer: Phase 1 position sizing per ADR-005.

Each signal receives a fixed USD notional exposure regardless of asset
volatility. Phase 2 will add VolatilityScaledSizer implementing the
same PositionSizer interface. See ADR-005.
"""

from __future__ import annotations

import logging

from src.core.registry import PositionSizer


class FixedNotionalSizer(PositionSizer):
    """Phase 1 position sizing: fixed USD notional per signal.

    Position size does not vary with signal strength, asset, or current
    equity. This is a documented Phase 1 simplification — results
    represent relative signal performance, not realistic risk-adjusted
    dollar PnL. See ADR-005.
    """

    def __init__(self, notional_usd: float) -> None:
        """Initialise FixedNotionalSizer.

        Args:
            notional_usd: Fixed USD notional exposure per signal.
                Default 100000.0 per config.yaml sizing.fixed_notional_usd.
        """
        self._notional_usd = notional_usd
        self._logger = logging.getLogger(__name__)

    def compute_size(self, signal: float, asset: str, equity: float) -> float:
        """Return the fixed notional size, ignoring signal/asset/equity.

        Args:
            signal: Unused in Phase 1. Accepted for interface compliance
                with Phase 2 VolatilityScaledSizer.
            asset: Unused in Phase 1. Accepted for interface compliance.
            equity: Unused in Phase 1. Accepted for interface compliance.

        Returns:
            Fixed USD notional size. See ADR-005.
        """
        return self._notional_usd
