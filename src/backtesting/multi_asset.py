"""MultiAssetRunner: runs VectorizedBacktester across multiple assets.

Implements the full research pipeline per asset (Steps 1–7 from Architecture
Section 10) and aggregates results into a MultiAssetBacktestResult.

Architecture: Layer 3 (Backtesting Engine) — Phase 3 addition.
Does NOT do capital allocation, risk budgeting, or portfolio construction.
See Module 15 (PortfolioPerformanceEngine) for portfolio-level metrics.

See ADR-010 (Multi-Asset Research Scope and Phasing).
"""

from __future__ import annotations

import logging
import math
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pandas as pd

from src.backtesting.engine import VectorizedBacktester
from src.core.config import Config
from src.core.types import BacktestResult, MultiAssetBacktestResult
from src.data.loader import DataLoader
from src.research.momentum import Momentum
from src.research.moving_averages import EMA
from src.research.oscillators import RSI
from src.research.pipeline import FeaturePipeline
from src.signal.breakout import DonchianBreakoutSignal
from src.signal.evaluation import SignalEvaluator
from src.signal.position import PositionSignalConstructor
from src.signal.reversion import RSIReversionSignal
from src.signal.trend import EMACrossoverSignal, MomentumSignal

if TYPE_CHECKING:
    from src.core.registry import PositionSizer


