"""TradeLog: trade boundary detection and TradeRecord construction.

Implements the trade detection rules from Architecture Section 11 and
the Implementation Roadmap's trade boundary spec. The core invariant:
held_position[t] = position_signal.shift(1, fill_value=0) — the
position actually held during bar t was decided using information
available at Close[t-1] and executed at Open[t]. See ADR-002.
"""

from __future__ import annotations

import logging

import pandas as pd

from src.backtesting.costs import CostModel
from src.core.registry import PositionSizer
from src.core.types import TradeRecord


class TradeLog:
    """Detects trade boundaries in a PositionSignal and builds TradeRecord objects.

    Algorithm:
        1. executed_position = position_signal.shift(1, fill_value=0)
           — the position actually held during each bar, per ADR-002.
        2. Group executed_position into maximal runs of constant value.
        3. Each non-zero run is a trade:
           - entry_date/entry_price = first bar of the run / that bar's open
           - exit_date/exit_price = bar AFTER the run / that bar's open
             (normal close), OR if the run extends to the last bar in the
             data, force-close at that bar's close (force_closed=True).
        4. A direction reversal (e.g., +1 directly to -1) produces two
           adjacent runs, which naturally yields two TradeRecords whose
           exit/entry coincide at the same date and price — no special
           casing required.
    """

    def __init__(
        self,
        run_id: str,
        asset: str,
        cost_model: CostModel,
        position_sizer: PositionSizer,
        contract_multiplier: float,
        tick_value: float,
        initial_capital_usd: float,
        rolling_equity: pd.Series | None = None,
    ) -> None:
        """Initialise TradeLog.

        Args:
            run_id: Run identifier, embedded in every TradeRecord.
            asset: Asset identifier (e.g., "gold").
            cost_model: CostModel for transaction cost computation.
            position_sizer: PositionSizer for size_notional computation.
            contract_multiplier: Dollar value per point move (assets.yaml).
                Used to derive size_contracts from size_notional.
            tick_value: Dollar value per tick (assets.yaml). Passed to
                cost_model.compute().
            initial_capital_usd: Passed to position_sizer.compute_size()
                as the equity argument. Phase 1: not used by
                FixedNotionalSizer but required by the PositionSizer
                interface for Phase 2 compatibility.
        """
        self._run_id = run_id
        self._asset = asset
        self._cost_model = cost_model
        self._position_sizer = position_sizer
        self._contract_multiplier = contract_multiplier
        self._tick_value = tick_value
        self._initial_capital_usd = initial_capital_usd
        self._rolling_equity = rolling_equity
        self._logger = logging.getLogger(__name__)

    def build(
        self,
        position_signal: pd.Series,
        ohlcv: pd.DataFrame,
    ) -> list[TradeRecord]:
        """Detect trades and construct TradeRecord objects.

        Args:
            position_signal: PositionSignal Series, values in {-1, 0, +1}.
            ohlcv: NormalizedOHLCV DataFrame, same or overlapping index.

        Returns:
            List of TradeRecord, one per detected trade. Empty list if
            position_signal is all-zero (no trades).
        """
        executed_position = position_signal.shift(1, fill_value=0).astype("int8")
        change_points = executed_position != executed_position.shift(1, fill_value=0)
        group_id = change_points.cumsum()

        trades: list[TradeRecord] = []
        n = len(ohlcv)

        for _, group in executed_position.groupby(group_id):
            direction = int(group.iloc[0])
            if direction == 0:
                continue

            start_idx = group.index[0]
            end_idx = group.index[-1]
            start_pos = ohlcv.index.get_loc(start_idx)
            end_pos = ohlcv.index.get_loc(end_idx)

            entry_date = start_idx
            entry_price = float(ohlcv.loc[start_idx, "open"])

            if end_pos + 1 < n:
                exit_loc = ohlcv.index[end_pos + 1]
                exit_date = exit_loc
                exit_price = float(ohlcv.loc[exit_loc, "open"])
                force_closed = False
            else:
                exit_date = end_idx
                exit_price = float(ohlcv.loc[end_idx, "close"])
                force_closed = True

            duration_bars = end_pos - start_pos + 1

            # TD-B: rolling equity at entry bar — fall back to initial capital
            if self._rolling_equity is not None:
                equity_at_bar = float(
                    self._rolling_equity.get(entry_date, self._initial_capital_usd)
                )
            else:
                equity_at_bar = self._initial_capital_usd

            signed_notional = self._position_sizer.compute_size(
                signal=float(direction),
                asset=self._asset,
                equity=equity_at_bar,
                bar_date=entry_date,
            )
            size_contracts = signed_notional / (entry_price * self._contract_multiplier)

            gross_pnl = (exit_price - entry_price) * signed_notional / entry_price
            transaction_cost = self._cost_model.compute(self._tick_value)
            net_pnl = gross_pnl - transaction_cost
            return_pct = (
                net_pnl / abs(signed_notional) if signed_notional != 0.0 else 0.0
            )

            trades.append(
                TradeRecord(
                    run_id=self._run_id,
                    asset=self._asset,
                    direction=direction,
                    entry_date=entry_date.date(),
                    exit_date=exit_date.date(),
                    entry_price=entry_price,
                    exit_price=exit_price,
                    size_notional=abs(signed_notional),
                    size_contracts=abs(size_contracts),
                    gross_pnl=gross_pnl,
                    transaction_cost=transaction_cost,
                    net_pnl=net_pnl,
                    duration_bars=duration_bars,
                    return_pct=return_pct,
                    force_closed=force_closed,
                )
            )

        self._logger.info(
            "TradeLog: detected %d trades for %s (run_id=%s)",
            len(trades),
            self._asset,
            self._run_id,
        )
        return trades
