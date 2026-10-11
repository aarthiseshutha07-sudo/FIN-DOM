
"""Iterative financial contagion simulation for FIN-DOM."""

from __future__ import annotations

import math

import pandas as pd

from engine.params import (
    CONVERGENCE_TOL,
    FAILED_MIN,
    LOSS_RATE,
    MAX_ROUNDS,
    SCORE_WEIGHTS,
    SHOCK_SCALE,
    STABLE_MAX,
    STATUS_FAILED,
    STATUS_STABLE,
    STATUS_STRESSED,
)
from engine.risk import compute_baseline


STATE_COLUMNS = [
    "entity_id",
    "name",
    "type",
    "region",
    "total_assets_bn",
    "capital_buffer_bn",
    "baseline_score",
    "final_stress",
    "scenario_score",
    "status",
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
    entities: pd.DataFrame,
    exposures: pd.DataFrame,
    source_id: str,
    severity: float,
) -> dict:
    """Simulate stress propagation and return state, ledger, and snapshots.

    severity must be between 0 and 1.
    Monetary amounts are expressed in fictional billions.
    """

    if not 0 <= severity <= 1 or not math.isfinite(severity):
        raise ValueError("severity must be a finite number between 0 and 1.")

    if source_id not in entities["entity_id"].values:
        raise ValueError(f"Unknown source institution: {source_id}")

    if (entities["capital_buffer_bn"] <= 0).any():
        raise ValueError("All capital buffers must be greater than zero.")

    if (exposures["exposure_bn"] < 0).any():
        raise ValueError("Exposure amounts cannot be negative.")

    # Calculate baseline scores before applying the scenario.
    baseline = compute_baseline(entities, exposures)

    ids = baseline["entity_id"].tolist()
    buffers = baseline.set_index("entity_id")["capital_buffer_bn"].to_dict()
    base_scores = baseline.set_index("entity_id")["baseline_score"].to_dict()

    # Stress and losses are stored by entity ID.
    stress = {entity_id: 0.0 for entity_id in ids}
    initial_stress = min(1.0, severity * SHOCK_SCALE)
    initial_loss = initial_stress * buffers[source_id]

    # Round 0: apply the external shock to the selected institution.
    stress[source_id] = initial_stress

    snapshots = {0: stress.copy()}
    ledger_rows = [
        {
            "round": 0,
            "creditor_id": source_id,
            "debtor_id": "SHOCK",
            "exposure_bn": 0.0,
            "debtor_stress": initial_stress,
            "stress_increase": initial_stress,
            "loss_bn": initial_loss,
        }
    ]

    # Remember when each institution first becomes non-Stable.
    first_affected = {
        entity_id: (0 if stress[entity_id] >= STABLE_MAX else None)
        for entity_id in ids
    }

    # Keep a record of the shock loss. Each round recalculates total losses
    # from the initial shock plus losses implied by the previous round.
    initial_losses = {entity_id: 0.0 for entity_id in ids}
    initial_losses[source_id] = initial_loss

    # Propagate stress through the exposure network.
    for round_number in range(1, MAX_ROUNDS + 1):
        previous = stress.copy()
        next_stress = {}

        for entity_id in ids:
            incoming_loss = 0.0

            # A creditor incurs losses when its debtor is under stress.
            creditor_exposures = exposures[
                exposures["creditor_id"] == entity_id
            ]

            for _, exposure in creditor_exposures.iterrows():
                debtor_id = exposure["debtor_id"]
                incoming_loss += (
                    LOSS_RATE
                    * float(exposure["exposure_bn"])
                    * previous[debtor_id]
                )

            total_loss = initial_losses[entity_id] + incoming_loss
            next_stress[entity_id] = min(
                1.0, total_loss / buffers[entity_id]
            )

        # Record incremental losses caused by stress increases this round.
        for _, exposure in exposures.iterrows():
            creditor_id = exposure["creditor_id"]
            debtor_id = exposure["debtor_id"]
            stress_increase = max(
                0.0, next_stress[debtor_id] - previous[debtor_id]
            )

            if stress_increase <= 0:
                continue

            loss = (
                LOSS_RATE
                * float(exposure["exposure_bn"])
                * stress_increase
            )

            ledger_rows.append(
                {
                    "round": round_number,
                    "creditor_id": creditor_id,
                    "debtor_id": debtor_id,
                    "exposure_bn": float(exposure["exposure_bn"]),
                    "debtor_stress": previous[debtor_id],
                    "stress_increase": stress_increase,
                    "loss_bn": loss,
                }
            )

        stress = next_stress
        snapshots[round_number] = stress.copy()

        for entity_id in ids:
            if (
                first_affected[entity_id] is None
                and stress[entity_id] >= STABLE_MAX
            ):
                first_affected[entity_id] = round_number

        if all(
            abs(stress[entity_id] - previous[entity_id])
            <= CONVERGENCE_TOL
            for entity_id in ids
        ):
            break

    state = baseline.copy()
    state["final_stress"] = state["entity_id"].map(stress)
    state["scenario_score"] = (
        state["baseline_score"]
        + (100.0 - state["baseline_score"]) * state["final_stress"]
    )

    def classify(value: float) -> str:
        if value < STABLE_MAX:
            return STATUS_STABLE
        if value >= FAILED_MIN:
            return STATUS_FAILED
        return STATUS_STRESSED

    state["status"] = state["final_stress"].map(classify)
    state["first_round_affected"] = state["entity_id"].map(first_affected)

    # Preserve the expected public table shapes.
    for column in STATE_COLUMNS:
        if column not in state.columns:
            state[column] = None

    state = state[STATE_COLUMNS]
    ledger = pd.DataFrame(ledger_rows, columns=LEDGER_COLUMNS)

    return {
        "state": state,
        "ledger": ledger,
        "snapshots": snapshots,
    }
