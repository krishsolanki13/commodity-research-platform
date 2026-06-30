"""Signal research layer base imports.

Re-exports SignalGenerator from src.core.registry for convenience.
Concrete signal generator implementations import from this module.
See ADR-007 for the RawSignal, PositionSignal, and IC evaluation design.
"""

from src.core.registry import SignalGenerator  # noqa: F401
