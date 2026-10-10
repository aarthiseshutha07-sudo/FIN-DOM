"""Multi-round contagion cascade.

*** STUB (task A2) ***
`run_cascade` returns a correctly shaped result in which NOTHING spreads, so
the app can be built against it. The real algorithm (defined in
docs/ENGINE_RULES.md) is implemented in task A4.
"""

from __future__ import annotations

import pandas as pd

from engine import params
from engine.risk import compute_baseline

# Column names of the result tables (agreed in the Stage 3-4 design).
STATE_COLUMNS = [
    "entity_id",
    "baseline_score",
    "final_stress",
    "status",
    "scenario_score",
    "first_round_affected",
]
LEDGER_COLUMNS = [
    "round",
    "creditor_id",
    "debtor_id",
    "exposure_bn",
    "debtor_stress",
    "stress_increase",
    "loss_bn",
]


def run_cascade(
    entities_df: pd.DataFrame,
    exposures_df: pd.DataFrame,
    source_id: str,
    severity: float,
) -> dict:
    """Run a shock scenario and return the result.

    STUB: returns the "nothing happens" result. Real logic comes in task A4.

    Args:
        entities_df: validated entities table from `load_data()`.
        exposures_df: validated exposures table from `load_data()`.
        source_id: `entity_id` of the entity that is shocked.
        severity: shock severity from 0.0 to 1.0 (the UI's 0-100% slider / 100).

    Returns:
        A dict with three parts:
          "state":     one row per entity, columns = STATE_COLUMNS.
                       `first_round_affected` is empty (<NA>) for entities
                       that never leave "Stable".
          "ledger":    one row per loss event, columns = LEDGER_COLUMNS
                       (empty in the stub).
          "snapshots": {round_number: {entity_id: stress}} - the stress of
                       every entity at the end of each round (round 0 only
                       in the stub).
    """
    if source_id not in set(entities_df["entity_id"]):
        raise ValueError(f"source_id '{source_id}' is not a known entity_id")
    if not 0.0 <= float(severity) <= 1.0:
        raise ValueError(f"severity must be between 0 and 1, got {severity}")

    baseline = compute_baseline(entities_df, exposures_df)

    state = pd.DataFrame({
        "entity_id": baseline["entity_id"],
        "baseline_score": baseline["baseline_score"],
        "final_stress": 0.0,
        "status": params.STATUS_STABLE,
        "scenario_score": baseline["baseline_score"],
        "first_round_affected": pd.Series([pd.NA] * len(baseline), dtype="Int64"),
    })[STATE_COLUMNS]

    ledger = pd.DataFrame(columns=LEDGER_COLUMNS)
    snapshots = {0: {entity_id: 0.0 for entity_id in baseline["entity_id"]}}

    return {"state": state, "ledger": ledger, "snapshots": snapshots}
