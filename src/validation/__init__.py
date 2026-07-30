"""Statistical validation module for the Commodity Systematic Research Platform.

Implements:
  - Walk-forward out-of-sample testing with embargo periods
  - Sharpe ratio standard errors (Newey-West approximation)
  - Probabilistic Sharpe Ratio (PSR)
  - Deflated Sharpe Ratio (DSR) with MLflow trial count

References:
    Bailey, D.H. & López de Prado, M. (2012). The Sharpe Ratio
    Efficient Frontier. Journal of Risk, 15(2), 3-44.
"""

from src.validation.inference import (
    deflated_sharpe_ratio,
    expected_max_sharpe,
    probabilistic_sharpe_ratio,
    sharpe_se,
)
from src.validation.walk_forward import WalkForwardValidator

__all__ = [
    "WalkForwardValidator",
    "sharpe_se",
    "probabilistic_sharpe_ratio",
    "deflated_sharpe_ratio",
    "expected_max_sharpe",
]
