"""Configuration loader for the Commodity Systematic Research Platform.

Reads and validates config.yaml, assets.yaml, and strategies.yaml from the
config/ directory. Raises ConfigError on any missing required key.
See Architecture Section 14 for the configuration reference.
"""

from __future__ import annotations

import pathlib
from typing import Any

import yaml


class ConfigError(Exception):
    """Raised when required configuration keys are missing or files cannot be parsed.

    The error message identifies the failing key path, for example:
        "Missing required key: paths.raw_data in config.yaml"
    """


class Config:
    """Holds loaded configuration as typed attributes.

    Do not instantiate directly. Use Config.load().

    Attributes:
        paths: File system path configuration.
        logging: Logging level, format, and output path.
        costs: Default transaction cost parameters.
        sizing: Position sizing method and parameters.
        data: Data date range defaults.
        assets: Per-asset metadata (multipliers, ticks, tickers) for all six
                commodity assets.
        strategies: Strategy parameter defaults for all four Phase 1 strategies.
    """

    def __init__(
        self,
        paths: dict[str, str],
        logging: dict[str, Any],
        costs: dict[str, Any],
        sizing: dict[str, Any],
        data: dict[str, Any],
        assets: dict[str, dict],
        strategies: dict[str, dict],
        _config: dict[str, Any],
    ) -> None:
        self.paths = paths
        self.logging = logging
        self.costs = costs
        self.sizing = sizing
        self.data = data
        self.assets = assets
        self.strategies = strategies
        self._config = _config

    @classmethod
    def load(cls, config_dir: str = "config/") -> Config:
        """Load and validate all configuration files.

        Reads config.yaml, assets.yaml, and strategies.yaml from config_dir.
        Raises ConfigError on the first missing required key or unparseable file.
        Never substitutes defaults for missing keys.

        Args:
            config_dir: Path to the directory containing YAML configuration files.

        Returns:
            Populated Config instance.

        Raises:
            ConfigError: If any required key is absent or any file cannot be parsed.
        """
        base = pathlib.Path(config_dir)

        # --- Load raw YAML content ---
        try:
            with open(base / "config.yaml") as f:
                raw_config = yaml.safe_load(f)
        except Exception as exc:
            raise ConfigError(f"Failed to read config.yaml: {exc}") from exc

        try:
            with open(base / "assets.yaml") as f:
                raw_assets = yaml.safe_load(f)
        except Exception as exc:
            raise ConfigError(f"Failed to read assets.yaml: {exc}") from exc

        try:
            with open(base / "strategies.yaml") as f:
                raw_strategies = yaml.safe_load(f)
        except Exception as exc:
            raise ConfigError(f"Failed to read strategies.yaml: {exc}") from exc

        # --- Validate config.yaml top-level sections ---
        for section in ["paths", "logging", "costs", "sizing", "data"]:
            if section not in raw_config:
                raise ConfigError(f"Missing required key: {section} in config.yaml")

        # --- Validate config.yaml leaf keys ---
        for key in ["raw_data", "processed_data", "runs", "logs"]:
            if key not in raw_config["paths"]:
                raise ConfigError(f"Missing required key: paths.{key} in config.yaml")

        for key in ["level", "format", "file"]:
            if key not in raw_config["logging"]:
                raise ConfigError(f"Missing required key: logging.{key} in config.yaml")

        for key in ["default_commission_usd", "default_slippage_ticks"]:
            if key not in raw_config["costs"]:
                raise ConfigError(f"Missing required key: costs.{key} in config.yaml")

        for key in ["method", "fixed_notional_usd", "target_annual_vol"]:
            if key not in raw_config["sizing"]:
                raise ConfigError(f"Missing required key: sizing.{key} in config.yaml")

        if "default_start_date" not in raw_config["data"]:
            raise ConfigError(
                "Missing required key: data.default_start_date in config.yaml"
            )

        # --- Validate assets.yaml ---
        required_assets = ["gold", "silver", "copper", "wti", "brent", "natural_gas"]
        required_asset_fields = [
            "ticker_continuous",
            "contract_multiplier",
            "tick_size",
            "tick_value",
        ]
        for asset in required_assets:
            if asset not in raw_assets:
                raise ConfigError(f"Missing required asset: {asset} in assets.yaml")
            for field in required_asset_fields:
                if field not in raw_assets[asset]:
                    raise ConfigError(
                        f"Missing required key: {asset}.{field} in assets.yaml"
                    )

        # --- Validate strategies.yaml ---
        required_strategies = [
            "ema_crossover",
            "momentum",
            "donchian_breakout",
            "rsi_reversion",
        ]
        for strategy in required_strategies:
            if strategy not in raw_strategies:
                raise ConfigError(
                    f"Missing required strategy: {strategy} in strategies.yaml"
                )

        return cls(
            paths=raw_config["paths"],
            logging=raw_config["logging"],
            costs=raw_config["costs"],
            sizing=raw_config["sizing"],
            data=raw_config["data"],
            assets=raw_assets,
            strategies=raw_strategies,
            _config=raw_config,
        )

    @property
    def mlflow_tracking_uri(self) -> str:
        """MLflow tracking server URI. Default: local filesystem."""
        uri = self._config.get("mlflow", {}).get("tracking_uri", "file:./data/mlruns")
        return str(uri)

    @property
    def mlflow_experiment_prefix(self) -> str:
        """MLflow experiment name prefix. Experiments: {prefix}_{asset}."""
        prefix = self._config.get("mlflow", {}).get(
            "experiment_prefix", "commodity_research"
        )
        return str(prefix)

    @property
    def storage_backend(self) -> str:
        return str(self._config.get("storage", {}).get("backend", "parquet"))

    @property
    def clickhouse_host(self) -> str:
        return str(
            self._config.get("storage", {})
            .get("clickhouse", {})
            .get("host", "localhost")
        )

    @property
    def clickhouse_port(self) -> int:
        return int(
            self._config.get("storage", {}).get("clickhouse", {}).get("port", 8123)
        )

    @property
    def clickhouse_database(self) -> str:
        return str(
            self._config.get("storage", {})
            .get("clickhouse", {})
            .get("database", "commodity_research")
        )

    @property
    def clickhouse_table_ohlcv(self) -> str:
        return str(
            self._config.get("storage", {})
            .get("clickhouse", {})
            .get("table_ohlcv", "ohlcv_continuous")
        )

    @property
    def clickhouse_connect_timeout(self) -> int:
        return int(
            self._config.get("storage", {})
            .get("clickhouse", {})
            .get("connect_timeout", 10)
        )

    @property
    def clickhouse_send_receive_timeout(self) -> int:
        """ClickHouse query send/receive timeout in seconds.

        Controls how long clickhouse-connect waits for query results.
        Default 30 seconds is appropriate for single-asset OHLCV reads.
        Increase if running heavy aggregations (e.g. multi-year range scans).
        Controlled by storage.clickhouse.send_receive_timeout in config.yaml.
        """
        return int(
            self._config.get("storage", {})
            .get("clickhouse", {})
            .get("send_receive_timeout", 30)
        )
