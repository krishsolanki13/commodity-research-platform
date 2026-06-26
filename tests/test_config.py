"""Tests for Config loader and ConfigError behaviour.

Validates that Config.load() raises ConfigError (not KeyError or any other
exception) on missing required keys, and that all six assets and four strategies
load correctly from valid YAML files.
"""

from __future__ import annotations

import pathlib

import pytest
import yaml

from src.core.config import Config, ConfigError


def test_config_loads_without_error(tmp_path: pathlib.Path) -> None:
    """Config.load() returns a Config instance when all files are valid."""
    _write_valid_config_files(tmp_path)
    config = Config.load(str(tmp_path) + "/")
    assert isinstance(config, Config)


def test_all_six_assets_present(tmp_path: pathlib.Path) -> None:
    """All six commodity assets are present in loaded config."""
    _write_valid_config_files(tmp_path)
    config = Config.load(str(tmp_path) + "/")
    expected = {"gold", "silver", "copper", "wti", "brent", "natural_gas"}
    assert set(config.assets.keys()) == expected


def test_all_four_strategies_present(tmp_path: pathlib.Path) -> None:
    """All four Phase 1 strategies are present in loaded config."""
    _write_valid_config_files(tmp_path)
    config = Config.load(str(tmp_path) + "/")
    expected = {"ema_crossover", "momentum", "donchian_breakout", "rsi_reversion"}
    assert expected.issubset(set(config.strategies.keys()))


def test_missing_required_key_raises_config_error(tmp_path: pathlib.Path) -> None:
    """ConfigError (not KeyError) is raised when a required key is missing."""
    _write_valid_config_files(tmp_path)
    config_path = tmp_path / "config.yaml"
    with open(config_path) as f:
        raw = yaml.safe_load(f)
    del raw["paths"]["raw_data"]
    with open(config_path, "w") as f:
        yaml.dump(raw, f)
    with pytest.raises(ConfigError):
        Config.load(str(tmp_path) + "/")


def test_gold_asset_metadata_complete(tmp_path: pathlib.Path) -> None:
    """Gold asset entry contains all required metadata fields."""
    _write_valid_config_files(tmp_path)
    config = Config.load(str(tmp_path) + "/")
    gold = config.assets["gold"]
    for field in [
        "ticker_continuous",
        "contract_multiplier",
        "tick_size",
        "tick_value",
    ]:
        assert field in gold, f"Missing field: {field}"


def test_default_commission_is_positive(tmp_path: pathlib.Path) -> None:
    """Default commission value is a positive number."""
    _write_valid_config_files(tmp_path)
    config = Config.load(str(tmp_path) + "/")
    assert config.costs["default_commission_usd"] > 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_valid_config_files(tmp_path: pathlib.Path) -> None:
    """Write minimal valid YAML files to tmp_path for use in tests."""
    config_yaml = {
        "paths": {
            "raw_data": "data/raw/",
            "processed_data": "data/processed/",
            "runs": "data/runs/",
            "logs": "logs/",
        },
        "logging": {
            "level": "INFO",
            "format": "%(asctime)s | %(name)s | %(levelname)s | %(message)s",
            "file": "logs/platform.log",
        },
        "costs": {"default_commission_usd": 5.00, "default_slippage_ticks": 1},
        "sizing": {
            "method": "fixed_notional",
            "fixed_notional_usd": 100000,
            "target_annual_vol": 0.15,
        },
        "data": {"default_start_date": "2010-01-01", "default_end_date": None},
    }
    assets_yaml = {
        asset: {
            "ticker_continuous": f"{asset.upper()}=F",
            "exchange": "COMEX",
            "currency": "USD",
            "unit": "unit",
            "contract_multiplier": 100,
            "tick_size": 0.10,
            "tick_value": 10.00,
        }
        for asset in ["gold", "silver", "copper", "wti", "brent", "natural_gas"]
    }
    strategies_yaml = {
        "ema_crossover": {
            "fast_period": 50,
            "slow_period": 200,
            "signal_threshold": 0.0,
        },
        "momentum": {
            "lookback_period": 20,
            "z_score_window": 63,
            "signal_threshold": 0.5,
        },
        "donchian_breakout": {"channel_period": 20},
        "rsi_reversion": {
            "period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70,
        },
    }
    with open(tmp_path / "config.yaml", "w") as f:
        yaml.dump(config_yaml, f)
    with open(tmp_path / "assets.yaml", "w") as f:
        yaml.dump(assets_yaml, f)
    with open(tmp_path / "strategies.yaml", "w") as f:
        yaml.dump(strategies_yaml, f)
