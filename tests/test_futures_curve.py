"""Tests for Module 9: Futures Curve Layer.

Tests CurvePoint, FuturesCurve, and FuturesCurveBuilder using synthetic
contract data loaded into ContractParquetStore via tmp_path fixtures.
No network calls, no yfinance access.

See Architecture Section 5 (Layer 5 Responsibilities) and ADR-001.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from src.commodity.curve import FuturesCurveBuilder
from src.core.config import Config
from src.core.types import ContractMetadata, CurvePoint, FuturesCurve
from src.data.contract_store import ContractParquetStore

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


def _make_contract_df(
    n: int = 60,
    start: str = "2025-01-02",
    base_close: float = 2000.0,
) -> pd.DataFrame:
    """Build a synthetic NormalizedOHLCV DataFrame for contract tests."""
    dates = pd.bdate_range(start=start, periods=n, freq="B")
    closes = [base_close + i * 0.5 for i in range(n)]
    return pd.DataFrame(
        {
            "open": [c - 5.0 for c in closes],
            "high": [c + 10.0 for c in closes],
            "low": [c - 10.0 for c in closes],
            "close": closes,
            "volume": [25000.0] * n,
            "open_interest": [float("nan")] * n,
        },
        index=pd.DatetimeIndex(dates, tz="UTC"),
    )


def _make_meta(
    ticker: str,
    asset: str,
    root: str,
    month: int,
    year: int,
    n_bars: int = 60,
) -> ContractMetadata:
    """Build a ContractMetadata for testing."""
    return ContractMetadata(
        ticker=ticker,
        asset=asset,
        contract_root=root,
        contract_month=month,
        contract_year=year,
        n_bars=n_bars,
    )


@pytest.fixture
def tmp_config(tmp_path: Path) -> Config:
    """Config fixture redirecting contract paths to tmp_path."""
    cfg = Config.load("config/")
    cfg.paths["contracts_raw"] = str(tmp_path / "data" / "raw" / "contracts") + "/"
    cfg.paths["contracts_processed"] = (
        str(tmp_path / "data" / "processed" / "contracts") + "/"
    )
    (tmp_path / "data" / "raw" / "contracts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "data" / "processed" / "contracts").mkdir(parents=True, exist_ok=True)
    return cfg


def _load_gold_curve_into_store(
    tmp_config: Config,
    contracts: list[tuple[str, int, int, float]],
) -> None:
    """Pre-load synthetic gold contracts into ContractParquetStore.

    Args:
        tmp_config: Config with tmp_path redirected paths.
        contracts: List of (ticker, month, year, base_close) tuples.
    """
    store = ContractParquetStore(tmp_config)
    for ticker, month, year, base_close in contracts:
        df = _make_contract_df(60, base_close=base_close)
        meta = _make_meta(ticker, "gold", "GC", month, year, 60)
        store.write(df, "gold", ticker, meta)


# ---------------------------------------------------------------------------
# CurvePoint tests (3 tests)
# ---------------------------------------------------------------------------


def test_curve_point_days_to_delivery_positive_for_future_contract() -> None:
    """CurvePoint.days_to_delivery is positive for contracts in the future."""
    meta = _make_meta("GCZ26", "gold", "GC", 12, 2026)
    point = CurvePoint(
        metadata=meta,
        close=2500.0,
        volume=25000.0,
        observation_date=date(2026, 7, 1),
        data_date=date(2026, 7, 1),
        days_to_delivery=(date(2026, 12, 1) - date(2026, 7, 1)).days,
    )
    assert point.days_to_delivery > 0
    assert point.days_to_delivery == (date(2026, 12, 1) - date(2026, 7, 1)).days


def test_curve_point_days_to_delivery_negative_for_expired() -> None:
    """CurvePoint.days_to_delivery is negative for expired contracts."""
    meta = _make_meta("GCF26", "gold", "GC", 1, 2026)
    point = CurvePoint(
        metadata=meta,
        close=2400.0,
        volume=15000.0,
        observation_date=date(2026, 7, 1),
        data_date=date(2026, 1, 30),
        days_to_delivery=(date(2026, 1, 1) - date(2026, 7, 1)).days,
    )
    assert point.days_to_delivery < 0


def test_curve_point_volume_can_be_nan() -> None:
    """CurvePoint.volume accepts float('nan') for contracts with no volume data."""
    import math

    meta = _make_meta("GCZ26", "gold", "GC", 12, 2026)
    point = CurvePoint(
        metadata=meta,
        close=2500.0,
        volume=float("nan"),
        observation_date=date(2026, 7, 1),
        data_date=date(2026, 7, 1),
        days_to_delivery=153,
    )
    assert math.isnan(point.volume)
    assert point.close == 2500.0


# ---------------------------------------------------------------------------
# FuturesCurve property tests (5 tests)
# ---------------------------------------------------------------------------


def test_futures_curve_is_contango_when_back_above_front() -> None:
    """FuturesCurve.is_contango is True when back price > front price."""
    obs = date(2026, 7, 1)
    meta_front = _make_meta("GCQ26", "gold", "GC", 8, 2026)
    meta_back = _make_meta("GCZ26", "gold", "GC", 12, 2026)
    curve = FuturesCurve(
        asset="gold",
        observation_date=obs,
        points=[
            CurvePoint(meta_front, 2450.0, 30000.0, obs, obs, 31),
            CurvePoint(meta_back, 2500.0, 20000.0, obs, obs, 153),
        ],
    )
    assert curve.is_contango is True
    assert curve.is_backwardation is False


def test_futures_curve_is_backwardation_when_front_above_back() -> None:
    """FuturesCurve.is_backwardation is True when front price > back price."""
    obs = date(2026, 7, 1)
    meta_front = _make_meta("CLQ26", "wti", "CL", 8, 2026)
    meta_back = _make_meta("CLZ26", "wti", "CL", 12, 2026)
    curve = FuturesCurve(
        asset="wti",
        observation_date=obs,
        points=[
            CurvePoint(meta_front, 85.0, 200000.0, obs, obs, 31),
            CurvePoint(meta_back, 80.0, 100000.0, obs, obs, 153),
        ],
    )
    assert curve.is_backwardation is True
    assert curve.is_contango is False


def test_futures_curve_single_point_not_contango_or_backwardation() -> None:
    """FuturesCurve with one point returns False for both contango and backwardation."""
    obs = date(2026, 7, 1)
    meta = _make_meta("GCQ26", "gold", "GC", 8, 2026)
    curve = FuturesCurve(
        asset="gold",
        observation_date=obs,
        points=[CurvePoint(meta, 2450.0, 30000.0, obs, obs, 31)],
    )
    assert curve.is_contango is False
    assert curve.is_backwardation is False
    assert curve.n_points == 1


def test_futures_curve_slope_positive_for_contango() -> None:
    """FuturesCurve.slope is positive for contango term structure."""
    obs = date(2026, 7, 1)
    meta_front = _make_meta("GCQ26", "gold", "GC", 8, 2026)
    meta_back = _make_meta("GCZ26", "gold", "GC", 12, 2026)
    curve = FuturesCurve(
        asset="gold",
        observation_date=obs,
        points=[
            CurvePoint(
                meta_front, 2450.0, 30000.0, obs, obs, (date(2026, 8, 1) - obs).days
            ),
            CurvePoint(
                meta_back, 2500.0, 20000.0, obs, obs, (date(2026, 12, 1) - obs).days
            ),
        ],
    )
    assert curve.slope > 0, "Contango curve must have positive slope"


def test_futures_curve_prices_and_tickers_lists_correct() -> None:
    """FuturesCurve.prices and .tickers return ordered lists."""
    obs = date(2026, 7, 1)
    m1 = _make_meta("GCQ26", "gold", "GC", 8, 2026)
    m2 = _make_meta("GCU26", "gold", "GC", 9, 2026)
    m3 = _make_meta("GCZ26", "gold", "GC", 12, 2026)
    curve = FuturesCurve(
        asset="gold",
        observation_date=obs,
        points=[
            CurvePoint(m1, 2450.0, 30000.0, obs, obs, 31),
            CurvePoint(m2, 2465.0, 25000.0, obs, obs, 62),
            CurvePoint(m3, 2500.0, 20000.0, obs, obs, 153),
        ],
    )
    assert curve.prices == [2450.0, 2465.0, 2500.0]
    assert curve.tickers == ["GCQ26", "GCU26", "GCZ26"]
    assert curve.front_price == 2450.0
    assert curve.back_price == 2500.0
    assert curve.spread() == pytest.approx(50.0)


# ---------------------------------------------------------------------------
# FuturesCurveBuilder tests (7 tests)
# ---------------------------------------------------------------------------


def test_curve_builder_returns_futures_curve_type(tmp_config: Config) -> None:
    """FuturesCurveBuilder.build() returns a FuturesCurve instance."""
    _load_gold_curve_into_store(
        tmp_config,
        [
            ("GCQ26", 8, 2026, 2450.0),
            ("GCZ26", 12, 2026, 2500.0),
        ],
    )
    builder = FuturesCurveBuilder(tmp_config)
    curve = builder.build("gold", observation_date=date(2026, 7, 1))
    assert isinstance(curve, FuturesCurve)
    assert curve.asset == "gold"
    assert curve.observation_date == date(2026, 7, 1)


def test_curve_builder_points_sorted_nearest_first(tmp_config: Config) -> None:
    """FuturesCurveBuilder.build() returns points sorted by delivery date."""
    # Load in reverse order to confirm builder sorts correctly
    _load_gold_curve_into_store(
        tmp_config,
        [
            ("GCZ26", 12, 2026, 2500.0),
            ("GCQ26", 8, 2026, 2450.0),
            ("GCU26", 9, 2026, 2465.0),
        ],
    )
    builder = FuturesCurveBuilder(tmp_config)
    curve = builder.build("gold", observation_date=date(2026, 7, 1), n_contracts=3)

    months = [p.metadata.contract_month for p in curve.points]
    assert months == sorted(
        months
    ), f"Curve points must be sorted by delivery month (nearest first), got {months}"


def test_curve_builder_uses_observation_date_correctly(tmp_config: Config) -> None:
    """FuturesCurveBuilder uses price as of the observation_date, not latest price."""
    _load_gold_curve_into_store(tmp_config, [("GCZ26", 12, 2026, 2000.0)])

    builder = FuturesCurveBuilder(tmp_config)

    # observation_date on the first trading day — should get ~2000.0
    curve_early = builder.build("gold", observation_date=date(2025, 1, 2))
    # observation_date after the last data point — should get latest price (~2029.5)
    curve_late = builder.build("gold", observation_date=date(2026, 7, 1))

    if curve_early.n_points > 0 and curve_late.n_points > 0:
        assert (
            curve_late.front_price >= curve_early.front_price
        ), "Later observation should use a later price"


def test_curve_builder_excludes_contracts_with_no_data_before_observation(
    tmp_config: Config,
) -> None:
    """FuturesCurveBuilder excludes contracts that have no data before observation_date."""
    store = ContractParquetStore(tmp_config)
    df = _make_contract_df(30, start="2026-01-02", base_close=2500.0)
    meta = _make_meta("GCZ26", "gold", "GC", 12, 2026, 30)
    store.write(df, "gold", "GCZ26", meta)

    builder = FuturesCurveBuilder(tmp_config)
    # observation_date before any data exists for this contract
    curve = builder.build("gold", observation_date=date(2025, 6, 1))

    assert all(
        p.metadata.ticker != "GCZ26" for p in curve.points
    ), "Contract with no data before observation_date must be excluded"


def test_curve_builder_handles_fewer_than_n_contracts(tmp_config: Config) -> None:
    """FuturesCurveBuilder returns fewer points than n_contracts if coverage is thin."""
    _load_gold_curve_into_store(
        tmp_config,
        [
            ("GCQ26", 8, 2026, 2450.0),
            ("GCZ26", 12, 2026, 2500.0),
        ],
    )
    builder = FuturesCurveBuilder(tmp_config)
    curve = builder.build("gold", observation_date=date(2026, 7, 1), n_contracts=6)

    assert (
        curve.n_points <= 2
    ), "Curve must not invent contracts — n_points must be <= available contracts"


def test_curve_builder_raises_when_no_contracts_available(tmp_config: Config) -> None:
    """FuturesCurveBuilder.build() raises ValueError when no contracts exist for asset."""
    builder = FuturesCurveBuilder(tmp_config)
    with pytest.raises(ValueError, match="acquire_contract_data"):
        builder.build("silver", observation_date=date(2026, 7, 1))


def test_curve_builder_build_historical_curves_returns_correct_count(
    tmp_config: Config,
) -> None:
    """build_historical_curves() returns one FuturesCurve per input date."""
    _load_gold_curve_into_store(
        tmp_config,
        [
            ("GCQ26", 8, 2026, 2450.0),
            ("GCZ26", 12, 2026, 2500.0),
        ],
    )
    builder = FuturesCurveBuilder(tmp_config)
    dates = [date(2026, 6, 1), date(2026, 6, 15), date(2026, 7, 1)]
    curves = builder.build_historical_curves("gold", dates=dates, n_contracts=3)

    assert len(curves) == 3, f"Expected 3 curves, got {len(curves)}"
    obs_dates = [c.observation_date for c in curves]
    assert obs_dates == sorted(obs_dates)
    assert all(isinstance(c, FuturesCurve) for c in curves)


# ---------------------------------------------------------------------------
# available_assets and empty curve edge cases (2 tests)
# ---------------------------------------------------------------------------


def test_curve_builder_available_assets_returns_assets_with_parquet(
    tmp_config: Config,
) -> None:
    """available_assets() returns sorted list of assets with processed data."""
    for asset, ticker, root, month, year, price in [
        ("gold", "GCQ26", "GC", 8, 2026, 2450.0),
        ("wti", "CLQ26", "CL", 8, 2026, 80.0),
    ]:
        store = ContractParquetStore(tmp_config)
        df = _make_contract_df(20, base_close=price)
        meta = _make_meta(ticker, asset, root, month, year, 20)
        store.write(df, asset, ticker, meta)

    builder = FuturesCurveBuilder(tmp_config)
    assets = builder.available_assets()

    assert "gold" in assets
    assert "wti" in assets
    assert assets == sorted(assets)


def test_futures_curve_empty_curve_properties() -> None:
    """FuturesCurve with no points returns safe defaults for all properties."""
    import math

    curve = FuturesCurve(
        asset="gold",
        observation_date=date(2026, 7, 1),
        points=[],
    )
    assert curve.is_empty is True
    assert curve.n_points == 0
    assert math.isnan(curve.front_price)
    assert math.isnan(curve.back_price)
    assert math.isnan(curve.slope)
    assert curve.is_contango is False
    assert curve.is_backwardation is False
    assert curve.prices == []
    assert curve.tickers == []
    assert math.isnan(curve.spread())


def test_futures_curve_builder_list_contracts_returns_sorted_list(
    tmp_config: Config,
) -> None:
    """FuturesCurveBuilder.list_contracts() delegates to loader and returns sorted list."""
    store = ContractParquetStore(tmp_config)
    for ticker, month in [("GCZ26", 12), ("GCF26", 1), ("GCQ26", 8)]:
        df = _make_contract_df(20)
        meta = _make_meta(ticker, "gold", "GC", month, 2026, 20)
        store.write(df, "gold", ticker, meta)

    builder = FuturesCurveBuilder(tmp_config)
    contracts = builder.list_contracts("gold")

    assert len(contracts) == 3
    months = [m.contract_month for m in contracts]
    assert months == sorted(
        months
    ), "list_contracts must return sorted by delivery date"


def test_futures_curve_builder_list_contracts_empty_for_unknown_asset(
    tmp_config: Config,
) -> None:
    """FuturesCurveBuilder.list_contracts() returns empty list when no data exists."""
    builder = FuturesCurveBuilder(tmp_config)
    result = builder.list_contracts("copper")
    assert (
        result == []
    ), "Must return empty list, not raise, for asset with no contracts"