class MultiAssetRunner:
    """Runs VectorizedBacktester across multiple assets with the same strategy.

    For each asset, executes the complete research pipeline:
        Step 1: Load OHLCV (DataLoader)
        Step 2: Build feature frame (FeaturePipeline)
        Step 3: Generate raw signal (SignalGenerator)
        Step 4: Evaluate IC (SignalEvaluator) — enforced per ADR-010
        Step 5: Construct position signal (PositionSignalConstructor)
        Step 6: Run backtest (VectorizedBacktester)
        Step 7: Attach signal evaluation to BacktestResult

    Aggregates per-asset results:
        - portfolio_equity_curve: sum of per-asset equity curves
        - portfolio_pnl_series: sum of per-asset PnL series

    Does NOT do:
        - Capital allocation or risk budgeting (Modules 16–17)
        - RunManager persistence (Module 15)
        - Portfolio-level metrics (Module 15)

    Technical debt TD-M14-A:
        _build_pipeline_components() duplicates the strategy->pipeline mapping
        from dashboard/pages/3_strategy_builder.py. Phase 3+ refactor:
        extract to src/backtesting/pipeline_builder.py for shared use.

    See Architecture Section 5 (Layer 3) and ADR-010.

    Usage:
        runner = MultiAssetRunner(config)
        result = runner.run(
            assets=["gold", "silver", "copper", "wti", "brent", "natural_gas"],
            strategy_name="ema_crossover",
            parameters={"fast_period": 50, "slow_period": 200},
        )
        print(f"Portfolio covers {result.n_assets} assets, {result.total_trades} trades")
    """

    def __init__(self, config: Config) -> None:
        """Initialise MultiAssetRunner.

        Args:
            config: Config instance from Config.load().
        """
        self._config = config
        self._loader = DataLoader(config)
        self._logger = logging.getLogger(__name__)

    def run(
        self,
        assets: list[str],
        strategy_name: str,
        parameters: dict[str, Any],
        sizer: PositionSizer | None = None,
        signal_threshold: float = 0.0,
    ) -> MultiAssetBacktestResult:
        """Run the strategy across all specified assets and aggregate results.

        Each asset is processed independently. If an asset's pipeline fails
        (insufficient data, unknown strategy, any exception), it is added to
        skipped_assets and the run continues. A ValueError is raised only if
        ALL assets fail.

        IC evaluation (Step 4) is run for each asset per ADR-010. Low IC
        (|IC| < 0.02) is logged as a warning but does NOT block the backtest
        — research transparency requires that all results are visible even for
        noisy signals. The signal_evaluation field on each BacktestResult
        carries the IC information for downstream analysis.

        Args:
            assets: List of platform asset identifiers (e.g. ['gold', 'silver']).
                Must not be empty.
            strategy_name: Strategy identifier matching strategies.yaml
                (ema_crossover | momentum | rsi_reversion | donchian_breakout).
            parameters: Strategy parameters applied identically to all assets.
                Must contain the required keys for the chosen strategy.
            sizer: Optional PositionSizer override. If None, uses FixedNotionalSizer
                from config (default $100,000/signal). Pass VolatilityScaledSizer
                for equal-vol contributions across assets.
            signal_threshold: Raw signal values within [-threshold, +threshold]
                produce a flat (0) position. Default 0.0 (no flat zone).

        Returns:
            MultiAssetBacktestResult with per-asset results and aggregated
            portfolio equity curve. skipped_assets may be non-empty if some
            assets failed.

        Raises:
            ValueError: If assets list is empty, or if all assets fail.
        """
        if not assets:
            raise ValueError("MultiAssetRunner.run(): assets list must not be empty.")

        run_id = self._generate_portfolio_run_id(strategy_name)
        executed_at = datetime.now(UTC)

        asset_results: dict[str, BacktestResult] = {}
        skipped_assets: list[str] = []

        self._logger.info(
            "MultiAssetRunner: starting portfolio run %s — strategy=%s assets=%s",
            run_id,
            strategy_name,
            assets,
        )

        for asset in assets:
            try:
                result = self._run_single_asset(
                    asset=asset,
                    strategy_name=strategy_name,
                    parameters=parameters,
                    sizer=sizer,
                    signal_threshold=signal_threshold,
                )
                asset_results[asset] = result
                n_trades = len(result.trades)
                self._logger.info(
                    "MultiAssetRunner: %s complete — %d trades",
                    asset,
                    n_trades,
                )
            except Exception as exc:  # noqa: BLE001
                skipped_assets.append(asset)
                self._logger.warning(
                    "MultiAssetRunner: skipping %s — %s: %s",
                    asset,
                    type(exc).__name__,
                    exc,
                )

        if not asset_results:
            raise ValueError(
                f"MultiAssetRunner: all {len(assets)} requested assets failed. "
                f"Skipped: {skipped_assets}. "
                "Check data availability (data/processed/continuous/) "
                "and strategy parameters."
            )

        portfolio_equity, portfolio_pnl = self._aggregate_portfolio(asset_results)

        self._logger.info(
            "MultiAssetRunner: portfolio run %s complete — "
            "%d/%d assets successful (%d skipped)",
            run_id,
            len(asset_results),
            len(assets),
            len(skipped_assets),
        )

        first_result = next(iter(asset_results.values()))
        signal_name = first_result.metadata.signal_name

        return MultiAssetBacktestResult(
            strategy_name=strategy_name,
            signal_name=signal_name,
            parameters=parameters,
            assets=list(asset_results.keys()),
            skipped_assets=skipped_assets,
            run_id=run_id,
            executed_at=executed_at,
            asset_results=asset_results,
            portfolio_equity_curve=portfolio_equity,
            portfolio_pnl_series=portfolio_pnl,
        )

    def _run_single_asset(
        self,
        asset: str,
        strategy_name: str,
        parameters: dict[str, Any],
        sizer: PositionSizer | None,
        signal_threshold: float,
    ) -> BacktestResult:
        """Execute the complete research pipeline for one asset.

        Raises any exception from any pipeline step — caller catches and
        records as a skipped asset.
        """
        # Step 1: Load OHLCV
        ohlcv = self._loader.load(asset)

        # Step 2: Build feature frame
        indicators, signal_gen = self._build_pipeline_components(
            strategy_name, parameters
        )
        ff = FeaturePipeline(indicators).compute(ohlcv, asset=asset)

        # Step 3: Generate raw signal
        raw_signal = signal_gen.generate(ff)

        # Step 4: Evaluate signal quality (ADR-010 requirement)
        signal_evaluation = None
        try:
            signal_evaluation = SignalEvaluator(asset).evaluate(raw_signal, ohlcv)
            if (
                not math.isnan(signal_evaluation.ic)
                and abs(signal_evaluation.ic) < 0.02
            ):
                self._logger.warning(
                    "MultiAssetRunner: %s IC=%.4f below 0.02 threshold — "
                    "signal noise level; proceeding (research transparency per ADR-010)",
                    asset,
                    signal_evaluation.ic,
                )
        except ValueError:
            self._logger.debug(
                "MultiAssetRunner: %s — IC evaluation skipped (insufficient data)",
                asset,
            )

        # Step 5: Construct position signal
        position_signal = PositionSignalConstructor().build(
            raw_signal, threshold=signal_threshold
        )

        # Step 6: Run backtest
        result = VectorizedBacktester(
            asset=asset,
            strategy_name=strategy_name,
            signal_name=signal_gen.name,
            config=self._config,
            parameters=parameters,
            sizer=sizer,
        ).run(position_signal, ohlcv)

        # Step 7: Attach signal evaluation
        result.signal_evaluation = signal_evaluation

        return result

    def _build_pipeline_components(
        self,
        strategy_name: str,
        parameters: dict[str, Any],
    ) -> tuple[list, Any]:
        """Return (indicators, signal_generator) for the given strategy and params.

        Technical debt TD-M14-A: this mapping duplicates logic in
        dashboard/pages/3_strategy_builder.py._build_pipeline_components().
        Refactor to src/backtesting/pipeline_builder.py in a future module.

        Args:
            strategy_name: One of ema_crossover | momentum | rsi_reversion |
                donchian_breakout.
            parameters: Parameter dict matching the strategy's schema.

        Returns:
            (indicators: list[Indicator], signal_gen: SignalGenerator)

        Raises:
            ValueError: If strategy_name is not recognized.
        """
        if strategy_name == "ema_crossover":
            fast = int(parameters["fast_period"])
            slow = int(parameters["slow_period"])
            return (
                [EMA(period=fast), EMA(period=slow)],
                EMACrossoverSignal(fast_period=fast, slow_period=slow),
            )

        if strategy_name == "momentum":
            lookback = int(parameters["lookback_period"])
            z_window = int(parameters.get("z_score_window", 63))
            return (
                [Momentum(lookback=lookback)],
                MomentumSignal(lookback=lookback, z_score_window=z_window),
            )

        if strategy_name == "rsi_reversion":
            period = int(parameters["period"])
            return (
                [RSI(period=period)],
                RSIReversionSignal(period=period),
            )

        if strategy_name == "donchian_breakout":
            channel = int(parameters["channel_period"])
            return (
                [],
                DonchianBreakoutSignal(channel_period=channel),
            )

        raise ValueError(
            f"MultiAssetRunner: unknown strategy '{strategy_name}'. "
            "Valid: ema_crossover, momentum, rsi_reversion, donchian_breakout"
        )

    def _aggregate_portfolio(
        self,
        asset_results: dict[str, BacktestResult],
    ) -> tuple[pd.Series, pd.Series]:
        """Aggregate per-asset equity curves and PnL series into a portfolio.

        Alignment strategy: inner join on dates (intersection). Assets with
        different data start dates will produce a portfolio computed only over
        the common date range. Missing trade dates (flat periods) produce
        zero PnL and carry-forward equity.

        Args:
            asset_results: Dict of asset -> BacktestResult for all successful assets.

        Returns:
            (portfolio_equity_curve, portfolio_pnl_series) as pd.Series.
        """
        equity_dict = {
            asset: result.equity_curve for asset, result in asset_results.items()
        }
        pnl_dict = {asset: result.pnl_series for asset, result in asset_results.items()}

        equity_df = pd.DataFrame(equity_dict)
        equity_df = equity_df.dropna()

        if equity_df.empty:
            self._logger.warning(
                "MultiAssetRunner: portfolio equity empty after alignment — "
                "no overlapping date range across all assets"
            )
            equity_df = pd.DataFrame(equity_dict).ffill().bfill()

        pnl_df = pd.DataFrame(pnl_dict)
        pnl_df = pnl_df.reindex(equity_df.index).fillna(0.0)

        portfolio_equity = equity_df.sum(axis=1)
        portfolio_equity.name = "portfolio_equity"

        portfolio_pnl = pnl_df.sum(axis=1)
        portfolio_pnl.name = "portfolio_pnl"

        return portfolio_equity, portfolio_pnl

    @staticmethod
    def _generate_portfolio_run_id(strategy_name: str) -> str:
        """Generate a portfolio-level run identifier.

        Format: YYYYMMDD_HHMMSS_portfolio_{strategy_name}

        This is distinct from per-asset run IDs (YYYYMMDD_HHMMSS_{strategy}_{asset}).
        Portfolio runs are not persisted by MultiAssetRunner — that is Module 15.
        """
        ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        return f"{ts}_portfolio_{strategy_name}"
