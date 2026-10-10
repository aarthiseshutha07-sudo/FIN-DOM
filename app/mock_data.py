"""TEMPORARY mock data for UI development (Person B).

*** SYNTHETIC AND ILLUSTRATIVE ONLY ***
- Not the real engine. Delete this file when the real engine is wired in.
- Function names start with `mock_` on purpose: they are NOT the engine's API.
- Column names and result keys here are placeholders; the UI will reach them
  through one adapter so they can be changed in a single place later.
"""
import random

import pandas as pd

_NAMES = [
    ("Meridian Bank", "Bank"), ("Harbor Insurance", "Insurer"), ("Atlas Fund", "Fund"),
    ("Northgate Bank", "Bank"), ("Crestline Bank", "Bank"), ("Solace Bank", "Bank"),
    ("Pinnacle Bank", "Bank"), ("Ironwood Bank", "Bank"), ("Bluewater Bank", "Bank"),
    ("Evergreen Insurance", "Insurer"), ("Sentinel Insurance", "Insurer"),
    ("Lighthouse Assurance", "Insurer"), ("Granite Life", "Insurer"),
    ("Vanguard Capital Fund", "Fund"), ("Summit Hedge Fund", "Fund"),
    ("Orchid Pension Fund", "Fund"), ("Falcon Asset Fund", "Fund"), ("Cedar Growth Fund", "Fund"),
    ("Titan Steel Corp", "Corporate"), ("Helix Energy Corp", "Corporate"),
    ("Nimbus Telecom", "Corporate"), ("Quartz Logistics", "Corporate"),
    ("Republic of Aldoria", "Sovereign"), ("Kingdom of Verandi", "Sovereign"),
    ("Federation of Lumeria", "Sovereign"),
]
_REGIONS = ["North", "South", "East", "West"]


def mock_load_data():
    """Return (entities, exposures) DataFrames with fixed, repeatable values."""
    rng = random.Random(7)
    rows = []
    for i, (name, kind) in enumerate(_NAMES):
        assets = rng.randint(2000, 9000)
        rows.append({
            "id": f"E{i + 1:02d}", "name": name, "type": kind,
            "region": rng.choice(_REGIONS), "assets": assets,
            "buffer": round(assets * rng.uniform(0.06, 0.14)),
            "leverage": round(rng.uniform(4, 16), 1),
        })
    entities = pd.DataFrame(rows)

    ids = entities["id"].tolist()
    links = set()
    while len(links) < 60:
        a, b = rng.sample(ids, 2)
        links.add((a, b))
    exposures = pd.DataFrame(
        [{"from_id": a, "to_id": b, "amount": rng.randint(60, 420)} for a, b in sorted(links)]
    )
    return entities, exposures


def mock_baseline(entities, exposures):
    """Return a DataFrame: id, baseline_score (0-100). Illustrative formula."""
    degree = pd.concat([exposures["from_id"], exposures["to_id"]]).value_counts()
    out = entities[["id"]].copy()
    lev = entities["leverage"] / 16
    thin = 1 - (entities["buffer"] / entities["assets"]) / 0.14
    conn = entities["id"].map(degree).fillna(0) / max(degree.max(), 1)
    out["baseline_score"] = ((0.4 * lev + 0.3 * thin.clip(0, 1) + 0.3 * conn) * 100).round(1)
    return out


def mock_cascade(entities, exposures, source_id, severity_pct):
    """Return a result dict. Illustrative cascade, not the real engine rules."""
    buf = entities.set_index("id")["buffer"].to_dict()
    direct = {i: 0.0 for i in buf}
    direct[source_id] = min(1.0, severity_pct / 100 * 1.2)
    stress = dict(direct)
    history = [dict(stress)]
    events = []
    changed_prev = {source_id} if direct[source_id] > 0 else set()
    for rnd in range(1, 11):
        incoming = {i: 0.0 for i in buf}
        for r in exposures.itertuples():
            loss = r.amount * stress[r.to_id] * 0.6
            incoming[r.from_id] += loss
        new = {i: min(1.5, direct[i] + incoming[i] / buf[i]) for i in buf}
        new[source_id] = max(new[source_id], direct[source_id])
        changed = {i for i in buf if abs(new[i] - stress[i]) > 0.01}
        for r in exposures.itertuples():
            if r.to_id in changed_prev and r.from_id in changed and r.from_id != source_id:
                events.append({"round": rnd, "from_id": r.to_id, "to_id": r.from_id,
                               "loss": round(r.amount * stress[r.to_id] * 0.6, 1)})
        if not changed:
            break
        stress, changed_prev = new, changed
        history.append(dict(stress))
    final = history[-1]
    status = {k: ("Failed" if v >= 1 else "Stressed" if v >= 0.25 else "Stable")
              for k, v in final.items()}
    base = mock_baseline(entities, exposures).set_index("id")["baseline_score"]
    scenario = (base + pd.Series(final) * 40).clip(upper=100).round(1)
    return {
        "source_id": source_id, "severity": severity_pct,
        "rounds": len(history) - 1, "stress_history": history,
        "status": status, "events": events,
        "total_loss": round(sum(e["loss"] for e in events), 1),
        "scenario_score": scenario.to_dict(),
    }


def mock_explain(result, entities, entity_id):
    """Return a dict with before/after stress and readable reasons."""
    names = entities.set_index("id")["name"].to_dict()
    mine = [e for e in result["events"] if e["to_id"] == entity_id]
    top = sorted(mine, key=lambda e: -e["loss"])[:3]
    reasons = [f"Lost {e['loss']:.0f}M from exposure to {names[e['from_id']]} in round {e['round']}"
               for e in top]
    if entity_id == result["source_id"]:
        reasons = [f"Source of the shock ({result['severity']}% severity)"]
    return {
        "stress_before": result["stress_history"][0][entity_id],
        "stress_after": result["stress_history"][-1][entity_id],
        "reasons": reasons or ["No material losses traced to this entity."],
    }