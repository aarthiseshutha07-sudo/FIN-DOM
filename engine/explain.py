"""Human-readable explanations for FIN-DOM cascade results."""

from __future__ import annotations

import pandas as pd


def explain(result: dict, entity_id: str) -> list[str]:
    """Explain an institution's scenario result in up to three sentences."""

    state = result["state"]
    ledger = result["ledger"]

    matches = state[state["entity_id"] == entity_id]

    if matches.empty:
        raise ValueError(f"Unknown entity ID: {entity_id}")

    entity = matches.iloc[0]

    name = entity["name"]
    status = entity["status"]
    stress = float(entity["final_stress"])
    baseline = float(entity["baseline_score"])
    scenario = float(entity["scenario_score"])

    sentences = [
        (
            f"{name} is classified as {status}, with final stress "
            f"of {stress:.1%}."
        ),
        (
            f"Its baseline risk score is {baseline:.1f}/100, "
            f"and its scenario score is {scenario:.1f}/100."
        ),
    ]

    # Find the largest recorded losses experienced by this institution.
    if not ledger.empty:
        losses = ledger[
            (ledger["creditor_id"] == entity_id)
            & (ledger["debtor_id"] != "SHOCK")
        ]

        losses = losses.groupby("debtor_id")["loss_bn"].sum()
        losses = losses[losses > 0].sort_values(ascending=False)

        if not losses.empty:
            main_source = losses.index[0]
            loss_amount = float(losses.iloc[0])
            sentences.append(
                f"The largest recorded contagion loss came from "
                f"{main_source}, contributing {loss_amount:.2f} "
                f"billion in modeled losses."
            )
        elif stress > 0:
            sentences.append(
                "No incoming contagion loss was recorded; "
                "the stress may come from the initial shock."
            )
        else:
            sentences.append(
                "No stress was recorded for this institution "
                "in the scenario."
            )
    else:
        sentences.append("The scenario loss ledger contains no entries.")

    return sentences