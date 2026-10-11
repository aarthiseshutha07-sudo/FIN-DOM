"""Checks that the adapter gives the dashboard exactly the shapes it reads."""
import pandas as pd
import pytest

from app import engine_adapter as ad

RESULT_KEYS = {"source_id", "severity", "rounds", "stress_history",
               "status", "events", "total_loss", "scenario_score"}


def test_table_shapes():
    ents, exps = ad.load_data()
    assert list(ents.columns) == ["id", "name", "type", "region", "assets", "buffer", "leverage"]
    assert list(exps.columns) == ["from_id", "to_id", "amount"]
    assert list(ad.baseline().columns) == ["id", "baseline_score"]


@pytest.mark.parametrize("severity", [0, 30, 70, 100])
def test_every_source_gives_a_complete_result(severity):
    ents, _ = ad.load_data()
    ids = set(ents["id"])
    for src in ids:
        r = ad.run_scenario(src, severity)
        assert set(r) == RESULT_KEYS
        assert len(r["stress_history"]) == r["rounds"] + 1
        assert all(set(step) == ids for step in r["stress_history"])
        assert set(r["status"]) == ids and set(r["scenario_score"]) == ids
        assert all(e["from_id"] in ids and e["to_id"] in ids for e in r["events"])
        for i in ids:
            info = ad.explain_entity(r, ents, i)
            assert set(info) == {"stress_before", "stress_after", "reasons"}
            assert info["reasons"]


def test_source_is_marked_as_source():
    ents, _ = ad.load_data()
    r = ad.run_scenario("MER", 70)
    assert r["status"]["MER"] == "Failed"  # 70% x 1.5 caps at full stress
    assert "Source of the shock" in ad.explain_entity(r, ents, "MER")["reasons"][0]
