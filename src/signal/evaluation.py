"""SignalEvaluator: IC, ICIR, signal decay, and turnover computation.

Signal evaluation is a PRECONDITION for backtesting per ADR-007.
IC analysis determines whether a backtest is warranted.
Never run a backtest without first evaluating signal quality here.
"""

from __future__ import annotations

import logging
from typing import ClassVar

import numpy as np
import pandas as pd

from src.core.types import SignalEvaluation


class SignalEvaluator:
    """Evaluates RawSignal quality using IC, ICIR, decay, and turnover.

    All metrics use 1-bar forward log returns: log(close[t+1] / close[t]).
    IC = Pearson correlation(signal[t], forward_return[t+1]).
    ICIR = mean(rolling_IC) / std(rolling_IC).
    Decay = IC at horizons {1, 2, 5, 10, 20} bars forward.

    See ADR-007 and Architecture Section 10.
    """

    HORIZONS: ClassVar[list[int]] = [1, 2, 5, 10, 20]

    def __init__(self, asset: str, ic_rolling_window: int = 63) -> None:
        """Initialise SignalEvaluator for a specific asset.

        Args:
            asset: Asset identifier for SignalEvaluation metadata (e.g., "gold").
            ic_rolling_window: Rolling window for ICIR computation. Default 63 bars.
        """
        self._asset = asset
        self._ic_rolling_window = ic_rolling_window
        self._logger = logging.getLogger(__name__)

    def evaluate(
        self,
        raw_signal: pd.Series,
        ohlcv: pd.DataFrame,
    ) -> SignalEvaluation:
        """Evaluate RawSignal predictive quality against forward returns.

        Args:
            raw_signal: RawSignal Series from a SignalGenerator. Must share
                the same DatetimeIndex (or overlap) with ohlcv.
            ohlcv: NormalizedOHLCV DataFrame from DataLoader.load(). Used
                to compute forward log returns.

        Returns:
            SignalEvaluation with IC, ICIR, ic_decay, and turnover populated.

        Raises:
            ValueError: If fewer than 10 valid aligned observations exist.
        """
        fwd_1 = self._forward_return(ohlcv, horizon=1)

        # Align signal and 1-bar forward return; drop NaN from both
        signal_aligned, fwd_aligned = raw_signal.align(fwd_1, join="inner")
        valid = signal_aligned.notna() & fwd_aligned.notna()

        if valid.sum() < 10:
            raise ValueError(
                f"Insufficient valid observations for IC computation: "
                f"{valid.sum()} rows after alignment and NaN removal. "
                f"Minimum 10 required."
            )

        s_valid = signal_aligned[valid]
        r_valid = fwd_aligned[valid]

        ic = float(s_valid.corr(r_valid))
        self._logger.info(
            "SignalEvaluator: IC=%.4f for signal '%s' on %s",
            ic,
            raw_signal.name or "unnamed",
            self._asset,
        )

        # Rolling IC for ICIR
        rolling_ic = signal_aligned.rolling(
            window=self._ic_rolling_window,
            min_periods=max(10, self._ic_rolling_window // 2),
        ).corr(fwd_aligned)

        ic_mean = float(rolling_ic.mean())
        ic_std = float(rolling_ic.std())
        icir = ic_mean / (ic_std + 1e-10) if ic_std > 1e-10 else 0.0

        # IC decay across multiple horizons
        ic_decay: dict[int, float] = {}
        for h in self.HORIZONS:
            fwd_h = self._forward_return(ohlcv, horizon=h)
            s_h, r_h = raw_signal.align(fwd_h, join="inner")
            valid_h = s_h.notna() & r_h.notna()
            if valid_h.sum() >= 10:
                ic_decay[h] = float(s_h[valid_h].corr(r_h[valid_h]))
            else:
                ic_decay[h] = float("nan")
                self._logger.debug(
                    "SignalEvaluator: insufficient data for IC at horizon %d", h
                )

        # Turnover: discretize signal at threshold=0 then compute mean abs change
        position = (raw_signal > 0).astype(int) - (raw_signal < 0).astype(int)
        turnover = float(position.diff().abs().mean())

        return SignalEvaluation(
            signal_name=raw_signal.name or "unnamed",
            asset=self._asset,
            ic=ic,
            icir=icir,
            ic_decay=ic_decay,
            turnover=turnover,
            ic_rolling_window=self._ic_rolling_window,
            evaluation_start=ohlcv.index.min().date(),
            evaluation_end=ohlcv.index.max().date(),
        )

    def compute_rolling_ic(
        self,
        strategy_name: str,
        parameters: dict,
    ) -> pd.Series:
        """Compute rolling information coefficient for this evaluator's asset.

        Rolling IC at bar t = Pearson correlation between the raw signal
        and the 1-bar-ahead forward return over the preceding
        self._ic_rolling_window bars.

        Uses RawSignal (not PositionSignal) for consistency with the static IC
        definition: Pearson(RawSignal[t], forward_return[t+1]). Rolling IC values
        are therefore directly comparable to the static IC scalar.

        NaN for the first ic_rolling_window-1 bars (insufficient history).
        NaN where signal variance is zero over the window.

        Args:
            strategy_name: Strategy name (e.g. 'ema_crossover').
            parameters: Strategy parameter dict (e.g. {'fast_period': 50}).

        Returns:
            pd.Series of rolling IC values indexed by DatetimeIndex (UTC).
            Values in [-1.0, 1.0] or NaN. Series named 'rolling_ic'.

        Raises:
            ValueError: If window exceeds available aligned bars.
        """
        from src.backtesting.pipeline_builder import (  # noqa: PLC0415
            build_pipeline_components,
        )
        from src.core.config import Config  # noqa: PLC0415
        from src.data.loader import DataLoader  # noqa: PLC0415
        from src.research.pipeline import FeaturePipeline  # noqa: PLC0415

        config = Config.load("config/")
        ohlcv = DataLoader(config).load(self._asset)

        # DEV-EM5-1: build_pipeline_components returns 2-tuple
        indicators, signal_generator = build_pipeline_components(
            strategy_name=strategy_name,
            parameters=parameters,
            config=config,
        )
        feature_pipeline = FeaturePipeline(indicators)
        feature_frame = feature_pipeline.compute(ohlcv, asset=self._asset)

        raw_signal = signal_generator.generate(feature_frame)

        # Forward return: close[t+1]/close[t] - 1, aligned to bar t
        forward_returns = ohlcv["close"].pct_change().shift(-1)

        aligned = pd.DataFrame(
            {"signal": raw_signal, "fwd_return": forward_returns},
            index=ohlcv.index,
        ).dropna()

        if len(aligned) < self._ic_rolling_window:
            raise ValueError(
                f"Insufficient data: {len(aligned)} bars < "
                f"window={self._ic_rolling_window}. "
                f"Reduce window or ingest more data for '{self._asset}'."
            )

        rolling_ic = (
            aligned["signal"]
            .rolling(
                window=self._ic_rolling_window,
                min_periods=self._ic_rolling_window,
            )
            .corr(aligned["fwd_return"])
        )

        return rolling_ic.rename("rolling_ic")

    def _forward_return(self, ohlcv: pd.DataFrame, horizon: int = 1) -> pd.Series:
        """Compute h-period forward log return at each bar t.

        forward_return[t] = log(close[t+h] / close[t])
                          = log(close).diff(horizon).shift(-horizon)

        Args:
            ohlcv: NormalizedOHLCV DataFrame with a "close" column.
            horizon: Number of bars forward. Default 1.

        Returns:
            pd.Series of forward log returns. NaN at the last h bars.
        """
        log_close = np.log(ohlcv["close"])
        return log_close.diff(horizon).shift(-horizon)
