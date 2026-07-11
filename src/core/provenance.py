"""Run provenance utilities — git SHA, dirty flag, package versions.

Called once per backtest run to capture the exact code and environment
state. All functions are non-fatal: they return safe defaults when git
is unavailable or a package is not installed.

The captured provenance is stored in BacktestMetadata and serialized
to params.json by RunManager.save(). The frontend Artifacts tab reads
and displays these fields without any additional endpoint work.

See Known Limitation #13 in ARCHITECTURE.md (data manifests and
run provenance).
"""

from __future__ import annotations

import importlib.metadata
import logging
import subprocess
from typing import TypedDict

_logger = logging.getLogger(__name__)

# Packages to capture versions for.
# These are the packages most likely to affect numerical results.
_VERSION_PACKAGES = [
    "pandas",
    "numpy",
    "yfinance",
    "mlflow",
    "clickhouse-connect",
    "pyarrow",
]


class ProvenanceSnapshot(TypedDict):
    """Provenance fields captured at backtest run time."""

    git_sha: str
    dirty_flag: bool
    package_versions: dict[str, str]


def get_git_sha(short: bool = True) -> str:
    """Return the current git commit SHA.

    Args:
        short: If True, return 8-character short SHA. If False, full SHA.

    Returns:
        Git commit SHA string. 'unknown' if git is unavailable or
        the current directory is not inside a git repository.
    """
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "rev-parse", "HEAD"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            sha = result.stdout.strip()
            return sha[:8] if short else sha
        _logger.debug(
            "provenance: git rev-parse failed (returncode=%d)", result.returncode
        )
        return "unknown"
    except Exception as exc:  # noqa: BLE001
        _logger.debug("provenance: git_sha unavailable — %s", exc)
        return "unknown"


def get_git_dirty() -> bool:
    """Return True if the working tree has uncommitted changes.

    Returns:
        True if any tracked or untracked files are modified.
        False if the working tree is clean or git is unavailable.
    """
    try:
        result = subprocess.run(  # noqa: S603
            ["git", "status", "--porcelain"],  # noqa: S607
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return bool(result.stdout.strip())
        return False
    except Exception as exc:  # noqa: BLE001
        _logger.debug("provenance: git_dirty unavailable — %s", exc)
        return False


def get_package_versions(packages: list[str] | None = None) -> dict[str, str]:
    """Return installed versions for the specified packages.

    Args:
        packages: List of package names to check. If None, uses the
            default set defined in _VERSION_PACKAGES.

    Returns:
        Dict mapping package name → version string.
        'unknown' for any package that cannot be found.
    """
    if packages is None:
        packages = _VERSION_PACKAGES

    versions: dict[str, str] = {}
    for pkg in packages:
        try:
            versions[pkg] = importlib.metadata.version(pkg)
        except importlib.metadata.PackageNotFoundError:
            versions[pkg] = "unknown"
        except Exception as exc:  # noqa: BLE001
            _logger.debug("provenance: version check failed for %s — %s", pkg, exc)
            versions[pkg] = "unknown"

    return versions


def capture() -> ProvenanceSnapshot:
    """Capture all provenance in one call.

    Returns:
        Dict with keys: git_sha (str), dirty_flag (bool),
        package_versions (dict[str, str]).

    This is the single function called by VectorizedBacktester
    when constructing BacktestMetadata.
    """
    return {
        "git_sha": get_git_sha(short=True),
        "dirty_flag": get_git_dirty(),
        "package_versions": get_package_versions(),
    }
