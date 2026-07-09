"""Tests for Module 16: Risk Analytics.

Tests RiskReport, RiskEngine.compute(), VaR correctness, ES correctness,
and notional exposure computation. Uses monkeypatch on DataLoader.load()
and MultiAssetRunner to produce MultiAssetBacktestResult for integration
tests. All synthetic — no filesystem or network access.

See Architecture Section 5 (Layer 6) and ADR-003.
"""

from __future__ import annotations

import math
from datetime import date

import numpy as np
import pandas as pd
import pytest

from src.backtesting.multi_asset import MultiAssetRunner
from src.core.config import Config
from src.core.types import MultiAssetBacktestResult, RiskReport
from src.data.loader import DataLoader
from src.risk.risk_engine import RiskEngine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv(
    n: int = 300,
    base_close: float = 100.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Synthetic NormalizedOHLCV."""
    rng = np.random.default_rng(seed=seed)
    returns = rng.normal(0.0, 0.01, n)
    closes = base_close * np.cumprod(1 + returns)
    dates = pd.bdate_range(start="2022-01-03", periods=n, freq="B")
    return pd.DataFrame(
        {
            "open": closes * 0.999,
            "high": closes * 1.002,
            "low": closes * 0.998,
            "close": closes,
            "volume": [25000.0] * n,
            "open_interest": [float("nan")] * n,
        },
        index=pd.DatetimeIndex(dates, tz="UTC"),
    )


def _make_pnl_series(n: int = 300, seed: int = 0) -> pd.Series:
    """Synthetic daily PnL series with known statistical properties."""
    rng = np.random.default_rng(seed=seed)
    pnl = rng.normal(loc=100.0, scale=500.0, size=n)
    dates = pd.bdate_range(start="2022-01-03", periods=n, freq="B")
    return pd.Series(pnl, index=pd.DatetimeIndex(dates, tz="UTC"), name="pnl")


def _make_multi_result(
    config: Config,
    monkeypatch: pytest.MonkeyPatch,
    assets: list[str] | None = None,
    n_bars: int = 300,
    seeds: list[int] | None = None,
) -> MultiAssetBacktestResult:
    """Produce a MultiAssetBacktestResult via patched DataLoader."""
    if assets is None:
        assets = ["gold", "silver"]
    if seeds is None:
        seeds = list(range(len(assets)))

    ohlcv_map = {
        asset: _make_ohlcv(n_bars, base_close=float(100 * (i + 1)), seed=seeds[i])
        for i, asset in enumerate(assets)
    }

    def mock_load(self, asset, **kwargs):  # noqa: ANN001
        if asset in ohlcv_map:
            return ohlcv_map[asset]
        raise FileNotFoundError(f"No data for {asset}")

    monkeypatch.setattr(DataLoader, "load", mock_load)
    runner = MultiAssetRunner(config)
    return runner.run(
        assets=assets,
        strategy_name="ema_crossover",
        parameters={"fast_period": 50, "slow_period": 200},
    )


# ---------------------------------------------------------------------------
# RiskReport dataclass tests (2 tests)
# ---------------------------------------------------------------------------


def test_risk_report_creation_and_fields() -> None:
    """RiskReport fields and portfolio_diversification_benefit property work."""
    report = RiskReport(
        strategy_name="ema_crossover",
        run_id="20260101_000000_portfolio_ema_crossover",
        assets=["gold", "silver"],
        computation_date=date(2026, 7, 9),
        lookback_days=252,
        initial_capital_total=2_000_000.0,
        portfolio_var_95=3_000.0,
        portfolio_var_99=5_000.0,
        portfolio_var_95_pct=0.0015,
        portfolio_var_99_pct=0.0025,
        portfolio_es_95=3_800.0,
        portfolio_es_99=7_000.0,
        asset_var_95={"gold": 2_000.0, "silver": 2_500.0},
        asset_var_99={"gold": 3_500.0, "silver": 4_000.0},
        avg_gross_notional_by_asset={"gold": 100_000.0, "silver": 100_000.0},
        avg_net_notional_by_asset={"gold": 50_000.0, "silver": -30_000.0},
        total_avg_gross_notional=200_000.0,
        total_avg_net_notional=20_000.0,
    )

    assert report.strategy_name == "ema_crossover"
    assert report.lookback_days == 252
    assert report.portfolio_var_99 == pytest.approx(5_000.0)
    assert report.portfolio_es_99 >= report.portfolio_var_99
    # Diversification benefit: (3500 + 4000) / 5000 = 1.5
    benefit = report.portfolio_diversification_benefit
    assert not math.isnan(benefit)
    assert benefit > 1.0, "Sum of asset VaR99 should exceed portfolio VaR99"


def test_risk_report_diversification_benefit_nan_when_var_zero() -> None:
    """portfolio_diversification_benefit is NaN when portfolio_var_99 is zero."""
    report = RiskReport(
        strategy_name="test",
        run_id="test",
        assets=["gold"],
        computation_date=date.today(),
        lookback_days=252,
        initial_capital_total=1_000_000.0,
        portfolio_var_95=0.0,
        portfolio_var_99=0.0,
        portfolio_var_95_pct=0.0,
        portfolio_var_99_pct=0.0,
        portfolio_es_95=0.0,
        portfolio_es_99=0.0,
        asset_var_95={"gold": 1_000.0},
        asset_var_99={"gold": 2_000.0},
        avg_gross_notional_by_asset={"gold": 100_000.0},
        avg_net_notional_by_asset={"gold": 100_000.0},
        total_avg_gross_notional=100_000.0,
        total_avg_net_notional=100_000.0,
    )
    assert math.isnan(report.portfolio_diversification_benefit)


# ---------------------------------------------------------------------------
# RiskEngine.compute() type and completeness (3 tests)
# ---------------------------------------------------------------------------


def test_risk_engine_returns_correct_type(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """RiskEngine.compute() returns a RiskReport instance."""
    multi_result = _make_multi_result(config, monkeypatch)
    engine = RiskEngine()
    report = engine.compute(multi_result)

    assert isinstance(report, RiskReport)
    assert report.strategy_name == "ema_crossover"
    assert report.run_id == multi_result.run_id


def test_risk_engine_all_portfolio_metrics_populated(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All portfolio VaR, ES, and pct fields are populated (float — may be NaN)."""
    multi_result = _make_multi_result(config, monkeypatch)
    engine = RiskEngine()
    report = engine.compute(multi_result)

    assert isinstance(report.portfolio_var_95, float)
    assert isinstance(report.portfolio_var_99, float)
    assert isinstance(report.portfolio_es_95, float)
    assert isinstance(report.portfolio_es_99, float)
    assert isinstance(report.portfolio_var_95_pct, float)
    assert isinstance(report.portfolio_var_99_pct, float)


def test_risk_engine_per_asset_var_for_all_assets(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """asset_var_95 and asset_var_99 contain entries for all successful assets."""
    assets = ["gold", "silver", "copper"]
    multi_result = _make_multi_result(
        config, monkeypatch, assets=assets, seeds=[1, 2, 3]
    )
    engine = RiskEngine()
    report = engine.compute(multi_result)

    for asset in assets:
        assert asset in report.asset_var_95, f"asset_var_95 missing {asset}"
        assert asset in report.asset_var_99, f"asset_var_99 missing {asset}"
        assert isinstance(report.asset_var_95[asset], float)
        assert isinstance(report.asset_var_99[asset], float)


# ---------------------------------------------------------------------------
# VaR correctness tests (4 tests)
# ---------------------------------------------------------------------------


def test_var_99_geq_var_95(config: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    """portfolio_var_99 >= portfolio_var_95 (higher confidence = larger loss)."""
    multi_result = _make_multi_result(config, monkeypatch, n_bars=300, seeds=[42, 43])
    engine = RiskEngine()
    report = engine.compute(multi_result)

    v95 = report.portfolio_var_95
    v99 = report.portfolio_var_99
    if not math.isnan(v95) and not math.isnan(v99):
        assert v99 >= v95, f"VaR99 ({v99:.2f}) must be >= VaR95 ({v95:.2f})"


def test_var_is_positive_loss_magnitude(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All VaR values are non-negative (expressed as loss magnitude)."""
    multi_result = _make_multi_result(config, monkeypatch, seeds=[10, 11])
    engine = RiskEngine()
    report = engine.compute(multi_result)

    for field_name, value in [
        ("portfolio_var_95", report.portfolio_var_95),
        ("portfolio_var_99", report.portfolio_var_99),
    ]:
        if not math.isnan(value):
            assert value >= 0.0, f"{field_name} must be non-negative, got {value}"

    for asset, v in report.asset_var_99.items():
        if not math.isnan(v):
            assert v >= 0.0, f"asset_var_99[{asset}] must be non-negative, got {v}"


def test_var_pct_equals_var_over_initial_capital(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """portfolio_var_99_pct == portfolio_var_99 / initial_capital_total."""
    multi_result = _make_multi_result(config, monkeypatch, seeds=[20, 21])
    engine = RiskEngine()
    report = engine.compute(multi_result)

    if not math.isnan(report.portfolio_var_99) and report.initial_capital_total > 0:
        expected_pct = report.portfolio_var_99 / report.initial_capital_total
        assert report.portfolio_var_99_pct == pytest.approx(expected_pct, rel=1e-6)


def test_var_on_known_pnl_series() -> None:
    """VaR computation matches expected quantile on a controlled PnL series."""
    engine = RiskEngine()

    # Create a PnL series where the 1st percentile is known
    # 100 identical -1000 values and 9900 identical +100 values
    # 1st percentile should be -1000
    losses = [-1000.0] * 100 + [100.0] * 900
    dates = pd.bdate_range(start="2020-01-02", periods=1000, freq="B")
    pnl = pd.Series(losses, index=pd.DatetimeIndex(dates, tz="UTC"))

    var_99 = engine._compute_var(pnl, 0.99, lookback_days=1000)
    # 1st percentile of this series ≈ -1000, so VaR99 ≈ 1000
    assert var_99 == pytest.approx(
        1000.0, abs=50.0
    ), f"Expected VaR99 ≈ 1000 on controlled series, got {var_99:.2f}"


# ---------------------------------------------------------------------------
# Expected Shortfall correctness tests (3 tests)
# ---------------------------------------------------------------------------


def test_es_geq_var_same_confidence(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ES >= VaR at the same confidence level (ES is always at least as large)."""
    multi_result = _make_multi_result(config, monkeypatch, n_bars=300, seeds=[30, 31])
    engine = RiskEngine()
    report = engine.compute(multi_result)

    if not math.isnan(report.portfolio_es_95) and not math.isnan(
        report.portfolio_var_95
    ):
        assert (
            report.portfolio_es_95 >= report.portfolio_var_95
        ), "ES95 must be >= VaR95 (ES is a coherent superset of VaR)"
    if not math.isnan(report.portfolio_es_99) and not math.isnan(
        report.portfolio_var_99
    ):
        assert (
            report.portfolio_es_99 >= report.portfolio_var_99
        ), "ES99 must be >= VaR99 (ES is a coherent superset of VaR)"


def test_es_99_geq_es_95(config: Config, monkeypatch: pytest.MonkeyPatch) -> None:
    """ES99 >= ES95 (stricter confidence = larger expected tail loss)."""
    multi_result = _make_multi_result(config, monkeypatch, n_bars=300, seeds=[40, 41])
    engine = RiskEngine()
    report = engine.compute(multi_result)

    if not math.isnan(report.portfolio_es_95) and not math.isnan(
        report.portfolio_es_99
    ):
        assert (
            report.portfolio_es_99 >= report.portfolio_es_95
        ), f"ES99 ({report.portfolio_es_99:.2f}) must be >= ES95 ({report.portfolio_es_95:.2f})"


def test_es_on_known_pnl_series() -> None:
    """ES computation matches expected tail mean on a controlled PnL series."""
    engine = RiskEngine()

    # 1000 observations: 10 identical -2000, 990 identical +100
    # 99th VaR threshold = -2000; ES99 = mean of values <= -2000 = -2000 → abs = 2000
    losses = [-2000.0] * 10 + [100.0] * 990
    dates = pd.bdate_range(start="2020-01-02", periods=1000, freq="B")
    pnl = pd.Series(losses, index=pd.DatetimeIndex(dates, tz="UTC"))

    es_99 = engine._compute_es(pnl, 0.99, lookback_days=1000)
    assert es_99 == pytest.approx(
        2000.0, abs=50.0
    ), f"Expected ES99 ≈ 2000 on controlled series, got {es_99:.2f}"


# ---------------------------------------------------------------------------
# Notional exposure tests (2 tests)
# ---------------------------------------------------------------------------


def test_notional_gross_is_non_negative(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """avg_gross_notional_by_asset is non-negative for all assets."""
    multi_result = _make_multi_result(config, monkeypatch, seeds=[50, 51])
    engine = RiskEngine()
    report = engine.compute(multi_result)

    for asset, gross in report.avg_gross_notional_by_asset.items():
        if not math.isnan(gross):
            assert gross >= 0.0, f"Gross notional must be non-negative for {asset}"

    assert report.total_avg_gross_notional >= 0.0


def test_total_gross_notional_equals_sum_of_assets(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """total_avg_gross_notional == sum of avg_gross_notional_by_asset."""
    multi_result = _make_multi_result(
        config, monkeypatch, assets=["gold", "silver", "copper"], seeds=[60, 61, 62]
    )
    engine = RiskEngine()
    report = engine.compute(multi_result)

    expected_total = sum(
        v for v in report.avg_gross_notional_by_asset.values() if not math.isnan(v)
    )
    assert report.total_avg_gross_notional == pytest.approx(expected_total, rel=1e-6)


# ---------------------------------------------------------------------------
# Edge case tests (1 test)
# ---------------------------------------------------------------------------


def test_var_nan_for_insufficient_data(config: Config) -> None:
    """VaR returns NaN when PnL series has fewer than 20 valid observations."""
    engine = RiskEngine()

    short_pnl = pd.Series(
        [-100.0, 200.0, -50.0],  # only 3 observations
        index=pd.DatetimeIndex(
            pd.bdate_range("2026-01-02", periods=3, freq="B"), tz="UTC"
        ),
    )

    var = engine._compute_var(short_pnl, 0.99, lookback_days=252)
    assert math.isnan(var), f"VaR must be NaN for fewer than 20 observations, got {var}"
