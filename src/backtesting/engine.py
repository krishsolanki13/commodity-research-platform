"""VectorizedBacktester: Phase 1 backtesting engine implementation.

Orchestrates TradeLog → daily PnL decomposition → equity curve assembly.
See ADR-002, ADR-003, ADR-005 and Section 7.1 of the Module 5 Transfer
Package for the PnL decomposition derivation.
"""

from __future__ import annotations

import datetime
import logging
import subprocess
from typing import Any

import pandas as pd

from src.backtesting.costs import CostModel
from src.backtesting.run_manager import generate_run_id
from src.backtesting.sizing import FixedNotionalSizer
from src.backtesting.trade_log import TradeLog
from src.core import provenance
from src.core.config import Config
from src.core.registry import BacktestEngine, PositionSizer
from src.core.types import BacktestMetadata, BacktestResult, TradeRecord


class VectorizedBacktester(BacktestEngine):
    """Phase 1 vectorized backtesting engine. See ADR-003.

    Constructor binds asset/strategy/signal context and reads cost,
    sizing, and asset metadata from Config. run() then executes the
    backtest given just PositionSignal + OHLCV, per the frozen
    BacktestEngine.run() interface.
    """

    def __init__(
        self,
        asset: str,
        strategy_name: str,
        signal_name: str,
        config: Config,
        parameters: dict[str, Any] | None = None,
        initial_capital_usd: float = 1_000_000.0,
        sizer: PositionSizer | None = None,
    ) -> None:
        """Initialise VectorizedBacktester.

        Args:
            asset: Asset identifier (e.g., "gold").
            strategy_name: Strategy identifier, used in run_id and metadata.
            signal_name: Signal identifier, used in metadata.
            config: Config instance from Config.load().
            parameters: Strategy parameter snapshot for BacktestMetadata.
            initial_capital_usd: Starting capital account value. Default
                1,000,000.0 per Architecture Section 11. This is a
                constructor parameter (not a config.yaml key) because no
                such key exists in the frozen Module 1 config.yaml
                schema — see Module 5 Transfer Package Section 8 for the
                resolution rationale.
        """
        self._asset = asset
        self._strategy_name = strategy_name
        self._signal_name = signal_name
        self._config = config
        self._parameters = parameters or {}
        self._initial_capital_usd = initial_capital_usd

        asset_metadata = config.assets[asset]
        self._contract_multiplier = float(asset_metadata["contract_multiplier"])
        self._tick_value = float(asset_metadata["tick_value"])

        self._cost_model = CostModel(
            commission_per_trade=config.costs["default_commission_usd"],
            slippage_ticks=config.costs["default_slippage_ticks"],
        )
        if sizer is not None:
            self._sizer = sizer
        else:
            self._sizer = FixedNotionalSizer(
                notional_usd=config.sizing["fixed_notional_usd"]
            )
        self._logger = logging.getLogger(__name__)

    def run(self, position_signal: pd.Series, ohlcv: pd.DataFrame) -> BacktestResult:
        """Execute the backtest and assemble BacktestResult.

        Args:
            position_signal: PositionSignal Series, values in {-1, 0, +1}.
            ohlcv: NormalizedOHLCV DataFrame.

        Returns:
            BacktestResult with trades, equity_curve, positions, pnl_series,
            metadata populated. signal_evaluation is None — Module 6's
            orchestration layer attaches it.
        """
        run_id = generate_run_id(self._strategy_name, self._asset)

        trade_log = TradeLog(
            run_id=run_id,
            asset=self._asset,
            cost_model=self._cost_model,
            position_sizer=self._sizer,
            contract_multiplier=self._contract_multiplier,
            tick_value=self._tick_value,
            initial_capital_usd=self._initial_capital_usd,
        )
        self._sizer.configure(
            ohlcv
        )  # no-op for FixedNotionalSizer; pre-computes vol for VolatilityScaledSizer
        trades = trade_log.build(position_signal, ohlcv)

        pnl_series = self._build_pnl_series(trades, ohlcv)
        pnl_series.name = "pnl"
        positions = self._build_positions_series(trades, ohlcv)
        positions.name = "position"
        equity_curve = self._initial_capital_usd + pnl_series.cumsum()
        equity_curve.name = "equity"

        _prov = provenance.capture()
        metadata = BacktestMetadata(
            run_id=run_id,
            asset=self._asset,
            strategy_name=self._strategy_name,
            signal_name=self._signal_name,
            parameters=self._parameters,
            data_source=str(ohlcv.attrs.get("source", "unknown")),
            data_start=ohlcv.index.min().date(),
            data_end=ohlcv.index.max().date(),
            initial_capital_usd=self._initial_capital_usd,
            cost_model_params={
                "commission_per_trade": self._config.costs["default_commission_usd"],
                "slippage_ticks": self._config.costs["default_slippage_ticks"],
            },
            sizing_model_params={
                "method": self._config.sizing["method"],
                "fixed_notional_usd": self._config.sizing["fixed_notional_usd"],
            },
            executed_at=datetime.datetime.now(tz=datetime.UTC),
            git_commit_hash=self._get_git_commit_hash(),
            git_sha=_prov["git_sha"],
            dirty_flag=_prov["dirty_flag"],
            package_versions=_prov["package_versions"],
        )

        self._logger.info(
            "VectorizedBacktester: run %s complete — %d trades, final equity %.2f",
            run_id,
            len(trades),
            float(equity_curve.iloc[-1])
            if len(equity_curve)
            else self._initial_capital_usd,
        )

        return BacktestResult(
            run_id=run_id,
            asset=self._asset,
            trades=trades,
            equity_curve=equity_curve,
            positions=positions,
            pnl_series=pnl_series,
            metadata=metadata,
            signal_evaluation=None,
        )

    def _build_pnl_series(
        self,
        trades: list[TradeRecord],
        ohlcv: pd.DataFrame,
    ) -> pd.Series:
        """Decompose trade-level PnL into a daily series. See Section 7.1.

        The cumulative sum of the returned Series equals the sum of
        every trade's gross_pnl minus transaction_cost (i.e. net_pnl),
        by the telescoping property derived in Section 7.1.

        Args:
            trades: List of TradeRecord from TradeLog.build().
            ohlcv: NormalizedOHLCV DataFrame, used for daily close prices.

        Returns:
            pd.Series of daily net PnL, same index as ohlcv, float64.
            Transaction cost is subtracted on the entry day's mark.
        """
        pnl = pd.Series(0.0, index=ohlcv.index, dtype="float64")
        close = ohlcv["close"]

        for trade in trades:
            entry_pos = ohlcv.index.get_loc(pd.Timestamp(trade.entry_date, tz="UTC"))
            direction = trade.direction
            size = trade.size_notional
            entry_price = trade.entry_price

            if trade.force_closed:
                end_pos = ohlcv.index.get_loc(pd.Timestamp(trade.exit_date, tz="UTC"))
            else:
                exit_pos = ohlcv.index.get_loc(pd.Timestamp(trade.exit_date, tz="UTC"))
                end_pos = exit_pos - 1

            # Entry day mark: entry_price -> close[entry_day]
            pnl.iloc[entry_pos] += (
                direction * size * (close.iloc[entry_pos] - entry_price) / entry_price
            )

            # Continuation days: close[d-1] -> close[d]
            for pos in range(entry_pos + 1, end_pos + 1):
                pnl.iloc[pos] += (
                    direction
                    * size
                    * (close.iloc[pos] - close.iloc[pos - 1])
                    / entry_price
                )

            # Exit day mark (non-force-closed trades only — force-closed
            # already fully captured by the entry/continuation marks above)
            if not trade.force_closed:
                exit_pos = end_pos + 1
                pnl.iloc[exit_pos] += (
                    direction
                    * size
                    * (trade.exit_price - close.iloc[end_pos])
                    / entry_price
                )

            # Transaction cost applied on the entry day per trade
            pnl.iloc[entry_pos] -= trade.transaction_cost

        return pnl

    def _build_positions_series(
        self,
        trades: list[TradeRecord],
        ohlcv: pd.DataFrame,
    ) -> pd.Series:
        """Build the daily notional position exposure series.

        Args:
            trades: List of TradeRecord from TradeLog.build().
            ohlcv: NormalizedOHLCV DataFrame.

        Returns:
            pd.Series of signed notional exposure per day. 0.0 when flat.
        """
        positions = pd.Series(0.0, index=ohlcv.index, dtype="float64")
        for trade in trades:
            entry_pos = ohlcv.index.get_loc(pd.Timestamp(trade.entry_date, tz="UTC"))
            end_pos = entry_pos + trade.duration_bars - 1
            notional = trade.direction * trade.size_notional
            positions.iloc[entry_pos : end_pos + 1] = notional
        return positions

    @staticmethod
    def _get_git_commit_hash() -> str:
        """Return the current git commit hash, or 'unknown' if unavailable."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
                check=True,
            )
            return result.stdout.strip()
        except Exception:  # noqa: BLE001
            return "unknown"
