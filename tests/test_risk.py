
import pandas as pd
import pytest

from engine.risk import compute_baseline


def test_baseline_score_is_between_zero_and_100():
    entities = pd.DataFrame({
        "entity_id": ["A", "B", "C"],
        "total_assets_bn": [100.0, 200.0, 150.0],
        "capital_buffer_bn": [20.0, 20.0, 30.0],
    })

    exposures = pd.DataFrame({
        "creditor_id": ["A", "B", "C"],
        "debtor_id": ["B", "C", "A"],
        "exposure_bn": [10.0, 30.0, 15.0],
    })

    result = compute_baseline(entities, exposures)

    assert "baseline_score" in result.columns
    assert result["baseline_score"].between(0, 100).all()


def test_highest_leverage_has_highest_leverage_component():
    entities = pd.DataFrame({
        "entity_id": ["A", "B"],
        "total_assets_bn": [100.0, 100.0],
        "capital_buffer_bn": [10.0, 50.0],
    })

    exposures = pd.DataFrame({
        "creditor_id": [],
        "debtor_id": [],
        "exposure_bn": [],
    })

    result = compute_baseline(entities, exposures)

    scores = result.set_index("entity_id")["leverage"]

    assert scores["A"] > scores["B"]
