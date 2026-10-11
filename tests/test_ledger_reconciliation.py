import pandas as pd
import pytest

from engine.cascade import run_cascade


def worked_example():
    entities = pd.DataFrame({
        "entity_id": ["MER", "HAR", "NOR"],
        "name": ["Meridian Bank", "Harbor Insurance", "Northwind Capital"],
        "type": ["Bank", "Insurer", "Fund"],
        "region": ["Europe", "Europe", "Americas"],
        "total_assets_bn": [900.0, 300.0, 120.0],
        "capital_buffer_bn": [63.0, 36.0, 14.0],
    })
    exposures = pd.DataFrame({
        "exposure_id": ["X1", "X2", "X3"],
        "creditor_id": ["HAR", "NOR", "NOR"],
        "debtor_id": ["MER", "MER", "HAR"],
        "exposure_bn": [28.0, 10.0, 20.0],
        "exposure_type": ["Bond holding", "Derivative", "Credit line"],
    })
    return entities, exposures


def ledger_rows(ledger, round_number, creditor, debtor):
    return ledger[
        (ledger["round"] == round_number)
        & (ledger["creditor_id"] == creditor)
        & (ledger["debtor_id"] == debtor)
    ]


def test_worked_example_final_stress():
    entities, exposures = worked_example()
    state = run_cascade(entities, exposures, "MER", 0.7)["state"].set_index("entity_id")
    assert state.loc["MER", "final_stress"] == pytest.approx(1.0)
    assert state.loc["HAR", "final_stress"] == pytest.approx(16.8 / 36)
    assert state.loc["NOR", "final_stress"] == pytest.approx(11.6 / 14)


def test_ledger_reconciles_with_final_stress():
    entities, exposures = worked_example()
    result = run_cascade(entities, exposures, "MER", 0.7)
    state = result["state"].set_index("entity_id")
    ledger = result["ledger"]
    buffers = entities.set_index("entity_id")["capital_buffer_bn"]
    for entity_id in state.index:
        total = ledger.loc[ledger["creditor_id"] == entity_id, "loss_bn"].sum()
        expected = min(1.0, total / buffers[entity_id])
        assert expected == pytest.approx(state.loc[entity_id, "final_stress"])


def test_ledger_has_the_expected_loss_events_and_no_double_count():
    entities, exposures = worked_example()
    ledger = run_cascade(entities, exposures, "MER", 0.7)["ledger"]

    assert ledger_rows(ledger, 1, "HAR", "MER")["loss_bn"].iloc[0] == pytest.approx(16.8)
    assert ledger_rows(ledger, 1, "NOR", "MER")["loss_bn"].iloc[0] == pytest.approx(6.0)
    assert ledger_rows(ledger, 2, "NOR", "HAR")["loss_bn"].iloc[0] == pytest.approx(5.6)
    # Meridian's stress did not change after round 0, so it must not be charged again.
    assert len(ledger_rows(ledger, 2, "NOR", "MER")) == 0