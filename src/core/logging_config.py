"""Logging configuration utility for the Commodity Systematic Research Platform.

Call setup_logging(config) once at the application entry point.
All other modules obtain loggers via logging.getLogger(__name__).
"""

from __future__ import annotations

import logging
import pathlib
import sys

from src.core.config import Config


def setup_logging(config: Config) -> None:
    """Configure the root logger from the loaded Config.

    Creates the log directory if it does not exist. Adds a StreamHandler
    (stdout, INFO level) and a FileHandler (level and path from config).
    Guards against duplicate handlers so repeated calls in tests are safe.

    Args:
        config: Populated Config instance from Config.load().
    """
    log_dir = pathlib.Path(config.paths["logs"])
    log_dir.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    level = getattr(logging, config.logging["level"].upper(), logging.INFO)
    root_logger.setLevel(level)

    if root_logger.handlers:
        return

    formatter = logging.Formatter(config.logging["format"])

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(logging.INFO)
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    file_handler = logging.FileHandler(config.logging["file"])
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
