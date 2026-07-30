"""Statistical inference for Sharpe ratio estimation.

All functions operate on daily return series. Sharpe ratios are annualized
by multiplying by sqrt(252). Standard errors use the Newey-West approximation
accounting for non-normality (skewness and excess kurtosis).
"""

from __future__ import annotations

import math

import pandas as pd


def sharpe_se(returns: pd.Series, annual_factor: float = 252.0) -> float:
    """Compute the standard error of the annualized Sharpe ratio estimate.

    Uses the Newey-West approximation that accounts for non-normality.
    For large T and normally distributed returns, SE ≈ sqrt(annual_factor/T).

    Formula from Mertens (2002) / Bailey & López de Prado (2012):
        SE = sqrt((1 + SR²/2 × (1 - skew×SR/6 + γ₂×SR²/24)) / (T-1)) × sqrt(F)
    where SR is the annualized Sharpe ratio, T is sample size, F is annual_factor,
    and γ₂ is excess kurtosis (returned directly by pandas .kurtosis()).

    Args:
        returns: Daily P&L return series (not annualized).
        annual_factor: Annualization factor (252 for daily returns).

    Returns:
        Standard error of the annualized Sharpe ratio.
        Returns NaN if T < 4 (insufficient data for skewness/kurtosis).
    """
    clean = returns.dropna()
    T = len(clean)  # noqa: N806
    if T < 4:
        return float("nan")

    mean_r = float(clean.mean())
    std_r = float(clean.std(ddof=1))

    if std_r <= 0:
        return float("nan")

    # Annualized Sharpe ratio
    sr = (mean_r / std_r) * math.sqrt(annual_factor)

    # Higher moments — pandas .kurtosis() returns excess kurtosis (Fisher, γ₂ = kurt − 3)
    skew = float(clean.skew())
    kurt = float(clean.kurtosis())  # excess kurtosis; used directly in the formula

    # Newey-West SE approximation (annualized)
    se = math.sqrt(
        (1.0 + (sr**2) / 2.0 * (1.0 - skew * sr / 6.0 + kurt * sr**2 / 24.0)) / (T - 1)
    ) * math.sqrt(annual_factor)

    return float(se)


def probabilistic_sharpe_ratio(
    returns: pd.Series,
    sr_benchmark: float = 0.0,
    annual_factor: float = 252.0,
) -> float:
    """Compute the Probabilistic Sharpe Ratio (PSR).

    PSR(SR₀) = P[SR > SR₀] = Φ[(SR_observed − SR₀) / SE(SR)]

    For SR₀ = 0: PSR answers "what is the probability that the true
    Sharpe ratio is positive?"

    Args:
        returns: Daily return series.
        sr_benchmark: Benchmark Sharpe ratio to test against. Default 0.
        annual_factor: Annualization factor.

    Returns:
        PSR as a probability in [0, 1]. Returns NaN if SE cannot be computed.
    """
    clean = returns.dropna()
    T = len(clean)  # noqa: N806
    if T < 4:
        return float("nan")

    mean_r = float(clean.mean())
    std_r = float(clean.std(ddof=1))
    if std_r <= 0:
        return float("nan")

    sr_observed = (mean_r / std_r) * math.sqrt(annual_factor)
    se = sharpe_se(returns, annual_factor)

    if math.isnan(se) or se <= 0:
        return float("nan")

    z = (sr_observed - sr_benchmark) / se
    return float(_norm_cdf(z))


def expected_max_sharpe(n_trials: int, annual_factor: float = 252.0) -> float:  # noqa: ARG001
    """Compute E[max SR | n_trials] — the expected maximum Sharpe ratio
    from n_trials independent trials under the null hypothesis of no skill.

    This is the benchmark SR₀ used in the Deflated Sharpe Ratio.

    Formula (Bailey & López de Prado 2012, Equation 11):
        E[max SR] = (1−γ)×Φ⁻¹(1 − 1/N) + γ×Φ⁻¹(1 − 1/(N×e))
    where γ = Euler-Mascheroni constant ≈ 0.5772

    Args:
        n_trials: Number of independent trials (strategy evaluations).
        annual_factor: Kept for API consistency; not used in the formula.

    Returns:
        Expected maximum Sharpe ratio. Returns 0.0 if n_trials <= 1
        (no multiple-testing correction when only one trial exists).
    """
    if n_trials <= 1:
        return 0.0

    gamma_em = 0.5772156649015328  # Euler-Mascheroni constant

    p1 = 1.0 - 1.0 / n_trials
    p2 = 1.0 - 1.0 / (n_trials * math.e)

    z1 = _norm_ppf(p1)
    z2 = _norm_ppf(p2)

    return float((1.0 - gamma_em) * z1 + gamma_em * z2)


def deflated_sharpe_ratio(
    returns: pd.Series,
    n_trials: int,
    annual_factor: float = 252.0,
) -> float:
    """Compute the Deflated Sharpe Ratio (DSR).

    DSR = PSR[E[max SR | n_trials]] — the probability that the true Sharpe
    ratio exceeds the expected maximum Sharpe from n_trials trials under H₀.

    DSR corrects PSR for multiple testing: if n_trials parameter combinations
    were tested and this is the best result, the benchmark is not SR₀ = 0 but
    SR₀ = E[max SR | n_trials], which accounts for selection bias.

    DSR ≤ PSR always. Values > 0.95 conventionally indicate significance.

    Args:
        returns: Daily return series (full in-sample).
        n_trials: Number of trials run (from MLflow run count).
        annual_factor: Annualization factor.

    Returns:
        DSR in [0, 1].
    """
    sr_bench = expected_max_sharpe(n_trials, annual_factor)
    return probabilistic_sharpe_ratio(
        returns, sr_benchmark=sr_bench, annual_factor=annual_factor
    )


# ── Normal distribution utilities (scipy-free) ────────────────────────────────


def _norm_cdf(z: float) -> float:
    """Standard normal CDF using erfc. Exact, no scipy dependency."""
    return 0.5 * math.erfc(-z / math.sqrt(2.0))


def _norm_ppf(p: float) -> float:
    """Inverse standard normal CDF (quantile function).

    Rational approximation by Beasley-Springer-Moro (1977).
    Maximum absolute error: ~4.5e-4. Sufficient for DSR computation.
    Verified: _norm_ppf(0.975) ≈ 1.96 (within 0.001).
    """
    if p <= 0.0:
        return float("-inf")
    if p >= 1.0:
        return float("inf")

    a = [
        0.0,
        -3.969683028665376e1,
        2.209460984245205e2,
        -2.759285104469687e2,
        1.383577518672690e2,
        -3.066479806614716e1,
        2.506628277459239,
    ]
    b = [
        0.0,
        -5.447609879822406e1,
        1.615858368580409e2,
        -1.556989798598866e2,
        6.680131188771972e1,
        -1.328068155288572e1,
    ]
    c = [
        -7.784894002430293e-3,
        -3.223964580411365e-1,
        -2.400758277161838,
        -2.549732539343734,
        4.374664141464968,
        2.938163982698783,
    ]
    d = [
        7.784695709041462e-3,
        3.224671290700398e-1,
        2.445134137142996,
        3.754408661907416,
    ]

    p_low = 0.02425
    p_high = 1.0 - p_low

    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        x = (  # noqa: N806
            (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        x = (  # noqa: N806
            (((((a[1] * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * r + a[6])
            * q
            / (((((b[1] * r + b[2]) * r + b[3]) * r + b[4]) * r + b[5]) * r + 1.0)
        )
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        x = (  # noqa: N806
            -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5])
            / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0)
        )

    return float(x)
