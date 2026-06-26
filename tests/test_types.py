"""Tests for shared type definitions and abstract base class enforcement.

Verifies that all dataclasses instantiate correctly, default values are
correct, and all ABCs prevent direct instantiation.
"""

from __future__ import annotations

import datetime

import pandas as pd
import pytest

from src.core.registry import (
    BacktestEngine,
    DataSource,
    Indicator,
    PositionSizer,
    SignalGenerator,
)
from src.core.types import (
    BacktestMetadata,
    BacktestResult,
    FeatureSpec,
    PerformanceReport,
    SignalEvaluation,
    TradeRecord,
)


def test_feature_spec_instantiation() -> None:
    """FeatureSpec instantiates correctly with all five fields."""
    spec = FeatureSpec(
        indicator_name="ema",
        parameters={"period": 50},
        column_name="ema_50",
        asset="gold",
        computed_at=datetime.datetime(2024, 1, 1, 12, 0, 0),
    )
    assert spec.indicator_name == "ema"
    assert spec.column_name == "ema_50"
    assert spec.parameters == {"period": 50}


def test_signal_evaluation_instantiation() -> None:
    """SignalEvaluation instantiates correctly with all nine fields."""
    evaluation = SignalEvaluation(
        signal_name="ema_crossover_50_200",
        asset="gold",
        ic=0.045,
        icir=0.62,
        ic_decay={1: 0.045, 2: 0.038, 5: 0.021, 10: 0.012, 20: 0.005},
        turnover=0.12,
        ic_rolling_window=63,
        evaluation_start=datetime.date(2020, 1, 1),
        evaluation_end=datetime.date(2023, 12, 31),
    )
    assert evaluation.ic == 0.045
    assert evaluation.icir == 0.62
    assert set(evaluation.ic_decay.keys()) == {1, 2, 5, 10, 20}


def test_trade_record_instantiation() -> None:
    """TradeRecord instantiates correctly with all required fields."""
    trade = TradeRecord(
        run_id="20240101_120000_ema_crossover_gold",
        asset="gold",
        direction=1,
        entry_date=datetime.date(2023, 3, 1),
        exit_date=datetime.date(2023, 4, 1),
        entry_price=1900.0,
        exit_price=1950.0,
        size_notional=100000.0,
        size_contracts=0.526,
        gross_pnl=2631.58,
        transaction_cost=10.0,
        net_pnl=2621.58,
        duration_bars=23,
        return_pct=0.02622,
    )
    assert trade.direction == 1
    assert trade.net_pnl == 2621.58
    assert trade.entry_price == 1900.0


def test_trade_record_force_closed_defaults_false() -> None:
    """TradeRecord.force_closed defaults to False when not supplied."""
    trade = TradeRecord(
        run_id="test",
        asset="gold",
        direction=1,
        entry_date=datetime.date(2023, 1, 1),
        exit_date=datetime.date(2023, 2, 1),
        entry_price=1900.0,
        exit_price=1950.0,
        size_notional=100000.0,
        size_contracts=0.526,
        gross_pnl=2631.58,
        transaction_cost=10.0,
        net_pnl=2621.58,
        duration_bars=23,
        return_pct=0.02622,
    )
    assert trade.force_closed is False


def test_backtest_result_signal_evaluation_optional() -> None:
    """BacktestResult is valid with signal_evaluation=None."""
    metadata = BacktestMetadata(
        run_id="test",
        asset="gold",
        strategy_name="ema_crossover",
        signal_name="ema_crossover_50_200",
        parameters={"fast": 50, "slow": 200},
        data_source="yahoo_finance",
        data_start=datetime.date(2020, 1, 1),
        data_end=datetime.date(2023, 12, 31),
        initial_capital_usd=1_000_000.0,
        cost_model_params={"commission_usd": 5.0},
        sizing_model_params={"notional_usd": 100_000.0},
        executed_at=datetime.datetime(2024, 1, 1, 12, 0, 0),
        git_commit_hash="abc123",
    )
    result = BacktestResult(
        run_id="test",
        asset="gold",
        trades=[],
        equity_curve=pd.Series(dtype=float),
        positions=pd.Series(dtype=float),
        pnl_series=pd.Series(dtype=float),
        metadata=metadata,
        signal_evaluation=None,
    )
    assert result.signal_evaluation is None
    assert result.trades == []


def test_performance_report_instantiation() -> None:
    """PerformanceReport is valid with empty metric dicts."""
    report = PerformanceReport(
        run_id="test",
        initial_capital_usd=1_000_000.0,
        scalar_metrics={},
        rolling_metrics={},
        trade_statistics={},
        signal_metrics={},
    )
    assert report.run_id == "test"
    assert report.initial_capital_usd == 1_000_000.0


def test_datasource_is_abstract() -> None:
    """DataSource cannot be instantiated directly."""
    with pytest.raises(TypeError):
        DataSource()  # type: ignore[abstract]


def test_indicator_is_abstract() -> None:
    """Indicator cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Indicator()  # type: ignore[abstract]


def test_signal_generator_is_abstract() -> None:
    """SignalGenerator cannot be instantiated directly."""
    with pytest.raises(TypeError):
        SignalGenerator()  # type: ignore[abstract]


def test_backtest_engine_is_abstract() -> None:
    """BacktestEngine cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BacktestEngine()  # type: ignore[abstract]


def test_position_sizer_is_abstract() -> None:
    """PositionSizer cannot be instantiated directly."""
    with pytest.raises(TypeError):
        PositionSizer()  # type: ignore[abstract]
