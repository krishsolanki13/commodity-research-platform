"""Tests for Module 17: Cross-Asset Correlation Analytics.

Tests CorrelationReport, CorrelationEngine.compute(), correlation matrix
correctness, rolling correlation structure, realized volatility computation,
and derived analytics. Uses monkeypatch on DataLoader.load() and
MultiAssetRunner. All synthetic — no filesystem or network access.

See Architecture Section 5 (Layer 7) and ADR-010.
"""

from __future__ import annotations

import math
from datetime import UTC, date

import numpy as np
import pandas as pd
import pytest

from src.analytics.correlation import CorrelationEngine
from src.backtesting.multi_asset import MultiAssetRunner
from src.core.config import Config
from src.core.types import CorrelationReport, MultiAssetBacktestResult
from src.data.loader import DataLoader

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ohlcv(
    n: int = 400,
    base_close: float = 100.0,
    seed: int = 42,
) -> pd.DataFrame:
    """Synthetic NormalizedOHLCV with sufficient history for rolling windows."""
    rng = np.random.default_rng(seed=seed)
    returns = rng.normal(0.0, 0.01, n)
    closes = base_close * np.cumprod(1 + returns)
    dates = pd.bdate_range(start="2021-01-04", periods=n, freq="B")
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


def _make_multi_result(
    config: Config,
    monkeypatch: pytest.MonkeyPatch,
    assets: list[str] | None = None,
    n_bars: int = 400,
    seeds: list[int] | None = None,
) -> MultiAssetBacktestResult:
    """Run MultiAssetRunner with patched DataLoader."""
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
# CorrelationReport dataclass tests (2 tests)
# ---------------------------------------------------------------------------


def test_correlation_report_properties() -> None:
    """CorrelationReport n_assets, n_pairs, get_correlation work correctly."""
    matrix = {
        "gold": {"gold": 1.0, "silver": 0.75, "copper": 0.40},
        "silver": {"gold": 0.75, "silver": 1.0, "copper": 0.55},
        "copper": {"gold": 0.40, "silver": 0.55, "copper": 1.0},
    }
    report = CorrelationReport(
        strategy_name="ema_crossover",
        run_id="test_run",
        assets=["gold", "silver", "copper"],
        computation_date=date.today(),
        correlation_matrix=matrix,
        rolling_correlations_63={},
        rolling_correlations_126={},
        realized_vol_by_asset={"gold": 0.15, "silver": 0.25, "copper": 0.22},
        portfolio_realized_vol=0.10,
        avg_pairwise_correlation=0.567,
        most_correlated_pair=("gold", "silver", 0.75),
        least_correlated_pair=("copper", "gold", 0.40),
    )

    assert report.n_assets == 3
    assert report.n_pairs == 3  # 3*(3-1)/2
    assert report.get_correlation("gold", "silver") == pytest.approx(0.75)
    assert report.get_correlation("gold", "gold") == pytest.approx(1.0)
    assert math.isnan(report.get_correlation("gold", "platinum"))


def test_correlation_report_get_correlation_symmetric() -> None:
    """get_correlation(a, b) == get_correlation(b, a) for valid pairs."""
    matrix = {
        "gold": {"gold": 1.0, "wti": -0.10},
        "wti": {"gold": -0.10, "wti": 1.0},
    }
    report = CorrelationReport(
        strategy_name="test",
        run_id="test",
        assets=["gold", "wti"],
        computation_date=date.today(),
        correlation_matrix=matrix,
        rolling_correlations_63={},
        rolling_correlations_126={},
        realized_vol_by_asset={},
        portfolio_realized_vol=0.0,
        avg_pairwise_correlation=-0.10,
        most_correlated_pair=("gold", "wti", -0.10),
        least_correlated_pair=("gold", "wti", -0.10),
    )
    assert report.get_correlation("gold", "wti") == pytest.approx(
        report.get_correlation("wti", "gold")
    )


# ---------------------------------------------------------------------------
# CorrelationEngine.compute() core behavior (3 tests)
# ---------------------------------------------------------------------------


