from __future__ import annotations

from pathlib import Path

from .catalog_schema import compile_gathering_pacing
from .catalog_wave5 import wave5_method_catalog
from .catalog_wave6 import wave6_method_catalog


def wave7_method_catalog() -> dict[str, dict]:
    """Compile gathering V2 pacing from the data catalogue.

    Wave 7 previously embedded the pacing policy in Python. Wave 8 keeps the
    compiler in code but moves the policy, multipliers and model declarations to
    catalogue/gathering/pacing.yml so there is one editable source of truth.
    """
    base = wave5_method_catalog()
    base.update(wave6_method_catalog())
    return compile_gathering_pacing(Path("catalogue/gathering/pacing.yml"), base)
