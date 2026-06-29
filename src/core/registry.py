"""Abstract base classes for all pluggable components in the research platform.

Defines interface contracts that layer implementations must satisfy.
Upper layers depend on these ABCs, not on concrete implementations.
See Architecture Section 5 for layer responsibility definitions.
"""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from typing import Any

import pandas as pd


class DataSource(ABC):
    """Abstract base for all data source implementations.

    Separates continuous futures series (for signal research and backtesting)
    from contract-level series (for term structure analysis). See ADR-001.
    """

    @abstractmethod
    def fetch(
        self,
        asset: str,
        start: datetime.date,
        end: datetime.date,
    ) -> pd.DataFrame:
        """Return raw OHLCV data for the specified asset and date range.

        Args:
            asset: Asset identifier (e.g., "gold").
            start: Inclusive start date.
            end: Inclusive end date.

        Returns:
            Raw DataFrame. Schema normalisation is performed by the
            Normalizer in Layer 0, not by DataSource implementations.

        See ADR-001 for the continuous vs. contract-level data decision.
        """

    @abstractmethod
    def available_assets(self) -> list[str]:
        """Return the list of asset identifiers available from this source."""


class Indicator(ABC):
    """Abstract base for all technical indicator implementations.

    Concrete indicators must implement column_name as a property and
    compute() as a method. The column_name property enforces the
    {indicator_name}_{primary_parameter} naming convention. See ADR-006.
    """

    @property
    @abstractmethod
    def column_name(self) -> str:
        """Return the output column name for this indicator.

        Must follow {indicator_name}_{primary_parameter} convention.
        Example: EMA(period=50) returns "ema_50". See ADR-006.
        """

    @property
    def parameters(self) -> dict[str, Any]:
        """Return indicator parameters for FeatureSpec serialization.

        Concrete indicators override this to return their constructor parameters.
        Default returns empty dict for backward compatibility.
        Example: EMA(period=50) returns {"period": 50}.
        """
        return {}

    @abstractmethod
    def compute(self, df: pd.DataFrame) -> pd.Series:
        """Compute the indicator from the input OHLCV DataFrame.

        Args:
            df: NormalizedOHLCV DataFrame from Layer 0.

        Returns:
            pd.Series indexed identically to df, named per column_name.
        """


class SignalGenerator(ABC):
    """Abstract base for all signal generator implementations.

    Implementations produce a RawSignal from a FeatureFrame. The
    PositionSignalConstructor subsequently discretises the RawSignal
    into {+1, 0, -1}. See ADR-007.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the signal identifier string."""

    @abstractmethod
    def generate(self, feature_frame: Any) -> pd.Series:
        """Generate a RawSignal from the input FeatureFrame.

        Args:
            feature_frame: FeatureFrame instance. Typed as Any to avoid
                circular import with src.research.feature_frame; typed
                correctly in concrete implementations in Module 4.

        Returns:
            RawSignal: float64 pd.Series with no look-ahead bias.
            See ADR-002 for the signal timing convention.
        """


class BacktestEngine(ABC):
    """Abstract base for backtesting engine implementations.

    Isolates the algorithm behind an engine-agnostic interface so that
    an event-driven engine can replace the vectorized engine in a future
    phase without modifying Layer 2 or Layer 4. See ADR-003.
    """

    @abstractmethod
    def run(
        self,
        position_signal: pd.Series,
        ohlcv: pd.DataFrame,
    ) -> "BacktestResult":  # type: ignore[name-defined]  # noqa: F821, UP037
        """Execute the strategy over historical data.

        Args:
            position_signal: PositionSignal Series ({+1, 0, -1}).
            ohlcv: NormalizedOHLCV DataFrame from Layer 0.

        Returns:
            BacktestResult with trades, equity curve, and PnL series.

        See ADR-003. Contract is engine-agnostic to support future
        substitution with an event-driven implementation.
        """


class PositionSizer(ABC):
    """Abstract base for position sizing implementations.

    Phase 1 uses FixedNotionalSizer. Phase 2 adds VolatilityScaledSizer.
    Both implement this interface. See ADR-005.
    """

    @abstractmethod
    def compute_size(
        self,
        signal: float,
        asset: str,
        equity: float,
    ) -> float:
        """Compute position size in USD notional.

        Args:
            signal: Raw signal value (used by volatility-scaled sizer
                in Phase 2 for signal-proportional sizing).
            asset: Asset identifier for asset-specific parameters.
            equity: Current capital account value in USD.

        Returns:
            Position size in USD notional. See ADR-005.
        """
