"""Research layer base imports.

Re-exports Indicator from src.core.registry so that research-layer
implementations import from src.research without coupling to src.core.
See ADR-006 for the indicator design specification.
"""

from src.core.registry import Indicator  # noqa: F401
