"""Walk-forward out-of-sample validation with embargo periods."""

from __future__ import annotations

import datetime
import logging
import math
from typing import TYPE_CHECKING

import pandas as pd

from src.core.provenance import capture
from src.core.types import (
    TrainTestSplit,
    ValidationReport,
    WalkForwardFold,
)
from src.validation.inference import (
    deflated_sharpe_ratio,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
    sharpe_se,
)

if TYPE_CHECKING:
    from src.core.config import Config
    from src.performance.report import PerformanceEngine

logger = logging.getLogger(__name__)


def walk_forward_split(
    dates: pd.DatetimeIndex,
    n_splits: int = 5,
    embargo_bars: int = 10,
    min_train_bars: int = 252,
) -> list[TrainTestSplit]:
    """Produce train/test splits for walk-forward validation.

    Splits are expanding-window: each fold trains on all data up to
    a cutoff date, then tests on the next window. embargo_bars bars
    are excluded between train end and test start to prevent leakage
    from autocorrelated consecutive returns.

    Args:
        dates: Full DatetimeIndex of the strategy's OHLCV data.
        n_splits: Number of train/test folds.
        embargo_bars: Bars to exclude between train and test windows.
        min_train_bars: Minimum training bars required.

    Returns:
        List of TrainTestSplit objects ordered by fold_idx.

    Raises:
        ValueError: If insufficient bars for the requested splits.
    """
    n = len(dates)
    # Reserve min_train_bars + embargo, then divide the remainder into n_splits
    # equal test windows (expanding train grows by test_size each fold).
    available = n - min_train_bars - embargo_bars
    if n_splits < 1 or available < n_splits:
        raise ValueError(
            f"Insufficient bars ({n}) for {n_splits} splits with "
            f"min_train_bars={min_train_bars}, embargo_bars={embargo_bars}, "
            f"test_size={max(available // n_splits, 0) if n_splits else 0}."
        )
    test_size = available // n_splits
    if min_train_bars + embargo_bars + test_size * n_splits > n:
        raise ValueError(
            f"Insufficient bars ({n}) for {n_splits} splits with "
            f"min_train_bars={min_train_bars}, embargo_bars={embargo_bars}, "
            f"test_size={test_size}."
        )

    splits: list[TrainTestSplit] = []
    for fold in range(n_splits):
        # Expanding training window
        train_end_idx = min_train_bars + fold * test_size - 1
        test_start_idx = train_end_idx + 1 + embargo_bars
        test_end_idx = test_start_idx + test_size - 1

        if test_end_idx >= n:
            break

        splits.append(
            TrainTestSplit(
                fold_idx=fold,
                train_start=dates[0].date(),
                train_end=dates[train_end_idx].date(),
                test_start=dates[test_start_idx].date(),
                test_end=dates[test_end_idx].date(),
                n_train_bars=train_end_idx + 1,
                n_test_bars=test_size,
                embargo_bars=embargo_bars,
            )
        )

    if not splits:
        raise ValueError("No valid splits produced — check data size and parameters.")

    return splits


