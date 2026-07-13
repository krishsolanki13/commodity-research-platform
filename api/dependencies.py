from __future__ import annotations

from pathlib import Path

from api.exceptions import ApiError

KNOWN_ASSETS: set[str] = {
    "gold",
    "silver",
    "copper",
    "wti",
    "brent",
    "natural_gas",
}


def get_asset_or_404(asset: str) -> str:
    """Validate asset is in the platform universe; raise 404 if not."""
    if asset not in KNOWN_ASSETS:
        raise ApiError(
            code="ASSET_NOT_FOUND",
            message=f"Asset '{asset}' is not in the universe.",
            status=404,
        )
    return asset


def get_run_path_or_404(run_id: str) -> Path:
    """Resolve run directory from run_id; raise 404 if not found on disk.

    Config exposes paths as a dict; runs directory is paths["runs"].
    """
    # Deferred import: avoids loading all of src/ at API startup
    from src.core.config import Config  # noqa: PLC0415

    cfg = Config.load()
    run_dir = Path(cfg.paths["runs"]) / run_id
    if not run_dir.exists():
        raise ApiError(
            code="RUN_NOT_FOUND",
            message=f"Run '{run_id}' not found.",
            status=404,
        )
    return run_dir