def test_correlation_engine_returns_correct_type(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """CorrelationEngine.compute() returns a CorrelationReport."""
    multi_result = _make_multi_result(config, monkeypatch, seeds=[1, 2])
    engine = CorrelationEngine()
    report = engine.compute(multi_result)

    assert isinstance(report, CorrelationReport)
    assert report.strategy_name == "ema_crossover"
    assert set(report.assets) == {"gold", "silver"}


def test_correlation_engine_matrix_has_all_asset_pairs(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Correlation matrix contains entries for all pairs including diagonal."""
    assets = ["gold", "silver", "copper"]
    multi_result = _make_multi_result(
        config, monkeypatch, assets=assets, seeds=[1, 2, 3]
    )
    engine = CorrelationEngine()
    report = engine.compute(multi_result)

    for a in assets:
        assert a in report.correlation_matrix, f"Matrix missing row for {a}"
        for b in assets:
            assert b in report.correlation_matrix[a], f"Matrix missing {a}→{b}"
            if a == b:
                assert report.correlation_matrix[a][b] == pytest.approx(1.0)


def test_correlation_engine_raises_for_empty_asset_results(
    config: Config,
) -> None:
    """CorrelationEngine.compute() raises ValueError for empty asset_results."""
    equity = pd.Series(
        [1_000_000.0],
        index=pd.DatetimeIndex(["2026-01-02"], tz="UTC"),
    )
    from datetime import datetime

    empty_result = MultiAssetBacktestResult(
        strategy_name="test",
        signal_name="test",
        parameters={},
        assets=[],
        skipped_assets=[],
        run_id="test",
        executed_at=datetime.now(UTC),
        asset_results={},
        portfolio_equity_curve=equity,
        portfolio_pnl_series=equity * 0,
    )
    engine = CorrelationEngine()
    with pytest.raises(ValueError, match="no asset results"):
        engine.compute(empty_result)


# ---------------------------------------------------------------------------
# Correlation matrix correctness (4 tests)
# ---------------------------------------------------------------------------


def test_correlation_matrix_diagonal_is_one(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All diagonal entries of the correlation matrix are exactly 1.0."""
    assets = ["gold", "silver", "copper"]
    multi_result = _make_multi_result(
        config, monkeypatch, assets=assets, seeds=[10, 11, 12]
    )
    engine = CorrelationEngine()
    report = engine.compute(multi_result)

    for asset in assets:
        diag = report.correlation_matrix[asset][asset]
        assert diag == pytest.approx(1.0), f"Diagonal [{asset}][{asset}] = {diag}"


def test_correlation_matrix_is_symmetric(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """correlation_matrix[a][b] == correlation_matrix[b][a] for all pairs."""
    assets = ["gold", "silver", "copper"]
    multi_result = _make_multi_result(
        config, monkeypatch, assets=assets, seeds=[20, 21, 22]
    )
    engine = CorrelationEngine()
    report = engine.compute(multi_result)

    from itertools import combinations

    for a, b in combinations(assets, 2):
        val_ab = report.correlation_matrix[a][b]
        val_ba = report.correlation_matrix[b][a]
        if not math.isnan(val_ab) and not math.isnan(val_ba):
            assert val_ab == pytest.approx(
                val_ba, abs=1e-10
            ), f"Matrix not symmetric: [{a}][{b}]={val_ab} != [{b}][{a}]={val_ba}"


def test_correlation_bounded_between_minus_one_and_one(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All off-diagonal correlations are in [-1.0, 1.0]."""
    assets = ["gold", "silver", "copper"]
    multi_result = _make_multi_result(
        config, monkeypatch, assets=assets, seeds=[30, 31, 32]
    )
    engine = CorrelationEngine()
    report = engine.compute(multi_result)

    from itertools import combinations

    for a, b in combinations(assets, 2):
        val = report.correlation_matrix[a][b]
        if not math.isnan(val):
            assert (
                -1.0 <= val <= 1.0
            ), f"Correlation [{a}][{b}]={val} out of [-1, 1] range"


def test_perfectly_correlated_assets_have_correlation_one() -> None:
    """Two identical return series produce correlation of exactly 1.0."""
    engine = CorrelationEngine()
    returns = pd.Series(
        [0.01, -0.005, 0.02, -0.01, 0.015] * 40,
        index=pd.DatetimeIndex(
            pd.bdate_range("2023-01-02", periods=200, freq="B"), tz="UTC"
        ),
    )
    df = pd.DataFrame({"gold": returns, "silver": returns})
    matrix = engine._compute_correlation_matrix(df)

    assert matrix["gold"]["silver"] == pytest.approx(1.0, abs=1e-10)
    assert matrix["silver"]["gold"] == pytest.approx(1.0, abs=1e-10)


# ---------------------------------------------------------------------------
# Rolling correlation structure (3 tests)
# ---------------------------------------------------------------------------


def test_rolling_correlations_63_has_correct_window_keys(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """rolling_correlations_63 contains upper-triangle pairs (asset_a < asset_b)."""
    assets = ["gold", "silver", "copper"]
    multi_result = _make_multi_result(
        config, monkeypatch, assets=assets, seeds=[40, 41, 42]
    )
    engine = CorrelationEngine()
    report = engine.compute(multi_result)

    from itertools import combinations

    for a, b in combinations(sorted(assets), 2):
        assert a in report.rolling_correlations_63, f"Missing outer key {a}"
        assert b in report.rolling_correlations_63[a], f"Missing inner key {a}→{b}"
        series = report.rolling_correlations_63[a][b]
        assert isinstance(series, pd.Series)


def test_rolling_correlations_126_longer_window_fewer_valid_values(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """126-day rolling window has more NaN values than 63-day (longer warmup)."""
    multi_result = _make_multi_result(
        config, monkeypatch, assets=["gold", "silver"], n_bars=400, seeds=[50, 51]
    )
    engine = CorrelationEngine()
    report = engine.compute(multi_result)

    rc63 = report.rolling_correlations_63
    rc126 = report.rolling_correlations_126
    if "gold" in rc63 and "silver" in rc63.get("gold", {}):
        series_63 = rc63["gold"]["silver"]
        series_126 = rc126.get("gold", {}).get("silver", pd.Series(dtype=float))
        valid_63 = series_63.notna().sum()
        valid_126 = series_126.notna().sum()
        assert (
            valid_126 <= valid_63
        ), "126-day window must have <= valid values than 63-day (longer NaN warmup)"


def test_rolling_correlations_bounded_in_valid_range(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """All non-NaN rolling correlation values are in [-1.0, 1.0]."""
    multi_result = _make_multi_result(
        config, monkeypatch, assets=["gold", "silver"], n_bars=400, seeds=[60, 61]
    )
    engine = CorrelationEngine()
    report = engine.compute(multi_result)

    for outer_key, inner_dict in report.rolling_correlations_63.items():
        for inner_key, series in inner_dict.items():
            valid = series.dropna()
            if len(valid) > 0:
                assert (
                    (valid >= -1.0).all() and (valid <= 1.0).all()
                ), f"Rolling corr [{outer_key}][{inner_key}] has out-of-range values"


# ---------------------------------------------------------------------------
# Realized volatility tests (2 tests)
# ---------------------------------------------------------------------------


def test_realized_vol_by_asset_non_negative(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """realized_vol_by_asset values are non-negative for all assets."""
    assets = ["gold", "silver", "copper"]
    multi_result = _make_multi_result(
        config, monkeypatch, assets=assets, seeds=[70, 71, 72]
    )
    engine = CorrelationEngine()
    report = engine.compute(multi_result)

    for asset, vol in report.realized_vol_by_asset.items():
        if not math.isnan(vol):
            assert vol >= 0.0, f"Realized vol for {asset} must be non-negative"


def test_portfolio_realized_vol_below_avg_asset_vol(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Portfolio realized vol <= avg of per-asset vols (diversification effect)."""
    assets = ["gold", "silver", "copper"]
    multi_result = _make_multi_result(
        config, monkeypatch, assets=assets, n_bars=400, seeds=[80, 81, 82]
    )
    engine = CorrelationEngine()
    report = engine.compute(multi_result)

    asset_vols = [v for v in report.realized_vol_by_asset.values() if not math.isnan(v)]
    if asset_vols and not math.isnan(report.portfolio_realized_vol):
        avg_asset_vol = sum(asset_vols) / len(asset_vols)
        assert report.portfolio_realized_vol <= avg_asset_vol * 1.1, (
            f"Portfolio vol {report.portfolio_realized_vol:.4f} unexpectedly high "
            f"vs avg asset vol {avg_asset_vol:.4f}"
        )


# ---------------------------------------------------------------------------
# Derived analytics (1 test)
# ---------------------------------------------------------------------------


def test_most_and_least_correlated_pairs_are_valid(
    config: Config, monkeypatch: pytest.MonkeyPatch
) -> None:
    """most_correlated_pair and least_correlated_pair are valid asset pairs."""
    assets = ["gold", "silver", "copper"]
    multi_result = _make_multi_result(
        config, monkeypatch, assets=assets, seeds=[90, 91, 92]
    )
    engine = CorrelationEngine()
    report = engine.compute(multi_result)

    # Most correlated pair
    a, b, val = report.most_correlated_pair
    if a and b:
        assert (
            a in assets and b in assets
        ), "most_correlated pair contains unknown assets"
        assert a <= b, "Asset pair should be alphabetically ordered (a <= b)"
        if not math.isnan(val):
            assert -1.0 <= val <= 1.0

    # Least correlated pair
    c, d, val2 = report.least_correlated_pair
    if c and d:
        assert c in assets and d in assets
        if not math.isnan(val) and not math.isnan(val2):
            assert abs(val) >= abs(
                val2
            ), "Most correlated |corr| must be >= least correlated |corr|"
