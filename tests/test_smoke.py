"""Basic smoke tests for the A2 backend foundation.

These check that the constants, the CSV loader and the stubs hang together.
The full per-rule validation tests are a separate, later step.
Run with:  python -m pytest
"""

import pytest

from engine import params
from engine.cascade import LEDGER_COLUMNS, STATE_COLUMNS, run_cascade
from engine.data_loader import (
    ENTITY_COLUMNS,
    EXPOSURE_COLUMNS,
    DataValidationError,
    load_data,
)
from engine.explain import explain
from engine.risk import compute_baseline

# A tiny, valid dataset (the same three entities as the worked example in
# docs/ENGINE_RULES.md).
ENTITIES_CSV = """entity_id,name,type,region,total_assets_bn,capital_buffer_bn
E01,Meridian Bank,Bank,Europe,900,63
E02,Harbor Insurance,Insurer,Europe,300,36
E03,Northwind Capital,Fund,Americas,120,14
"""

EXPOSURES_CSV = """exposure_id,creditor_id,debtor_id,exposure_bn,exposure_type
X001,E02,E01,28,Bond holding
X002,E03,E01,10,Derivative
X003,E03,E02,20,Credit line
"""


def write_data(folder, entities=ENTITIES_CSV, exposures=EXPOSURES_CSV):
    (folder / "entities.csv").write_text(entities)
    (folder / "exposures.csv").write_text(exposures)
    return folder


def test_parameters_match_engine_rules():
    assert params.LOSS_RATE == 0.6
    assert params.SHOCK_SCALE == 1.5
    assert params.STABLE_MAX == 0.25
    assert params.FAILED_MIN == 1.0
    assert params.MAX_ROUNDS == 10
    assert sum(params.SCORE_WEIGHTS.values()) == pytest.approx(1.0)


def test_valid_data_loads_with_exact_columns(tmp_path):
    entities, exposures = load_data(write_data(tmp_path))
    assert list(entities.columns) == ENTITY_COLUMNS
    assert list(exposures.columns) == EXPOSURE_COLUMNS
    assert len(entities) == 3 and len(exposures) == 3
    assert entities["total_assets_bn"].dtype == float
    assert exposures["exposure_bn"].dtype == float


def test_row_order_does_not_change_the_loaded_tables(tmp_path):
    def reverse_rows(text):
        header, *rows = text.strip().splitlines()
        return "\n".join([header] + rows[::-1]) + "\n"

    normal = tmp_path / "normal"
    shuffled = tmp_path / "shuffled"
    normal.mkdir()
    shuffled.mkdir()
    write_data(normal)
    write_data(shuffled, reverse_rows(ENTITIES_CSV), reverse_rows(EXPOSURES_CSV))

    e1, x1 = load_data(normal)
    e2, x2 = load_data(shuffled)
    assert e1.equals(e2)
    assert x1.equals(x2)


def test_whitespace_around_values_is_cleaned(tmp_path):
    messy = ENTITIES_CSV.replace("Meridian Bank", "  Meridian Bank ")
    entities, _ = load_data(write_data(tmp_path, entities=messy))
    assert entities.loc[0, "name"] == "Meridian Bank"


def test_all_problems_are_reported_together(tmp_path):
    bad_entities = ENTITIES_CSV + "E01,Duplicate Id Bank,Bank,Europe,500,600\n"
    bad_exposures = EXPOSURES_CSV + "X004,E02,E99,5,Bond holding\n"
    with pytest.raises(DataValidationError) as caught:
        load_data(write_data(tmp_path, bad_entities, bad_exposures))

    text = str(caught.value)
    assert len(caught.value.problems) >= 3
    assert "entity_id 'E01' is a duplicate of row 2" in text   # rule E3
    assert "must be less than total_assets_bn" in text          # rule E9
    assert "debtor_id 'E99' not found in entities" in text      # rule X4
    assert "row 5" in text                                       # CSV line numbers


def test_missing_file_gives_a_clear_error(tmp_path):
    with pytest.raises(DataValidationError) as caught:
        load_data(tmp_path)  # empty folder
    assert "file not found" in str(caught.value)


def test_stubs_return_the_agreed_shapes(tmp_path):
    entities, exposures = load_data(write_data(tmp_path))

    scored = compute_baseline(entities, exposures)
    assert "baseline_score" in scored.columns
    assert len(scored) == len(entities)

    result = run_cascade(entities, exposures, source_id="E01", severity=0.7)
    assert set(result) == {"state", "ledger", "snapshots"}
    assert list(result["state"].columns) == STATE_COLUMNS
    assert list(result["ledger"].columns) == LEDGER_COLUMNS
    assert len(result["state"]) == len(entities)
    assert 0 in result["snapshots"]

    sentences = explain(result, "E02")
    assert isinstance(sentences, list) and 1 <= len(sentences) <= 3


def test_cascade_stub_rejects_bad_inputs(tmp_path):
    entities, exposures = load_data(write_data(tmp_path))
    with pytest.raises(ValueError):
        run_cascade(entities, exposures, source_id="NOPE", severity=0.5)
    with pytest.raises(ValueError):
        run_cascade(entities, exposures, source_id="E01", severity=1.5)
