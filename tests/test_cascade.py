
import pandas as pd
import pytest

from engine.cascade import run_cascade


@pytest.fixture
def sample_data():
    entities = pd.DataFrame({
        "entity_id": ["MER", "HAR", "NOR"],
        "name": ["Meridian", "Harbor", "Northwind"],
        "type": ["Bank", "Bank", "Fund"],
        "region": ["Americas", "Europe", "Asia-Pacific"],
        "total_assets_bn": [300.0, 180.0, 70.0],
        "capital_buffer_bn": [63.0, 36.0, 14.0],
    })

    exposures = pd.DataFrame({
        "exposure_id": ["E1", "E2", "E3"],
        "creditor_id": ["HAR", "NOR", "NOR"],
        "debtor_id": ["MER", "MER", "HAR"],
        "exposure_bn": [28.0, 10.0, 20.0],
        "exposure_type": [
            "Interbank loan",
            "Bond holding",
            "Credit line",
        ],
    })

    return entities, exposures


def test_cascade_spreads_stress_correctly(sample_data):
    entities, exposures = sample_data

    result = run_cascade(entities, exposures, "MER", 0.7)
    state = result["state"].set_index("entity_id")

    assert state.loc["MER", "status"] == "Failed"
    assert state.loc["HAR", "final_stress"] == pytest.approx(
        0.4666667, abs=1e-5
    )
    assert state.loc["NOR", "final_stress"] == pytest.approx(
        0.8285714, abs=1e-5
    )


def test_zero_severity_does_not_spread_stress(sample_data):
    entities, exposures = sample_data

    result = run_cascade(entities, exposures, "MER", 0.0)

    assert (result["state"]["final_stress"] == 0.0).all()


def test_row_order_does_not_change_final_stress(sample_data):
    entities, exposures = sample_data

    first = run_cascade(entities, exposures, "MER", 0.7)

    second = run_cascade(
        entities.iloc[::-1].reset_index(drop=True),
        exposures.iloc[::-1].reset_index(drop=True),
        "MER",
        0.7,
    )

    first_state = first["state"].set_index("entity_id")[
        "final_stress"
    ].sort_index()

    second_state = second["state"].set_index("entity_id")[
        "final_stress"
    ].sort_index()

    pd.testing.assert_series_equal(first_state, second_state)


def test_invalid_severity_is_rejected(sample_data):
    entities, exposures = sample_data

    with pytest.raises(ValueError):
        run_cascade(entities, exposures, "MER", 1.5)


def test_unknown_source_is_rejected(sample_data):
    entities, exposures = sample_data

    with pytest.raises(ValueError):
        run_cascade(entities, exposures, "UNKNOWN", 0.7)
