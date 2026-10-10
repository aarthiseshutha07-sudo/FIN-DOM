
"""Baseline risk scoring.

Task A2 stub: returns dummy scores until Task A3.
"""

from __future__ import annotations

import pandas as pd

_STUB_SCORE = 50.0


def compute_baseline(
    entities_df: pd.DataFrame,
    exposures_df: pd.DataFrame,
) -> pd.DataFrame:
    """Return entities with a baseline_score column ranging from 0 to 100."""
    if not isinstance(entities_df, pd.DataFrame):
        raise TypeError("entities_df must be a pandas DataFrame")

    result = entities_df.copy()
    result["baseline_score"] = _STUB_SCORE
    return result
