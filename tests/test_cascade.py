
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


def test_ledger_losses_are_non_negative(sample_data):
    entities, exposures = sample_data

    result = run_cascade(
        entities,
        exposures,
        source_id="MER",
        severity=0.7,
    )

    ledger = result["ledger"]

    assert (ledger["loss_bn"] >= 0).all()
    assert (ledger["stress_increase"] >= 0).all()


def test_ledger_records_expected_initial_shock(sample_data):
    entities, exposures = sample_data

    result = run_cascade(
        entities,
        exposures,
        source_id="MER",
        severity=0.7,
    )

    ledger = result["ledger"]
    shock = ledger[ledger["debtor_id"] == "SHOCK"]

    assert len(shock) == 1
    assert shock.iloc[0]["creditor_id"] == "MER"
    assert shock.iloc[0]["loss_bn"] == pytest.approx(63.0)


def test_final_losses_match_final_stress(sample_data):
    entities, exposures = sample_data

    result = run_cascade(
        entities,
        exposures,
        source_id="MER",
        severity=0.7,
    )

    state = result["state"].set_index("entity_id")

    expected_losses = {
        "MER": 63.0,
        "HAR": 16.8,
        "NOR": 11.6,
    }

    for entity_id, expected_loss in expected_losses.items():
        actual_loss = (
            float(state.loc[entity_id, "final_stress"])
            * float(
                entities.loc[
                    entities["entity_id"] == entity_id,
                    "capital_buffer_bn",
                ].iloc[0]
            )
        )

        assert actual_loss == pytest.approx(expected_loss, abs=0.02)

def test_simulation_stops_within_max_rounds(sample_data):
    from engine.params import MAX_ROUNDS

    entities, exposures = sample_data

    result = run_cascade(
        entities,
        exposures,
        source_id="MER",
        severity=0.7,
    )

    propagation_rounds = [
        round_number
        for round_number in result["snapshots"]
        if round_number > 0
    ]

    assert len(propagation_rounds) <= MAX_ROUNDS
    assert max(propagation_rounds, default=0) <= MAX_ROUNDS


def test_simulation_stops_when_stress_converges(sample_data):
    entities, exposures = sample_data

    result = run_cascade(
        entities,
        exposures,
        source_id="MER",
        severity=0.7,
    )

    snapshots = result["snapshots"]

    if len(snapshots) >= 2:
        last_round = max(snapshots)
        previous_round = last_round - 1

        if previous_round in snapshots:
            last_stress = snapshots[last_round]
            previous_stress = snapshots[previous_round]

            converged = all(
                abs(last_stress[entity_id] - previous_stress[entity_id])
                <= 1e-6
                for entity_id in last_stress
            )

            # If it stopped before MAX_ROUNDS, it should have converged.
            from engine.params import MAX_ROUNDS

            if last_round < MAX_ROUNDS:
                assert converged
