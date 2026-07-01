"""CostModel: per-trade transaction cost computation.

Commission per trade (flat fee) + slippage (ticks × tick_value).
Phase 1 simplification: cost is flat per trade execution, not scaled
by position size or contract count. See Architecture Section 11.
"""

from __future__ import annotations

import logging


class CostModel:
    """Computes transaction cost per trade execution.

    cost = commission_per_trade + (slippage_ticks * tick_value)

    Phase 1 interpretation: slippage_ticks represents total round-trip slippage
    (entry + exit fills combined), charged once per TradeRecord. Architecture
    Section 11 lists slippage as "fixed ticks per side" — in this implementation
    "per side" describes the slippage model's basis (tick-denominated) rather
    than mandating two separate CostModel calls per trade. A two-call model
    would also double-charge commission, which contradicts "per-trade flat fee."
    Revisit for Phase 2 if execution realism requires separate entry/exit fills.

    tick_value is asset-specific (e.g., $10.00 for Gold per assets.yaml)
    and is passed at compute() call time, not bound at construction,
    since one CostModel instance may be reused across assets.
    """

    def __init__(self, commission_per_trade: float, slippage_ticks: int) -> None:
        """Initialise CostModel.

        Args:
            commission_per_trade: Flat commission in USD per trade execution.
                Default 5.00 per config.yaml costs.default_commission_usd.
            slippage_ticks: Number of ticks of slippage per execution.
                Default 1 per config.yaml costs.default_slippage_ticks.
        """
        self._commission_per_trade = commission_per_trade
        self._slippage_ticks = slippage_ticks
        self._logger = logging.getLogger(__name__)

    def compute(self, tick_value: float) -> float:
        """Compute transaction cost in USD for one trade execution.

        Args:
            tick_value: Asset-specific dollar value per tick (e.g., assets.yaml
                gold.tick_value = 10.00).

        Returns:
            Transaction cost in USD: commission_per_trade + slippage_ticks * tick_value.
        """
        cost = self._commission_per_trade + (self._slippage_ticks * tick_value)
        self._logger.debug(
            "CostModel: commission=%.2f + slippage=%d*%.4f = %.4f",
            self._commission_per_trade,
            self._slippage_ticks,
            tick_value,
            cost,
        )
        return cost
