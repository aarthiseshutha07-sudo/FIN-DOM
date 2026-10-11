"""Adapter: connects the real FIN-DOM engine (engine/) to the dashboard (app/).

The dashboard views expect the shapes the old mock produced (ids named `id`,
amounts in millions, severity as a percent, a `stress_history` list, ...).
The engine uses its own names (`entity_id`, billions, severity 0-1, `snapshots`,
`ledger`). Every translation between the two lives in THIS file, so neither
the views nor the engine need to change.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from engine.cascade import run_cascade
from engine.data_loader import load_data as _engine_load_data
from engine.risk import compute_baseline

BN_TO_M = 1000.0  # the dashboard shows millions; the engine works in billions


@lru_cache(maxsize=1)
def _raw():
    """Engine tables, loaded and validated once."""
    return _engine_load_data()


def load_data():
    """Return (entities, exposures) in the shapes the dashboard views read."""
    ent, exp = _raw()
    entities = pd.DataFrame({
        "id": ent["entity_id"],
        "name": ent["name"],
        "type": ent["type"],
        "region": ent["region"],
        "assets": (ent["total_assets_bn"] * BN_TO_M).round().astype(int),
        "buffer": (ent["capital_buffer_bn"] * BN_TO_M).round().astype(int),
        "leverage": (ent["total_assets_bn"] / ent["capital_buffer_bn"]).round(1),
    })
    exposures = pd.DataFrame({
        "from_id": exp["creditor_id"],   # who is owed money
        "to_id": exp["debtor_id"],       # who owes it
        "amount": (exp["exposure_bn"] * BN_TO_M).round().astype(int),
    })
    return entities, exposures


def baseline():
    """DataFrame with columns: id, baseline_score (0-100)."""
    ent, exp = _raw()
    b = compute_baseline(ent, exp)
    return pd.DataFrame({"id": b["entity_id"], "baseline_score": b["baseline_score"].round(1)})


def run_scenario(source_id, severity_pct):
    """Run the engine cascade and return the dashboard's result dict."""
    ent, exp = _raw()
    out = run_cascade(ent, exp, source_id, severity_pct / 100.0)
    state, ledger, snaps = out["state"], out["ledger"], out["snapshots"]

    rounds = max(snaps)
    history = [dict(snaps[r]) for r in range(rounds + 1)]

    # Contagion losses only: drop the round-0 "SHOCK" row (the external hit itself).
    spread = ledger[ledger["debtor_id"] != "SHOCK"]
    events = [
        {"round": int(r.round), "from_id": r.debtor_id, "to_id": r.creditor_id,
         "loss": round(float(r.loss_bn) * BN_TO_M, 1)}
        for r in spread.itertuples() if r.loss_bn > 0
    ]

    indexed = state.set_index("entity_id")
    return {
        "source_id": source_id,
        "severity": severity_pct,
        "rounds": rounds,
        "stress_history": history,
        "status": indexed["status"].to_dict(),
        "events": events,
        "total_loss": round(sum(e["loss"] for e in events), 1),
        "scenario_score": indexed["scenario_score"].round(1).to_dict(),
    }


def explain_entity(result, entities, entity_id):
    """Dict with before/after stress and readable reasons for one institution."""
    names = entities.set_index("id")["name"].to_dict()
    history = result["stress_history"]

    if entity_id == result["source_id"]:
        reasons = [f"Source of the shock ({result['severity']}% severity)"]
    else:
        mine = [e for e in result["events"] if e["to_id"] == entity_id]
        top = sorted(mine, key=lambda e: -e["loss"])[:3]
        reasons = [
            f"Lost {e['loss']:,.0f}M from exposure to {names[e['from_id']]} in round {e['round']}"
            for e in top
        ]
    return {
        "stress_before": history[0][entity_id],
        "stress_after": history[-1][entity_id],
        "reasons": reasons or ["No material losses traced to this entity."],
    }
