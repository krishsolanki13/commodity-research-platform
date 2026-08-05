"""Pipeline construction utilities for signal research and backtesting.

Extracted from MultiAssetRunner._build_pipeline_components() (TD-M14-A).
Previously duplicated between multi_asset.py and dashboard/pages/3_strategy_builder.py.
Both callers now import build_pipeline_components() from this module.
"""

from __future__ import annotations

from typing import Any

from src.core.config import Config
from src.research.momentum import Momentum
from src.research.moving_averages import EMA
from src.research.oscillators import RSI
from src.signal.breakout import DonchianBreakoutSignal
from src.signal.reversion import RSIReversionSignal
from src.signal.trend import EMACrossoverSignal, MomentumSignal


def build_pipeline_components(
    strategy_name: str,
    parameters: dict[str, Any],
    config: Config,
) -> tuple[list, Any]:
    """Return (indicators, signal_generator) for the given strategy and params.

    Args:
        strategy_name: One of ema_crossover | momentum | rsi_reversion |
            donchian_breakout | carry.
        parameters: Parameter dict matching the strategy's schema.
        config: Platform Config (used by carry; reserved for others).

    Returns:
        (indicators: list[Indicator], signal_gen: SignalGenerator)

    Raises:
        ValueError: If strategy_name is not recognized.
    """
    _ = config  # reserved for future config-driven strategy defaults

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

    if strategy_name == "carry":
        from src.signal.carry import CarrySignal  # noqa: PLC0415

        indicators: list = []
        signal_gen = CarrySignal(
            config=config,
            threshold=parameters.get("threshold", 0.0),
            n_contracts=int(parameters.get("n_contracts", 4)),
        )
        return indicators, signal_gen

    if strategy_name == "wti_brent_spread":
        from src.signal.spread import WTIBrentSpreadSignal  # noqa: PLC0415

        indicators = []
        signal_gen = WTIBrentSpreadSignal(
            config=config,
            lookback=int(parameters.get("lookback", 63)),
            threshold=float(parameters.get("threshold", 1.0)),
        )
        return indicators, signal_gen

    if strategy_name == "cot_positioning":
        from src.signal.cot import COTPositioningSignal  # noqa: PLC0415

        indicators = []
        signal_gen = COTPositioningSignal(
            config=config,
            upper_pct=float(parameters.get("upper_pct", 80.0)),
            lower_pct=float(parameters.get("lower_pct", 20.0)),
        )
        return indicators, signal_gen

    if strategy_name == "eia_inventory":
        from src.signal.eia import EIAInventorySignal  # noqa: PLC0415

        indicators = []
        signal_gen = EIAInventorySignal(
            config=config,
            threshold=float(parameters.get("threshold", 1.0)),
        )
        return indicators, signal_gen

    raise ValueError(
        f"MultiAssetRunner: unknown strategy '{strategy_name}'. "
        "Valid: ema_crossover, momentum, rsi_reversion, donchian_breakout, carry"
    )
