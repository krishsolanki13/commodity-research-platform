"""Abstract base class for continuous futures data sources.

Defines ContinuousDataSource as the intermediate ABC between the generic
DataSource interface and concrete Phase 1 implementations.
See ADR-001 for the continuous vs. contract-level data separation decision.
"""

from __future__ import annotations

from abc import ABC

from src.core.registry import DataSource


class ContinuousDataSource(DataSource, ABC):
    """Abstract base for continuous futures price series data sources.

    Continuous series are pre-stitched multi-contract price streams used
    exclusively for signal generation, feature engineering, and backtesting.
    They are NOT used for term structure analysis. See ADR-001.

    Concrete implementations:
        Phase 1: LocalCSVSource  — reads from data/raw/continuous/
        Phase 1 (deferred): YahooFinanceSource
        Phase 2+: ContractDataSource (separate class for term structure)
    """

    @property
    def is_continuous(self) -> bool:
        """Return True for all continuous series sources.

        Concrete property, not abstract. All ContinuousDataSource
        implementations represent continuous series by definition.
        """
        return True
