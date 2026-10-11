
"""Baseline risk scoring for FIN-DOM."""

from __future__ import annotations

import pandas as pd

from engine.params import SCORE_WEIGHTS


def _normalize(series: pd.Series) -> pd.Series:
    """Normalize values to the 0–1 range."""
    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(0.0, index=series.index)

    return (series - minimum) / (maximum - minimum)


def compute_baseline(
    entities_df: pd.DataFrame,
    exposures_df: pd.DataFrame,
) -> pd.DataFrame:
    """Calculate baseline risk scores from 0 to 100."""

    result = entities_df.copy()

    # 1. Leverage = total assets / capital buffer
    result["leverage"] = (
        result["total_assets_bn"] / result["capital_buffer_bn"]
    )

    # 2. Outgoing exposure / capital buffer
    outgoing = exposures_df.groupby("creditor_id")["exposure_bn"].sum()

    result["outgoing_exposure_bn"] = (
        result["entity_id"].map(outgoing).fillna(0.0)
    )

    result["exposure_to_capital"] = (
        result["outgoing_exposure_bn"] / result["capital_buffer_bn"]
    )

    # 3. Interconnectedness = incoming links + outgoing links
    outgoing_links = exposures_df.groupby("creditor_id").size()
    incoming_links = exposures_df.groupby("debtor_id").size()

    result["interconnectedness"] = (
        result["entity_id"].map(outgoing_links).fillna(0)
        + result["entity_id"].map(incoming_links).fillna(0)
    )

    # Normalize all components
    leverage_norm = _normalize(result["leverage"])
    exposure_norm = _normalize(result["exposure_to_capital"])
    connections_norm = _normalize(result["interconnectedness"])

    # Weighted baseline score
    result["baseline_score"] = 100 * (
        SCORE_WEIGHTS["leverage"] * leverage_norm
        + SCORE_WEIGHTS["exposure_to_capital"] * exposure_norm
        + SCORE_WEIGHTS["interconnectedness"] * connections_norm
    )

    return result