class WalkForwardValidator:
    """Orchestrates walk-forward out-of-sample validation.

    Calls VectorizedBacktester on each fold's data subset, collects
    results, and computes statistical inference metrics (PSR, DSR).

    The same signal generator with the same parameters is used on both
    train and test windows. Walk-forward splits are applied to the
    pre-computed position_signal Series. Known limitation: signal features
    are computed on the full history before splitting, so the signal is
    not strictly walk-forward at the feature level. Acceptable for EM5.
    """

    def __init__(self, config: Config) -> None:
        self._config = config
        self._logger = logging.getLogger(__name__)

    def validate(
        self,
        asset: str,
        strategy_name: str,
        parameters: dict,
        n_splits: int = 5,
        embargo_bars: int = 10,
        n_trials: int = 1,
    ) -> ValidationReport:
        """Run walk-forward validation and return a complete ValidationReport.

        Args:
            asset: Asset identifier (e.g. 'gold').
            strategy_name: Strategy name (e.g. 'ema_crossover').
            parameters: Strategy parameter dict.
            n_splits: Number of walk-forward folds.
            embargo_bars: Bars excluded between train and test.
            n_trials: Trial count from MLflow (for DSR).

        Returns:
            ValidationReport with fold results and statistical inference.
        """
        from src.backtesting.engine import VectorizedBacktester  # noqa: PLC0415
        from src.backtesting.pipeline_builder import (
            build_pipeline_components,  # noqa: PLC0415
        )
        from src.data.loader import DataLoader  # noqa: PLC0415
        from src.performance.report import PerformanceEngine  # noqa: PLC0415
        from src.research.feature_frame import FeatureFrame  # noqa: PLC0415
        from src.research.pipeline import FeaturePipeline  # noqa: PLC0415
        from src.signal.position import PositionSignalConstructor  # noqa: PLC0415

        self._logger.info(
            "WalkForwardValidator: %s/%s — %d splits, %d embargo bars, %d trials",
            asset,
            strategy_name,
            n_splits,
            embargo_bars,
            n_trials,
        )

        # Load full OHLCV
        ohlcv = DataLoader(self._config).load(asset)

        # Build pipeline components once (signal generator is stateless)
        indicators, signal_generator = build_pipeline_components(
            strategy_name=strategy_name,
            parameters=parameters,
            config=self._config,
        )

        # Generate position signal on full dataset
        if indicators:
            feature_frame = FeaturePipeline(indicators).compute(ohlcv, asset=asset)
        else:
            feature_frame = FeatureFrame(ohlcv, feature_specs=[], asset=asset)
        raw_signal = signal_generator.generate(feature_frame)
        position_signal = PositionSignalConstructor().build(raw_signal, threshold=0.0)

        # Full in-sample run (for PSR/DSR statistical inference on all data)
        full_backtester = VectorizedBacktester(
            asset=asset,
            strategy_name=strategy_name,
            signal_name=signal_generator.name,
            config=self._config,
            parameters=parameters,
        )
        full_result = full_backtester.run(position_signal, ohlcv)
        full_report = PerformanceEngine().compute(full_result)

        # Daily returns from the full equity curve — used for Sharpe SE / PSR / DSR
        full_returns = full_result.equity_curve.pct_change().dropna()

        # Walk-forward splits
        splits = walk_forward_split(
            dates=ohlcv.index,
            n_splits=n_splits,
            embargo_bars=embargo_bars,
        )

        # Single PerformanceEngine instance for all folds (stateless; reuse is safe)
        fold_perf_engine = PerformanceEngine()

        # Run each fold
        folds: list[WalkForwardFold] = []
        for split in splits:
            fold = self._run_fold(
                split=split,
                ohlcv=ohlcv,
                position_signal=position_signal,
                asset=asset,
                strategy_name=strategy_name,
                signal_generator=signal_generator,
                parameters=parameters,
                perf_engine=fold_perf_engine,
            )
            folds.append(fold)
            self._logger.debug(
                "Fold %d: train_sharpe=%.3f  test_sharpe=%.3f",
                split.fold_idx,
                fold.train_sharpe,
                fold.test_sharpe,
            )

        # Aggregate fold results — skip folds with NaN test Sharpe
        valid_folds = [f for f in folds if not math.isnan(f.test_sharpe)]
        outsample_sharpe = (
            float(sum(f.test_sharpe for f in valid_folds) / len(valid_folds))
            if valid_folds
            else float("nan")
        )
        outsample_return = (
            float(sum(f.test_return for f in valid_folds) / len(valid_folds))
            if valid_folds
            else float("nan")
        )
        valid_ratios = [
            f.overfitting_ratio for f in folds if not math.isnan(f.overfitting_ratio)
        ]
        mean_overfitting = (
            float(sum(valid_ratios) / len(valid_ratios))
            if valid_ratios
            else float("nan")
        )

        # Statistical inference on full in-sample returns
        se = sharpe_se(full_returns)
        psr = probabilistic_sharpe_ratio(full_returns, sr_benchmark=0.0)
        sr_bench = expected_max_sharpe(n_trials)
        dsr = deflated_sharpe_ratio(full_returns, n_trials=n_trials)

        # Unique run identifier
        now = datetime.datetime.now(datetime.UTC)
        validation_run_id = (
            f"{now.strftime('%Y%m%d_%H%M%S')}_validation_{asset}_{strategy_name}"
        )

        _prov = capture()
        return ValidationReport(
            validation_run_id=validation_run_id,
            asset=asset,
            strategy_name=strategy_name,
            parameters=parameters,
            n_splits=len(splits),
            embargo_bars=embargo_bars,
            computation_date=datetime.date.today(),
            folds=folds,
            insample_sharpe=float(
                full_report.scalar_metrics.get("sharpe", float("nan"))
            ),
            outsample_sharpe=outsample_sharpe,
            insample_return=float(
                full_report.scalar_metrics.get("total_return", float("nan"))
            ),
            outsample_return=outsample_return,
            overfitting_ratio=mean_overfitting,
            sharpe_se=se,
            psr=psr,
            n_trials=n_trials,
            sr_benchmark=sr_bench,
            dsr=dsr,
            is_significant=dsr >= 0.95,
            dsr_threshold=0.95,
            git_sha=_prov["git_sha"],
            dirty_flag=_prov["dirty_flag"],
            package_versions=_prov["package_versions"],
        )

    def _run_fold(
        self,
        split: TrainTestSplit,
        ohlcv: pd.DataFrame,
        position_signal: pd.Series,
        asset: str,
        strategy_name: str,
        signal_generator: object,
        parameters: dict,
        perf_engine: PerformanceEngine,
    ) -> WalkForwardFold:
        """Run one walk-forward fold and return per-fold metrics.

        The perf_engine parameter is a PerformanceEngine instance created
        once by validate() and reused across folds (it is stateless).
        scalar_metrics live on PerformanceReport, not on BacktestResult —
        _run_and_report calls perf_engine.compute(result) to obtain them.
        """
        from src.backtesting.engine import VectorizedBacktester  # noqa: PLC0415

        def _slice_df(
            df: pd.DataFrame, start: datetime.date, end: datetime.date
        ) -> pd.DataFrame:
            mask = (df.index.date >= start) & (df.index.date <= end)
            return df[mask]

        def _slice_series(
            s: pd.Series, start: datetime.date, end: datetime.date
        ) -> pd.Series:
            mask = (s.index.date >= start) & (s.index.date <= end)
            return s[mask]

        def _run_and_report(
            ohlcv_slice: pd.DataFrame, sig_slice: pd.Series
        ) -> dict[str, float | int]:
            if len(ohlcv_slice) < 20 or len(sig_slice) < 20:
                return {
                    "sharpe": float("nan"),
                    "total_return": float("nan"),
                    "max_drawdown": float("nan"),
                    "n_trades": 0,
                }
            try:
                backtester = VectorizedBacktester(
                    asset=asset,
                    strategy_name=strategy_name,
                    signal_name=getattr(signal_generator, "name", strategy_name),
                    config=self._config,
                    parameters=parameters,
                )
                result = backtester.run(sig_slice, ohlcv_slice)

                # FIX (Issue 2): scalar_metrics is on PerformanceReport, not BacktestResult.
                # The original spec used getattr(result, "scalar_metrics", {}) which returns {}
                # silently. perf_engine is in the closure scope — call compute() here.
                perf_report = perf_engine.compute(result)
                metrics = perf_report.scalar_metrics or {}

                return {
                    "sharpe": float(metrics.get("sharpe", float("nan"))),
                    "total_return": float(metrics.get("total_return", float("nan"))),
                    "max_drawdown": float(metrics.get("max_drawdown", float("nan"))),
                    "n_trades": len(result.trades) if hasattr(result, "trades") else 0,
                }
            except Exception as exc:  # noqa: BLE001
                self._logger.warning("Fold %d run failed: %s", split.fold_idx, exc)
                return {
                    "sharpe": float("nan"),
                    "total_return": float("nan"),
                    "max_drawdown": float("nan"),
                    "n_trades": 0,
                }

        # Slice OHLCV and position signal for train and test windows
        ohlcv_train = _slice_df(ohlcv, split.train_start, split.train_end)
        sig_train = _slice_series(position_signal, split.train_start, split.train_end)

        ohlcv_test = _slice_df(ohlcv, split.test_start, split.test_end)
        sig_test = _slice_series(position_signal, split.test_start, split.test_end)

        train_m = _run_and_report(ohlcv_train, sig_train)
        test_m = _run_and_report(ohlcv_test, sig_test)

        train_sharpe = train_m["sharpe"]
        test_sharpe = test_m["sharpe"]
        overfitting_ratio = (
            test_sharpe / train_sharpe
            if (not math.isnan(train_sharpe) and train_sharpe != 0)
            else float("nan")
        )

        return WalkForwardFold(
            split=split,
            train_sharpe=train_sharpe,
            test_sharpe=test_sharpe,
            train_return=train_m["total_return"],
            test_return=test_m["total_return"],
            train_max_dd=train_m["max_drawdown"],
            test_max_dd=test_m["max_drawdown"],
            train_n_trades=int(train_m["n_trades"]),
            test_n_trades=int(test_m["n_trades"]),
            overfitting_ratio=overfitting_ratio,
        )
